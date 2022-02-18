#!/usr/bin/env python

"""Client to manage Ubuntu Advantage services on a machine."""

import argparse
import json
import logging
import os
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile
import textwrap
import time
from functools import wraps
from typing import List, Optional, Tuple  # noqa

import yaml

from uaclient import (
    actions,
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    jobs,
    lock,
    messages,
    security,
    security_status,
)
from uaclient import status as ua_status
from uaclient import util, version
from uaclient.clouds import AutoAttachCloudInstance  # noqa: F401
from uaclient.clouds import identity
from uaclient.data_types import AttachActionsConfigFile, IncorrectTypeError
from uaclient.defaults import (
    CLOUD_BUILD_INFO,
    CONFIG_FIELD_ENVVAR_ALLOWLIST,
    DEFAULT_CONFIG_FILE,
    PRINT_WRAP_WIDTH,
)

# TODO: Better address service commands running on cli
# It is not ideal for us to import an entitlement directly on the cli module.
# We need to refactor this to avoid that type of coupling in the code.
from uaclient.entitlements.livepatch import LIVEPATCH_CMD
from uaclient.jobs.update_messaging import update_apt_and_motd_messages

NAME = "ua"

USAGE_TMPL = "{name} {command} [flags]"
EPILOG_TMPL = (
    "Use {name} {command} --help for more information about a command."
)

STATUS_HEADER_TMPL = """\
Account: {account}
Subscription: {subscription}
Valid until: {contract_expiry}
Technical support level: {tech_support_level}
"""
UA_AUTH_TOKEN_URL = "https://auth.contracts.canonical.com"

DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(filename)s:(%(lineno)d) [%(levelname)s]: %(message)s"
)

STATUS_FORMATS = ["tabular", "json", "yaml"]

UA_COLLECT_LOGS_FILE = "ua_logs.tar.gz"

UA_SERVICES = (
    "ua-timer.service",
    "ua-timer.timer",
    "ua-auto-attach.path",
    "ua-auto-attach.service",
    "ua-reboot-cmds.service",
    "ua-license-check.path",
    "ua-license-check.service",
    "ua-license-check.timer",
)

event = event_logger.get_event_logger()


class UAArgumentParser(argparse.ArgumentParser):
    def __init__(
        self,
        prog=None,
        usage=None,
        epilog=None,
        formatter_class=argparse.HelpFormatter,
        base_desc: str = None,
    ):
        super().__init__(
            prog=prog,
            usage=usage,
            epilog=epilog,
            formatter_class=formatter_class,
        )

        self.base_desc = base_desc

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, message + "\n")

    def print_help(self, file=None, show_all=False):
        if self.base_desc:
            non_beta_services_desc, beta_services_desc = (
                UAArgumentParser._get_service_descriptions()
            )
            service_descriptions = sorted(non_beta_services_desc)
            if show_all:
                service_descriptions = sorted(
                    service_descriptions + beta_services_desc
                )
            self.description = "\n".join(
                [self.base_desc] + service_descriptions
            )
        super().print_help(file=file)

    @staticmethod
    def _get_service_descriptions() -> Tuple[List[str], List[str]]:
        service_info_tmpl = " - {name}: {description}{url}"
        non_beta_services_desc = []
        beta_services_desc = []

        resources = contract.get_available_resources(config.UAConfig())
        for resource in resources:
            try:
                ent_cls = entitlements.entitlement_factory(resource["name"])
            except exceptions.EntitlementNotFoundError:
                continue
            # Because we don't know the presentation name if unattached
            presentation_name = resource.get("presentedAs", resource["name"])
            if ent_cls.help_doc_url:
                url = " ({})".format(ent_cls.help_doc_url)
            else:
                url = ""
            service_info = textwrap.fill(
                service_info_tmpl.format(
                    name=presentation_name,
                    description=ent_cls.description,
                    url=url,
                ),
                width=PRINT_WRAP_WIDTH,
                subsequent_indent="   ",
                break_long_words=False,
                break_on_hyphens=False,
            )
            if ent_cls.is_beta:
                beta_services_desc.append(service_info)
            else:
                non_beta_services_desc.append(service_info)

        return (non_beta_services_desc, beta_services_desc)


def assert_lock_file(lock_holder=None):
    """Decorator asserting exclusive access to lock file"""

    def wrapper(f):
        @wraps(f)
        def new_f(*args, cfg, **kwargs):
            with lock.SingleAttemptLock(cfg=cfg, lock_holder=lock_holder):
                retval = f(*args, cfg=cfg, **kwargs)
            return retval

        return new_f

    return wrapper


def assert_root(f):
    """Decorator asserting root user"""

    @wraps(f)
    def new_f(*args, **kwargs):
        if os.getuid() != 0:
            raise exceptions.NonRootUserError()
        else:
            return f(*args, **kwargs)

    return new_f


def verify_json_format_args(f):
    """Decorator to verify if correct params are used for json format"""

    @wraps(f)
    def new_f(cmd_args, *args, **kwargs):
        if not cmd_args:
            return f(cmd_args, *args, **kwargs)

        if cmd_args.format == "json" and not cmd_args.assume_yes:
            msg = messages.JSON_FORMAT_REQUIRE_ASSUME_YES
            raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)
        else:
            return f(cmd_args, *args, **kwargs)

    return new_f


def assert_attached(unattached_msg_tmpl=None):
    """Decorator asserting attached config.

    :param unattached_msg_tmpl: Optional msg template to format if raising an
        UnattachedError
    """

    def wrapper(f):
        @wraps(f)
        def new_f(args, cfg, **kwargs):
            if not cfg.is_attached:
                if unattached_msg_tmpl:
                    names = getattr(args, "service", "None")
                    msg = unattached_msg_tmpl.format(name=", ".join(names))
                    exception = exceptions.UnattachedError(msg)
                else:
                    exception = exceptions.UnattachedError()
                raise exception
            return f(args, cfg=cfg, **kwargs)

        return new_f

    return wrapper


def assert_not_attached(f):
    """Decorator asserting unattached config."""

    @wraps(f)
    def new_f(args, cfg):
        if cfg.is_attached:
            raise exceptions.AlreadyAttachedError(cfg)
        return f(args, cfg=cfg)

    return new_f


def auto_attach_parser(parser):
    """Build or extend an arg parser for auto-attach subcommand."""
    parser.prog = "auto-attach"
    parser.description = (
        "Automatically attach an Ubuntu Advantage token on Ubuntu Pro"
        " images."
    )
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser._optionals.title = "Flags"
    return parser


def collect_logs_parser(parser):
    """Build or extend an arg parser for 'collect-logs' subcommand."""
    parser.prog = "collect-logs"
    parser.description = (
        "Collect UA logs and relevant system information into a tarball."
    )
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "tarball where the logs will be stored. (Defaults to "
            "./ua_logs.tar.gz)"
        ),
    )
    return parser


def config_show_parser(parser):
    """Build or extend an arg parser for 'config show' subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="show [key]")
    parser.prog = "show"
    parser.description = "Show customisable configuration settings"
    parser.add_argument(
        "key",
        nargs="?",  # action_config_show handles this optional argument
        help="Optional key or key(s) to show configuration settings.",
    )
    return parser


def config_set_parser(parser):
    """Build or extend an arg parser for 'config set' subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="set <key>=<value>")
    parser.prog = "set"
    parser.description = (
        "Set and apply Ubuntu Advantage configuration settings"
    )
    parser._optionals.title = "Flags"
    parser.add_argument(
        "key_value_pair",
        help=(
            "key=value pair to configure for Ubuntu Advantage services."
            " Key must be one of: {}".format(
                ", ".join(config.UA_CONFIGURABLE_KEYS)
            )
        ),
    )
    return parser


def config_unset_parser(parser):
    """Build or extend an arg parser for 'config unset' subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="unset <key>")
    parser.prog = "unset"
    parser.description = "Unset Ubuntu Advantage configuration setting"
    parser.add_argument(
        "key",
        help=(
            "configuration key to unset from Ubuntu Advantage services."
            " One of: {}".format(", ".join(config.UA_CONFIGURABLE_KEYS))
        ),
        metavar="key",
    )
    parser._optionals.title = "Flags"
    return parser


def config_parser(parser):
    """Build or extend an arg parser for config subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="config <command>")
    parser.prog = "config"
    parser.description = "Manage Ubuntu Advantage configuration"
    parser._optionals.title = "Flags"
    subparsers = parser.add_subparsers(
        title="Available Commands", dest="command", metavar=""
    )
    parser_show = subparsers.add_parser(
        "show", help="show all Ubuntu Advantage configuration setting(s)"
    )
    parser_show.set_defaults(action=action_config_show)
    config_show_parser(parser_show)

    parser_set = subparsers.add_parser(
        "set", help="set Ubuntu Advantage configuration setting"
    )
    parser_set.set_defaults(action=action_config_set)
    config_set_parser(parser_set)

    parser_unset = subparsers.add_parser(
        "unset", help="unset Ubuntu Advantage configuration setting"
    )
    parser_unset.set_defaults(action=action_config_unset)
    config_unset_parser(parser_unset)
    return parser


def attach_parser(parser):
    """Build or extend an arg parser for attach subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="attach <token>")
    parser.prog = "attach"
    parser.description = (
        "Attach this machine to Ubuntu Advantage with a token obtained"
        " from https://ubuntu.com/advantage"
    )
    parser._optionals.title = "Flags"
    parser.add_argument(
        "token",
        nargs="?",  # action_attach asserts this required argument
        help="token obtained for Ubuntu Advantage authentication: {}".format(
            UA_AUTH_TOKEN_URL
        ),
    )
    parser.add_argument(
        "--no-auto-enable",
        action="store_false",
        dest="auto_enable",
        help="do not enable any recommended services automatically",
    )
    parser.add_argument(
        "--attach-config",
        type=argparse.FileType("r"),
        help=(
            "use the provided attach config file instead of passing the token"
            " on the cli"
        ),
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=("output enable in the specified format (default: cli)"),
    )
    return parser


def fix_parser(parser):
    """Build or extend an arg parser for fix subcommand."""
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="fix <CVE-yyyy-nnnn+>|<USN-nnnn-d+>"
    )
    parser.prog = "fix"
    parser.description = (
        "Inspect and resolve CVEs and USNs (Ubuntu Security Notices) on this"
        " machine."
    )
    parser._optionals.title = "Flags"
    parser.add_argument(
        "security_issue",
        help=(
            "Security vulnerability ID to inspect and resolve on this system."
            " Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-dd"
        ),
    )
    return parser


def security_status_parser(parser):
    """Build or extend an arg parser for security-status subcommand."""
    parser.prog = "security-status"
    parser.description = (
        "Show security updates for packages in the system, including all"
        " available ESM related content."
    )
    parser.add_argument(
        "--format",
        help=("Format for the output (json or yaml)"),
        choices=("json", "yaml"),
        required=True,
    )
    return parser


def refresh_parser(parser):
    """Build or extend an arg parser for refresh subcommand."""
    parser.prog = "refresh"
    parser.description = (
        "Refresh existing Ubuntu Advantage contract and update services."
    )
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="refresh [contract|config]"
    )
    parser._optionals.title = "Flags"
    parser.add_argument(
        "target",
        choices=["contract", "config"],
        nargs="?",
        default=None,
        help=(
            "Target to refresh. `ua refresh contract` will update contract"
            " details from the server and perform any updates necessary."
            " `ua refresh config` will reload"
            " /etc/ubuntu-advantage/uaclient.conf and perform any changes"
            " necessary. `ua refresh` is the equivalent of `ua refresh"
            " config && ua refresh contract`."
        ),
    )
    return parser


def action_security_status(args, *, cfg, **kwargs):
    # For now, --format is mandatory so no need to check for it here.
    if args.format == "json":
        print(json.dumps(security_status.security_status(cfg)))
    else:
        print(
            yaml.safe_dump(
                security_status.security_status(cfg), default_flow_style=False
            )
        )
    return 0


def action_fix(args, *, cfg, **kwargs):
    if not re.match(security.CVE_OR_USN_REGEX, args.security_issue):
        msg = (
            'Error: issue "{}" is not recognized.\n'
            'Usage: "ua fix CVE-yyyy-nnnn" or "ua fix USN-nnnn"'
        ).format(args.security_issue)
        raise exceptions.UserFacingError(msg)

    fix_status = security.fix_security_issue_id(cfg, args.security_issue)
    return fix_status.value


def detach_parser(parser):
    """Build or extend an arg parser for detach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="detach")
    parser.usage = usage
    parser.prog = "detach"
    parser.description = "Detach this machine from Ubuntu Advantage services."
    parser._optionals.title = "Flags"
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help="do not prompt for confirmation before performing the detach",
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=("output enable in the specified format (default: cli)"),
    )
    return parser


def help_parser(parser):
    """Build or extend an arg parser for help subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="help [service]")
    parser.usage = usage
    parser.prog = "help"
    parser.description = (
        "Provide detailed information about Ubuntu Advantage services."
    )
    parser._positionals.title = "Arguments"
    parser.add_argument(
        "service",
        action="store",
        nargs="?",
        help="a service to view help output for. One of: {}".format(
            ", ".join(entitlements.valid_services())
        ),
    )

    parser.add_argument(
        "--format",
        action="store",
        choices=STATUS_FORMATS,
        default=STATUS_FORMATS[0],
        help=(
            "output help in the specified format (default: {})".format(
                STATUS_FORMATS[0]
            )
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Allow the visualization of beta services",
    )

    return parser


def enable_parser(parser):
    """Build or extend an arg parser for enable subcommand."""
    usage = USAGE_TMPL.format(
        name=NAME, command="enable <service> [<service>]"
    )
    parser.description = "Enable an Ubuntu Advantage service."
    parser.usage = usage
    parser.prog = "enable"
    parser._positionals.title = "Arguments"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            "the name(s) of the Ubuntu Advantage services to enable."
            " One of: {}".format(", ".join(entitlements.valid_services()))
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help="do not prompt for confirmation before performing the enable",
    )
    parser.add_argument(
        "--beta", action="store_true", help="allow beta service to be enabled"
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=("output enable in the specified format (default: cli)"),
    )
    return parser


def disable_parser(parser):
    """Build or extend an arg parser for disable subcommand."""
    usage = USAGE_TMPL.format(
        name=NAME, command="disable <service> [<service>]"
    )
    parser.description = "Disable an Ubuntu Advantage service."
    parser.usage = usage
    parser.prog = "disable"
    parser._positionals.title = "Arguments"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            "the name(s) of the Ubuntu Advantage services to disable"
            " One of: {}".format(", ".join(entitlements.valid_services()))
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help="do not prompt for confirmation before performing the disable",
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=("output disable in the specified format (default: cli)"),
    )
    return parser


def status_parser(parser):
    """Build or extend an arg parser for status subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="status")
    parser.usage = usage
    parser.description = (
        "Output the status information for Ubuntu Advantage services."
    )
    parser.prog = "status"
    # This formatter_class ensures that our formatting below isn't lost
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = textwrap.dedent(
        """\
        Report current status of Ubuntu Advantage services on system.

        This shows whether this machine is attached to an Ubuntu Advantage
        support contract. When attached, the report includes the specific
        support contract details including contract name, expiry dates, and the
        status of each service on this system.

        The attached status output has four columns:

        * SERVICE: name of the service
        * ENTITLED: whether the contract to which this machine is attached
          entitles use of this service. Possible values are: yes or no
        * STATUS: whether the service is enabled on this machine. Possible
          values are: enabled, disabled, n/a (if your contract entitles
          you to the service, but it isn't available for this machine) or — (if
          you aren't entitled to this service)
        * DESCRIPTION: a brief description of the service

        The unattached status output instead has three columns. SERVICE
        and DESCRIPTION are the same as above, and there is the addition
        of:

        * AVAILABLE: whether this service would be available if this machine
          were attached. The possible values are yes or no.

        If --simulate-with-token is used, then the output has five
        columns. SERVICE, AVAILABLE, ENTITLED and DESCRIPTION are the same
        as mentioned above, and AUTO_ENABLED shows whether the service is set
        to be enabled when that token is attached.

        If the --all flag is set, beta and unavailable services are also
        listed in the output.
        """
    )

    parser.add_argument(
        "--wait",
        action="store_true",
        default=False,
        help="Block waiting on ua to complete",
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=STATUS_FORMATS,
        default=STATUS_FORMATS[0],
        help=(
            "output status in the specified format (default: {})".format(
                STATUS_FORMATS[0]
            )
        ),
    )
    parser.add_argument(
        "--simulate-with-token",
        metavar="TOKEN",
        action="store",
        help=("simulate the output status using a provided token"),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Allow the visualization of beta services",
    )
    parser._optionals.title = "Flags"
    return parser


def _perform_disable(entitlement, cfg, *, assume_yes, update_status=True):
    """Perform the disable action on a named entitlement.

    :param entitlement_name: the name of the entitlement to enable
    :param cfg: the UAConfig to pass to the entitlement
    :param assume_yes:
        Assume a yes response for any prompts during service enable

    @return: True on success, False otherwise
    """
    ret, reason = entitlement.disable()

    if not ret:
        event.service_failed(entitlement.name)

        if reason is not None and isinstance(
            reason, ua_status.CanDisableFailure
        ):
            if reason.message is not None:
                event.info(reason.message.msg)
                event.error(
                    error_msg=reason.message.msg,
                    error_code=reason.message.name,
                    service=entitlement.name,
                )
    else:
        event.service_processed(entitlement.name)

    if update_status:
        cfg.status()  # Update the status cache

    return ret


def get_valid_entitlement_names(names: List[str]):
    """Return a list of valid entitlement names.

    :param names: List of entitlements to validate
    :return: a tuple of List containing the valid and invalid entitlements
    """
    entitlements_found = []

    for ent_name in names:
        if ent_name in entitlements.valid_services(
            allow_beta=True, all_names=True
        ):
            entitlements_found.append(ent_name)

    entitlements_not_found = sorted(set(names) - set(entitlements_found))

    return entitlements_found, entitlements_not_found


def action_config(args, *, cfg, **kwargs):
    """Perform the config action.

    :return: 0 on success, 1 otherwise
    """
    parser = get_parser()
    subparser = parser._get_positional_actions()[0].choices["config"]
    valid_choices = subparser._get_positional_actions()[0].choices.keys()
    if args.command not in valid_choices:
        parser._get_positional_actions()[0].choices["config"].print_help()
        raise exceptions.UserFacingError(
            "\n<command> must be one of: {}".format(", ".join(valid_choices))
        )


def action_config_show(args, *, cfg, **kwargs):
    """Perform the 'config show' action optionally limit output to a single key

    :return: 0 on success
    :raise UserFacingError: on invalid keys
    """
    if args.key:  # limit reporting config to a single config key
        if args.key not in config.UA_CONFIGURABLE_KEYS:
            msg = "\n'{}' must be one of: {}".format(
                args.key, ", ".join(config.UA_CONFIGURABLE_KEYS)
            )
            indent_position = msg.find(":") + 2
            raise exceptions.UserFacingError(
                textwrap.fill(
                    msg,
                    width=PRINT_WRAP_WIDTH,
                    subsequent_indent=" " * indent_position,
                )
            )
        print(
            "{key} {value}".format(key=args.key, value=getattr(cfg, args.key))
        )
        return 0

    col_width = str(max([len(x) for x in config.UA_CONFIGURABLE_KEYS]) + 1)
    row_tmpl = "{key: <" + col_width + "} {value}"
    for key in config.UA_CONFIGURABLE_KEYS:
        print(row_tmpl.format(key=key, value=getattr(cfg, key)))


@assert_root
def action_config_set(args, *, cfg, **kwargs):
    """Perform the 'config set' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.apt import setup_apt_proxy
    from uaclient.entitlements.livepatch import configure_livepatch_proxy
    from uaclient.snap import configure_snap_proxy

    parser = get_parser()
    config_parser = parser._get_positional_actions()[0].choices["config"]
    subparser = config_parser._get_positional_actions()[0].choices["set"]
    try:
        set_key, set_value = args.key_value_pair.split("=")
    except ValueError:
        subparser.print_help()
        raise exceptions.UserFacingError(
            "\nExpected <key>=<value> but found: {}".format(
                args.key_value_pair
            )
        )
    if set_key not in config.UA_CONFIGURABLE_KEYS:
        subparser.print_help()
        raise exceptions.UserFacingError(
            "\n<key> must be one of: {}".format(
                ", ".join(config.UA_CONFIGURABLE_KEYS)
            )
        )
    if set_key in ("http_proxy", "https_proxy"):
        protocol_type = set_key.split("_")[0]
        if protocol_type == "http":
            validate_url = util.PROXY_VALIDATION_SNAP_HTTP_URL
        else:
            validate_url = util.PROXY_VALIDATION_SNAP_HTTPS_URL
        util.validate_proxy(protocol_type, set_value, validate_url)

        kwargs = {set_key: set_value}
        configure_snap_proxy(**kwargs)
        # Only set livepatch proxy if livepatch is enabled
        entitlement = entitlements.livepatch.LivepatchEntitlement(cfg)
        livepatch_status, _ = entitlement.application_status()
        if livepatch_status == ua_status.ApplicationStatus.ENABLED:
            configure_livepatch_proxy(**kwargs)
    elif set_key in ("apt_http_proxy", "apt_https_proxy"):
        # setup_apt_proxy is destructive for unprovided values. Source complete
        # current config values from uaclient.conf before applying set_value.
        protocol_type = set_key.split("_")[1]
        if protocol_type == "http":
            validate_url = util.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = util.PROXY_VALIDATION_APT_HTTPS_URL
        util.validate_proxy(protocol_type, set_value, validate_url)
        kwargs = {
            "http_proxy": cfg.apt_http_proxy,
            "https_proxy": cfg.apt_https_proxy,
        }
        kwargs[set_key[4:]] = set_value
        setup_apt_proxy(**kwargs)
    elif set_key in (
        "update_messaging_timer",
        "update_status_timer",
        "metering_timer",
    ):
        try:
            set_value = int(set_value)
            if set_value < 0:
                raise ValueError("Invalid interval for {}".format(set_key))
        except ValueError:
            subparser.print_help()
            # More readable in the CLI, without breaking the line in the logs
            print("")
            raise exceptions.UserFacingError(
                (
                    "Cannot set {} to {}: "
                    "<value> for interval must be a positive integer."
                ).format(set_key, set_value)
            )
    setattr(cfg, set_key, set_value)


@assert_root
def action_config_unset(args, *, cfg, **kwargs):
    """Perform the 'config unset' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.apt import setup_apt_proxy
    from uaclient.entitlements.livepatch import unconfigure_livepatch_proxy
    from uaclient.snap import unconfigure_snap_proxy

    if args.key not in config.UA_CONFIGURABLE_KEYS:
        parser = get_parser()
        config_parser = parser._get_positional_actions()[0].choices["config"]
        subparser = config_parser._get_positional_actions()[0].choices["unset"]
        subparser.print_help()
        raise exceptions.UserFacingError(
            "\n<key> must be one of: {}".format(
                ", ".join(config.UA_CONFIGURABLE_KEYS)
            )
        )
    if args.key in ("http_proxy", "https_proxy"):
        protocol_type = args.key.split("_")[0]
        unconfigure_snap_proxy(protocol_type=protocol_type)
        # Only unset livepatch proxy if livepatch is enabled
        entitlement = entitlements.livepatch.LivepatchEntitlement(cfg)
        livepatch_status, _ = entitlement.application_status()
        if livepatch_status == ua_status.ApplicationStatus.ENABLED:
            unconfigure_livepatch_proxy(protocol_type=protocol_type)
    elif args.key in ("apt_http_proxy", "apt_https_proxy"):
        kwargs = {
            "http_proxy": cfg.apt_http_proxy,
            "https_proxy": cfg.apt_https_proxy,
        }
        kwargs[args.key[4:]] = None
        setup_apt_proxy(**kwargs)
    setattr(cfg, args.key, None)
    return 0


@verify_json_format_args
@assert_root
@assert_attached(messages.ENABLE_FAILURE_UNATTACHED)
@assert_lock_file("ua disable")
def action_disable(args, *, cfg, **kwargs):
    """Perform the disable action on a list of entitlements.

    @return: 0 on success, 1 otherwise
    """
    names = getattr(args, "service", [])
    entitlements_found, entitlements_not_found = get_valid_entitlement_names(
        names
    )
    ret = True

    for ent_name in entitlements_found:
        ent_cls = entitlements.entitlement_factory(ent_name)
        ent = ent_cls(cfg, assume_yes=args.assume_yes)

        ret &= _perform_disable(ent, cfg, assume_yes=args.assume_yes)

    if entitlements_not_found:
        valid_names = (
            "Try "
            + ", ".join(entitlements.valid_services(allow_beta=True))
            + "."
        )
        service_msg = "\n".join(
            textwrap.wrap(
                valid_names,
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
        raise exceptions.InvalidServiceToDisableError(
            operation="disable",
            name=", ".join(entitlements_not_found),
            service_msg=service_msg,
        )

    event.process_events()
    return 0 if ret else 1


def _create_enable_entitlements_not_found_message(
    entitlements_not_found, *, allow_beta: bool
) -> messages.NamedMessage:
    """
    Constructs the MESSAGE_INVALID_SERVICE_OP_FAILURE message
    based on the attempted services and valid services.
    """
    valid_services_names = entitlements.valid_services(allow_beta=allow_beta)
    valid_names = ", ".join(valid_services_names)
    service_msg = "\n".join(
        textwrap.wrap(
            "Try " + valid_names + ".",
            width=80,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )

    return messages.INVALID_SERVICE_OP_FAILURE.format(
        operation="enable",
        name=", ".join(entitlements_not_found),
        service_msg=service_msg,
    )


@verify_json_format_args
@assert_root
@assert_attached(messages.ENABLE_FAILURE_UNATTACHED)
@assert_lock_file("ua enable")
def action_enable(args, *, cfg, **kwargs):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    event.info(messages.REFRESH_CONTRACT_ENABLE)
    try:
        contract.request_updated_contract(cfg)
    except (exceptions.UrlError, exceptions.UserFacingError):
        # Inability to refresh is not a critical issue during enable
        logging.debug(messages.REFRESH_CONTRACT_FAILURE, exc_info=True)
        event.warning(warning_msg=messages.REFRESH_CONTRACT_FAILURE)

    names = getattr(args, "service", [])
    entitlements_found, entitlements_not_found = get_valid_entitlement_names(
        names
    )
    ret = True
    for ent_name in entitlements_found:
        try:
            ent_ret, reason = actions.enable_entitlement_by_name(
                cfg, ent_name, assume_yes=args.assume_yes, allow_beta=args.beta
            )
            cfg.status()  # Update the status cache

            if (
                not ent_ret
                and reason is not None
                and isinstance(reason, ua_status.CanEnableFailure)
            ):
                if reason.message is not None:
                    event.info(reason.message.msg)
                    event.error(
                        error_msg=reason.message.msg,
                        error_code=reason.message.name,
                        service=ent_name,
                    )
                if reason.reason == ua_status.CanEnableFailureReason.IS_BETA:
                    # if we failed because ent is in beta and there was no
                    # allow_beta flag/config, pretend it doesn't exist
                    entitlements_not_found.append(ent_name)
            elif ent_ret:
                event.service_processed(service=ent_name)
            elif not ent_ret and reason is None:
                event.service_failed(service=ent_name)

            ret &= ent_ret
        except exceptions.UserFacingError as e:
            event.info(e.msg)
            event.error(
                error_msg=e.msg, error_code=e.msg_code, service=ent_name
            )
            ret = False

    if entitlements_not_found:
        msg = _create_enable_entitlements_not_found_message(
            entitlements_not_found, allow_beta=args.beta
        )
        event.services_failed(entitlements_not_found)
        raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)

    event.process_events()
    return 0 if ret else 1


@verify_json_format_args
@assert_root
@assert_attached()
@assert_lock_file("ua detach")
def action_detach(args, *, cfg) -> int:
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    return _detach(cfg, assume_yes=args.assume_yes)


def _detach(cfg: config.UAConfig, assume_yes: bool) -> int:
    """Detach the machine from the active Ubuntu Advantage subscription,

    :param cfg: a ``config.UAConfig`` instance
    :param assume_yes: Assume a yes answer to any prompts requested.
         In this case, it means automatically disable any service during
         detach.

    @return: 0 on success, 1 otherwise
    """
    to_disable = []
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls(cfg=cfg, assume_yes=assume_yes)
        # For detach, we should not consider that a service
        # cannot be disabled because of dependent services,
        # since we are going to disable all of them anyway
        ret, _ = ent.can_disable(ignore_dependent_services=True)
        if ret:
            to_disable.append(ent)

    """
    We will make sure that services without dependencies are disabled first
    PS: This will only work because we have only three services with reverse
    dependencies:
    * ros: ros-updates
    * esm-infra: ros, ros-updates
    * esm-apps: ros, ros-updates

    Therefore, this logic will guarantee that we will always disable ros and
    ros-updates before diabling the esm services. If that dependency chain
    change, this logic won't hold anymore and must be properly fixed.

    More details can be seen here:
    https://github.com/canonical/ubuntu-advantage-client/issues/1831
    """
    to_disable.sort(key=lambda ent: len(ent.dependent_services))

    if to_disable:
        suffix = "s" if len(to_disable) > 1 else ""
        event.info(
            "Detach will disable the following service{}:".format(suffix)
        )
        for ent in to_disable:
            event.info("    {}".format(ent.name))
    if not util.prompt_for_confirmation(assume_yes=assume_yes):
        return 1
    for ent in to_disable:
        _perform_disable(ent, cfg, assume_yes=assume_yes, update_status=False)

    cfg.delete_cache()
    jobs.enable_license_check_if_applicable(cfg)
    update_apt_and_motd_messages(cfg)
    event.info(messages.DETACH_SUCCESS)
    event.process_events()
    return 0


def _post_cli_attach(cfg: config.UAConfig) -> None:
    contract_name = None

    if cfg.machine_token:
        contract_name = (
            cfg.machine_token.get("machineTokenInfo", {})
            .get("contractInfo", {})
            .get("name")
        )

    if contract_name:
        event.info(
            messages.ATTACH_SUCCESS_TMPL.format(contract_name=contract_name)
        )
    else:
        event.info(messages.ATTACH_SUCCESS_NO_CONTRACT_NAME)

    jobs.disable_license_check_if_applicable(cfg)

    status, _ret = actions.status(cfg)
    output = ua_status.format_tabular(status)
    event.info(util.handle_unicode_characters(output))
    event.process_events()


@assert_root
@assert_lock_file("ua auto-attach")
def action_auto_attach(args, *, cfg):
    disable_auto_attach = util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.disable_auto_attach"
    )
    if disable_auto_attach:
        msg = "Skipping auto-attach. Config disable_auto_attach is set."
        logging.debug(msg)
        print(msg)
        return 0

    instance = None  # type: Optional[AutoAttachCloudInstance]
    try:
        instance = identity.cloud_instance_factory()
    except exceptions.CloudFactoryError as e:
        if cfg.is_attached:
            # We are attached on non-Pro Image, just report already attached
            raise exceptions.AlreadyAttachedError(cfg)
        if isinstance(e, exceptions.CloudFactoryNoCloudError):
            raise exceptions.UserFacingError(
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE
            )
        if isinstance(e, exceptions.CloudFactoryNonViableCloudError):
            raise exceptions.UserFacingError(messages.UNSUPPORTED_AUTO_ATTACH)
        if isinstance(e, exceptions.CloudFactoryUnsupportedCloudError):
            raise exceptions.NonAutoAttachImageError(
                messages.UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
                    cloud_type=e.cloud_type
                )
            )
        # we shouldn't get here, but this is a reasonable default just in case
        raise exceptions.UserFacingError(
            messages.UNABLE_TO_DETERMINE_CLOUD_TYPE
        )

    if not instance:
        # we shouldn't get here, but this is a reasonable default just in case
        raise exceptions.UserFacingError(
            messages.UNABLE_TO_DETERMINE_CLOUD_TYPE
        )

    current_iid = identity.get_instance_id()
    if cfg.is_attached:
        prev_iid = cfg.read_cache("instance-id")
        if str(current_iid) == str(prev_iid):
            raise exceptions.AlreadyAttachedOnPROError(str(current_iid))
        print("Re-attaching Ubuntu Advantage subscription on new instance")
        if _detach(cfg, assume_yes=True) != 0:
            raise exceptions.UserFacingError(
                messages.DETACH_AUTOMATION_FAILURE
            )

    try:
        actions.auto_attach(cfg, instance)
    except exceptions.UrlError:
        event.info(messages.ATTACH_FAILURE)
        return 1
    except exceptions.UserFacingError:
        return 1
    else:
        _post_cli_attach(cfg)
        return 0


@assert_not_attached
@assert_root
@assert_lock_file("ua attach")
def action_attach(args, *, cfg):
    if not args.token and not args.attach_config:
        raise exceptions.UserFacingError(
            msg=messages.ATTACH_REQUIRES_TOKEN.msg,
            msg_code=messages.ATTACH_REQUIRES_TOKEN.name,
        )
    if args.token and args.attach_config:
        raise exceptions.UserFacingError(
            msg=messages.ATTACH_TOKEN_ARG_XOR_CONFIG.msg,
            msg_code=messages.ATTACH_TOKEN_ARG_XOR_CONFIG.name,
        )

    if args.token:
        token = args.token
        enable_services_override = None
    else:
        try:
            attach_config = AttachActionsConfigFile.from_dict(
                yaml.safe_load(args.attach_config)
            )
        except IncorrectTypeError as e:
            raise exceptions.AttachInvalidConfigFileError(
                config_name=args.attach_config.name, error=e.msg
            )

        token = attach_config.token
        enable_services_override = attach_config.enable_services

    allow_enable = args.auto_enable and enable_services_override is None

    try:
        actions.attach_with_token(cfg, token=token, allow_enable=allow_enable)
    except exceptions.UrlError:
        msg = messages.ATTACH_FAILURE
        event.info(msg.msg)
        event.error(error_msg=msg.msg, error_code=msg.name)
        event.process_events()
        return 1
    except exceptions.UserFacingError as exc:
        event.info(exc.msg)
        event.error(error_msg=exc.msg, error_code=exc.msg_code)
        event.process_events()
        return 1
    else:
        ret = 0
        if enable_services_override is not None and args.auto_enable:
            found, not_found = get_valid_entitlement_names(
                enable_services_override
            )
            for name in found:
                ent_ret, reason = actions.enable_entitlement_by_name(
                    cfg, name, assume_yes=True, allow_beta=True
                )
                if not ent_ret:
                    ret = 1
                    if (
                        reason is not None
                        and isinstance(reason, ua_status.CanEnableFailure)
                        and reason.message is not None
                    ):
                        event.info(reason.message.msg)
                        event.error(
                            error_msg=reason.message.msg,
                            error_code=reason.message.name,
                            service=name,
                        )
                else:
                    event.service_processed(name)

            if not_found:
                msg = _create_enable_entitlements_not_found_message(
                    not_found, allow_beta=True
                )
                event.info(msg.msg, file_type=sys.stderr)
                event.error(error_msg=msg.msg, error_code=msg.name)
                ret = 1
        _post_cli_attach(cfg)
        return ret


def _write_command_output_to_file(
    cmd, filename: str, return_codes: List[int] = None
) -> None:
    """Helper which runs a command and writes output or error to filename."""
    try:
        out, _ = util.subp(cmd.split(), rcs=return_codes)
    except exceptions.ProcessExecutionError as e:
        util.write_file("{}-error".format(filename), str(e))
    else:
        util.write_file(filename, out)


# We have to assert root here, because the logs are not non-root user readable
@assert_root
def action_collect_logs(args, *, cfg: config.UAConfig):
    output_file = args.output or UA_COLLECT_LOGS_FILE

    with tempfile.TemporaryDirectory() as output_dir:

        _write_command_output_to_file(
            "cloud-id", "{}/cloud-id.txt".format(output_dir)
        )
        _write_command_output_to_file(
            "ua status --format json", "{}/ua-status.json".format(output_dir)
        )
        _write_command_output_to_file(
            "{} status".format(LIVEPATCH_CMD),
            "{}/livepatch-status.txt".format(output_dir),
        )
        _write_command_output_to_file(
            "systemctl list-timers --all",
            "{}/systemd-timers.txt".format(output_dir),
        )
        _write_command_output_to_file(
            (
                "journalctl --boot=0 -o short-precise "
                "{} "
                "-u cloud-init-local.service "
                "-u cloud-init-config.service -u cloud-config.service"
            ).format(
                " ".join(
                    ["-u {}".format(s) for s in UA_SERVICES if ".service" in s]
                )
            ),
            "{}/journalctl.txt".format(output_dir),
        )

        for service in UA_SERVICES:
            _write_command_output_to_file(
                "systemctl status {}".format(service),
                "{}/{}.txt".format(output_dir, service),
                return_codes=[0, 3],
            )

        ua_logs = (
            cfg.cfg_path or DEFAULT_CONFIG_FILE,
            cfg.log_file,
            cfg.timer_log_file,
            cfg.license_check_log_file,
            cfg.data_path("jobs-status"),
            CLOUD_BUILD_INFO,
            *(
                entitlement.repo_list_file_tmpl.format(name=entitlement.name)
                for entitlement in entitlements.ENTITLEMENT_CLASSES
                if issubclass(entitlement, entitlements.repo.RepoEntitlement)
            ),
        )

        for log in ua_logs:
            if os.path.isfile(log):
                log_content = util.load_file(log)
                log_content = util.redact_sensitive_logs(log_content)
                util.write_file(log, log_content)
                shutil.copy(log, output_dir)

        with tarfile.open(output_file, "w:gz") as results:
            results.add(output_dir, arcname="logs/")


def get_parser():
    base_desc = __doc__
    parser = UAArgumentParser(
        prog=NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=USAGE_TMPL.format(name=NAME, command="<command>"),
        epilog=EPILOG_TMPL.format(name=NAME, command="<command>"),
        base_desc=base_desc,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show all debug log messages to console",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=get_version(),
        help="show version of {}".format(NAME),
    )
    parser._optionals.title = "Flags"
    subparsers = parser.add_subparsers(
        title="Available Commands", dest="command", metavar=""
    )
    subparsers.required = True
    parser_attach = subparsers.add_parser(
        "attach",
        help="attach this machine to an Ubuntu Advantage subscription",
    )
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)
    parser_auto_attach = subparsers.add_parser(
        "auto-attach", help="automatically attach on supported platforms"
    )
    auto_attach_parser(parser_auto_attach)
    parser_auto_attach.set_defaults(action=action_auto_attach)

    parser_collect_logs = subparsers.add_parser(
        "collect-logs", help="collect UA logs and debug information"
    )
    collect_logs_parser(parser_collect_logs)
    parser_collect_logs.set_defaults(action=action_collect_logs)

    parser_config = subparsers.add_parser(
        "config", help="manage Ubuntu Advantage configuration on this machine"
    )
    config_parser(parser_config)
    parser_config.set_defaults(action=action_config)

    parser_detach = subparsers.add_parser(
        "detach",
        help="remove this machine from an Ubuntu Advantage subscription",
    )
    detach_parser(parser_detach)
    parser_detach.set_defaults(action=action_detach)

    parser_disable = subparsers.add_parser(
        "disable",
        help="disable a specific Ubuntu Advantage service on this machine",
    )
    disable_parser(parser_disable)
    parser_disable.set_defaults(action=action_disable)

    parser_enable = subparsers.add_parser(
        "enable",
        help="enable a specific Ubuntu Advantage service on this machine",
    )
    enable_parser(parser_enable)
    parser_enable.set_defaults(action=action_enable)

    parser_fix = subparsers.add_parser(
        "fix",
        help="check for and mitigate the impact of a CVE/USN on this system",
    )
    parser_fix.set_defaults(action=action_fix)
    fix_parser(parser_fix)

    parser_security_status = subparsers.add_parser(
        "security-status",
        help="list available security updates for the system",
    )
    security_status_parser(parser_security_status)
    parser_security_status.set_defaults(action=action_security_status)

    parser_help = subparsers.add_parser(
        "help",
        help="show detailed information about Ubuntu Advantage services",
    )
    help_parser(parser_help)
    parser_help.set_defaults(action=action_help)

    parser_refresh = subparsers.add_parser(
        "refresh", help="refresh Ubuntu Advantage services"
    )
    parser_refresh.set_defaults(action=action_refresh)
    refresh_parser(parser_refresh)

    parser_status = subparsers.add_parser(
        "status", help="current status of all Ubuntu Advantage services"
    )
    parser_status.set_defaults(action=action_status)
    status_parser(parser_status)

    parser_version = subparsers.add_parser(
        "version", help="show version of {}".format(NAME)
    )
    parser_version.set_defaults(action=print_version)
    return parser


def action_status(args, *, cfg):
    if not cfg:
        cfg = config.UAConfig()
    show_beta = args.all if args else False
    token = args.simulate_with_token if args else None
    active_value = ua_status.UserFacingConfigStatus.ACTIVE.value

    status, ret = actions.status(
        cfg, simulate_with_token=token, show_beta=show_beta
    )
    config_active = bool(status["execution_status"] == active_value)

    if args and args.wait and config_active:
        while status["execution_status"] == active_value:
            event.info(".", end="")
            time.sleep(1)
            status, ret = actions.status(
                cfg, simulate_with_token=token, show_beta=show_beta
            )
        event.info("")

    event.set_output_content(status)
    output = ua_status.format_tabular(status)
    event.info(util.handle_unicode_characters(output))
    event.process_events()
    return ret


def get_version(_args=None, _cfg=None):
    if _cfg is None:
        _cfg = config.UAConfig()

    return version.get_version(features=_cfg.features)


def print_version(_args=None, cfg=None):
    print(get_version(_args, cfg))


def _action_refresh_config(args, cfg: config.UAConfig):
    try:
        cfg.process_config()
    except RuntimeError as exc:
        with util.disable_log_to_console():
            logging.exception(exc)
        raise exceptions.UserFacingError(messages.REFRESH_CONFIG_FAILURE)
    print(messages.REFRESH_CONFIG_SUCCESS)


@assert_attached()
def _action_refresh_contract(_args, cfg: config.UAConfig):
    try:
        contract.request_updated_contract(cfg)
    except exceptions.UrlError as exc:
        with util.disable_log_to_console():
            logging.exception(exc)
        raise exceptions.UserFacingError(messages.REFRESH_CONTRACT_FAILURE)
    print(messages.REFRESH_CONTRACT_SUCCESS)


@assert_root
@assert_lock_file("ua refresh")
def action_refresh(args, *, cfg: config.UAConfig):
    if args.target is None or args.target == "config":
        _action_refresh_config(args, cfg)

    if args.target is None or args.target == "contract":
        _action_refresh_contract(args, cfg)

    return 0


def action_help(args, *, cfg):
    service = args.service
    show_all = args.all

    if not service:
        get_parser().print_help(show_all=show_all)
        return 0

    if not cfg:
        cfg = config.UAConfig()

    help_response = cfg.help(service)

    if args.format == "json":
        print(json.dumps(help_response))
    else:
        for key, value in help_response.items():
            print("{}:\n{}\n".format(key.title(), value))

    return 0


def setup_logging(console_level, log_level, log_file=None, logger=None):
    """Setup console logging and debug logging to log_file"""
    if log_file is None:
        cfg = config.UAConfig()
        log_file = cfg.log_file
    console_formatter = util.LogFormatter()
    log_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    if logger is None:
        # Then we configure the root logger
        logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear all handlers, so they are replaced for this logger
    logger.handlers = []

    # Setup console logging
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)
    console_handler.set_name("ua-console")  # Used to disable console logging
    logger.addHandler(console_handler)

    # Setup file logging
    if os.getuid() == 0:
        # Setup readable-by-root-only debug file logging if running as root
        log_file_path = pathlib.Path(log_file)

        if not log_file_path.exists():
            log_file_path.touch()
            log_file_path.chmod(0o644)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_formatter)
        file_handler.set_name("ua-file")
        logger.addHandler(file_handler)


def set_event_mode(cmd_args):
    """Set the right event mode based on the args provided"""
    if cmd_args.command in ("attach", "detach", "enable", "disable", "status"):
        event.set_command(cmd_args.command)
        if hasattr(cmd_args, "format"):
            if cmd_args.format == "json":
                event.set_event_mode(event_logger.EventLoggerMode.JSON)
            if cmd_args.format == "yaml":
                event.set_event_mode(event_logger.EventLoggerMode.YAML)


def main_error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            with util.disable_log_to_console():
                logging.error("KeyboardInterrupt")
            print("Interrupt received; exiting.", file=sys.stderr)
            lock.clear_lock_file_if_present()
            sys.exit(1)
        except exceptions.UrlError as exc:
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                tmpl = messages.SSL_VERIFICATION_ERROR_CA_CERTIFICATES
                if util.is_installed("ca-certificates"):
                    tmpl = messages.SSL_VERIFICATION_ERROR_OPENSSL_CONFIG
                msg = tmpl.format(url=exc.url)
                event.error(error_msg=msg.msg, error_code=msg.name)
                event.info(info_msg=msg.msg, file_type=sys.stderr)
            else:
                with util.disable_log_to_console():
                    msg_args = {"url": exc.url, "error": exc}
                    if exc.url:
                        msg_tmpl = (
                            messages.LOG_CONNECTIVITY_ERROR_WITH_URL_TMPL
                        )
                    else:
                        msg_tmpl = messages.LOG_CONNECTIVITY_ERROR_TMPL
                    logging.exception(msg_tmpl.format(**msg_args))

                msg = messages.CONNECTIVITY_ERROR
                event.error(error_msg=msg.msg, error_code=msg.name)
                event.info(info_msg=msg.msg, file_type=sys.stderr)

            lock.clear_lock_file_if_present()
            event.process_events()
            sys.exit(1)
        except exceptions.UserFacingError as exc:
            with util.disable_log_to_console():
                logging.error(exc.msg)
            event.error(error_msg=exc.msg, error_code=exc.msg_code)
            event.info(info_msg="{}".format(exc.msg), file_type=sys.stderr)
            if not isinstance(exc, exceptions.LockHeldError):
                # Only clear the lock if it is ours.
                lock.clear_lock_file_if_present()
            event.process_events()
            sys.exit(exc.exit_code)
        except Exception as e:
            with util.disable_log_to_console():
                logging.exception("Unhandled exception, please file a bug")
            lock.clear_lock_file_if_present()
            event.info(
                info_msg=messages.UNEXPECTED_ERROR.msg, file_type=sys.stderr
            )
            event.error(
                error_msg=getattr(e, "msg", str(e)), error_type="exception"
            )
            event.process_events()
            sys.exit(1)

    return wrapper


@main_error_handler
def main(sys_argv=None):
    if not sys_argv:
        sys_argv = sys.argv
    parser = get_parser()
    cli_arguments = sys_argv[1:]
    if not cli_arguments:
        parser.print_usage()
        print("Try 'ua --help' for more information.")
        sys.exit(1)
    args = parser.parse_args(args=cli_arguments)
    set_event_mode(args)
    cfg = config.UAConfig()

    http_proxy = cfg.http_proxy
    https_proxy = cfg.https_proxy
    util.configure_web_proxy(http_proxy=http_proxy, https_proxy=https_proxy)

    log_level = cfg.log_level
    console_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(console_level, log_level, cfg.log_file)
    logging.debug(
        util.redact_sensitive_logs("Executed with sys.argv: %r" % sys_argv)
    )
    ua_environment = [
        "{}={}".format(k, v)
        for k, v in sorted(os.environ.items())
        if k.lower() in CONFIG_FIELD_ENVVAR_ALLOWLIST
        or k.startswith("UA_FEATURES")
        or k == "UA_CONFIG_FILE"
    ]
    if ua_environment:
        logging.debug(
            util.redact_sensitive_logs(
                "Executed with UA environment variables: %r" % ua_environment
            )
        )
    return args.action(args, cfg=cfg)


if __name__ == "__main__":
    sys.exit(main())
