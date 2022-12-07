"""Client to manage Ubuntu Pro services on a machine."""

import argparse
import json
import logging
import os
import pathlib
import re
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
    apt,
    apt_news,
    config,
    contract,
    daemon,
    defaults,
    entitlements,
    event_logger,
    exceptions,
    lock,
    messages,
    security,
    security_status,
)
from uaclient import status as ua_status
from uaclient import util, version
from uaclient.api.api import call_api
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    _full_auto_attach,
)
from uaclient.api.u.pro.attach.magic.initiate.v1 import _initiate
from uaclient.api.u.pro.attach.magic.revoke.v1 import (
    MagicAttachRevokeOptions,
    _revoke,
)
from uaclient.api.u.pro.attach.magic.wait.v1 import (
    MagicAttachWaitOptions,
    _wait,
)
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.apt import AptProxyScope, setup_apt_proxy
from uaclient.data_types import AttachActionsConfigFile, IncorrectTypeError
from uaclient.defaults import DEFAULT_LOG_FORMAT, PRINT_WRAP_WIDTH
from uaclient.entitlements import (
    create_enable_entitlements_not_found_message,
    entitlements_disable_order,
    get_valid_entitlement_names,
)
from uaclient.entitlements.entitlement_status import (
    ApplicationStatus,
    CanDisableFailure,
    CanEnableFailure,
    CanEnableFailureReason,
)
from uaclient.files import state_files
from uaclient.jobs.update_messaging import (
    refresh_motd,
    update_apt_and_motd_messages,
)

NAME = "pro"

USAGE_TMPL = "{name} {command} [flags]"
EPILOG_TMPL = (
    "Use {name} {command} --help for more information about a command."
)
TRY_HELP = "Try 'pro --help' for more information."

STATUS_HEADER_TMPL = """\
Account: {account}
Subscription: {subscription}
Valid until: {contract_expiry}
Technical support level: {tech_support_level}
"""
UA_AUTH_TOKEN_URL = "https://auth.contracts.canonical.com"

STATUS_FORMATS = ["tabular", "json", "yaml"]

UA_COLLECT_LOGS_FILE = "ua_logs.tar.gz"

NEW_VERSION_NOTICE = (
    "\n"
    + messages.BLUE_INFO
    + """\
 A new version is available: {version}
Please run:
    sudo apt-get install ubuntu-advantage-tools
to get the latest version with new features and bug fixes."""
)

event = event_logger.get_event_logger()


class UAArgumentParser(argparse.ArgumentParser):
    def __init__(
        self,
        prog=None,
        usage=None,
        epilog=None,
        formatter_class=argparse.HelpFormatter,
        base_desc: Optional[str] = None,
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
        # In some cases (e.g. `pro --wrong-flag`) argparse errors out asking
        # for required arguments, but the error message it gives us doesn't
        # include any info about what required args it expects.
        # In python versions prior to 3.9 there is no `exit_on_error` param
        # to ArgumentParser, and as a result, there is no built-in way of
        # catching the ArgumentError exception and handling it ourselves.
        # Instead we just look for the buggy error message.
        # Rather than try to fill in what arguments argparse was hoping for,
        # we just suggest the user runs `--help` which should cover most
        # use cases.
        if message == "the following arguments are required: ":
            message = TRY_HELP
        self.exit(2, message + "\n")

    def print_help(self, file=None, show_all=False):
        if self.base_desc:
            (
                non_beta_services_desc,
                beta_services_desc,
            ) = UAArgumentParser._get_service_descriptions()
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
        root_mode = os.getuid() == 0
        cfg = config.UAConfig(root_mode=root_mode)

        service_info_tmpl = " - {name}: {description}{url}"
        non_beta_services_desc = []
        beta_services_desc = []

        resources = contract.get_available_resources(config.UAConfig())
        for resource in resources:
            try:
                ent_cls = entitlements.entitlement_factory(
                    cfg=cfg, name=resource["name"]
                )
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


def assert_attached(msg_function=None):
    """Decorator asserting attached config.
    :param msg_function: Optional function to generate a custom message
    if raising an UnattachedError
    """

    def wrapper(f):
        @wraps(f)
        def new_f(args, cfg, **kwargs):
            if not cfg.is_attached:
                if msg_function:
                    command = getattr(args, "command", "")
                    service_names = getattr(args, "service", "")
                    msg = msg_function(
                        command=command, service_names=service_names, cfg=cfg
                    )
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
            raise exceptions.AlreadyAttachedError(
                cfg.machine_token_file.account.get("name", "")
            )
        return f(args, cfg=cfg)

    return new_f


def api_parser(parser):
    """Build or extend an arg parser for the api subcommand."""
    parser.prog = "api"
    parser.description = "Calls the Client API endpoints."
    parser.add_argument(
        "endpoint_path", metavar="endpoint", help="API endpoint to call"
    )
    parser.add_argument(
        "--args",
        dest="options",
        default=[],
        nargs="*",
        help="Options to pass to the API endpoint, formatted as key=value",
    )
    return parser


def auto_attach_parser(parser):
    """Build or extend an arg parser for auto-attach subcommand."""
    parser.prog = "auto-attach"
    parser.description = (
        "Automatically attach on an Ubuntu Pro cloud instance."
    )
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser._optionals.title = "Flags"
    return parser


def collect_logs_parser(parser):
    """Build or extend an arg parser for 'collect-logs' subcommand."""
    parser.prog = "collect-logs"
    parser.description = (
        "Collect logs and relevant system information into a tarball."
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
    parser.description = "Set and apply Ubuntu Pro configuration settings"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "key_value_pair",
        help=(
            "key=value pair to configure for Ubuntu Pro services."
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
    parser.description = "Unset Ubuntu Pro configuration setting"
    parser.add_argument(
        "key",
        help=(
            "configuration key to unset from Ubuntu Pro services."
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
    parser.description = "Manage Ubuntu Pro configuration"
    parser._optionals.title = "Flags"
    subparsers = parser.add_subparsers(
        title="Available Commands", dest="command", metavar=""
    )
    parser_show = subparsers.add_parser(
        "show", help="show all Ubuntu Pro configuration setting(s)"
    )
    parser_show.set_defaults(action=action_config_show)
    config_show_parser(parser_show)

    parser_set = subparsers.add_parser(
        "set", help="set Ubuntu Pro configuration setting"
    )
    parser_set.set_defaults(action=action_config_set)
    config_set_parser(parser_set)

    parser_unset = subparsers.add_parser(
        "unset", help="unset Ubuntu Pro configuration setting"
    )
    parser_unset.set_defaults(action=action_config_unset)
    config_unset_parser(parser_unset)
    return parser


def attach_parser(parser):
    """Build or extend an arg parser for attach subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="attach <token>")
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.prog = "attach"
    base_desc = (
        "Attach this machine to Ubuntu Pro with a token obtained"
        " from:\n{}".format(defaults.BASE_UA_URL)
    )
    parser.description = (
        base_desc
        + "\n\n"
        + (
            "When running this command without a token, it will generate "
            "a short code\nand prompt you to attach the machine to your "
            "Ubuntu Pro account using\na web browser."
        )
    )
    parser._optionals.title = "Flags"
    parser.add_argument(
        "token",
        nargs="?",  # action_attach asserts this required argument
        help="token obtained for Ubuntu Pro authentication: {}".format(
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "If used, fix will not actually run but will display"
            " everything that will happen on the machine during the"
            " command."
        ),
    )

    return parser


def security_status_parser(parser):
    """Build or extend an arg parser for security-status subcommand."""
    parser.prog = "security-status"
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = textwrap.dedent(
        """\
        Show security updates for packages in the system, including all
        available Expanded Security Maintenance (ESM) related content.

        Shows counts of how many packages are supported for security updates
        in the system.

        If called with --format json|yaml it shows a summary of the
        installed packages based on the origin:
        - main/restricted/universe/multiverse: packages from the Ubuntu archive
        - esm-infra/esm-apps: packages from the ESM archive
        - third-party: packages installed from non-Ubuntu sources
        - unknown: packages which don't have an installation source (like local
          deb packages or packages for which the source was removed)

        The output contains basic information about Ubuntu Pro. For a
        complete status on Ubuntu Pro services, run 'pro status'.
        """
    )

    parser.add_argument(
        "--format",
        help=("Format for the output"),
        choices=("json", "yaml", "text"),
        default="text",
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--thirdparty",
        help=("List and present information about third-party packages"),
        action="store_true",
    )
    group.add_argument(
        "--unavailable",
        help=("List and present information about unavailable packages"),
        action="store_true",
    )
    group.add_argument(
        "--esm-infra",
        help=("List and present information about esm-infra packages"),
        action="store_true",
    )
    group.add_argument(
        "--esm-apps",
        help=("List and present information about esm-apps packages"),
        action="store_true",
    )
    return parser


def refresh_parser(parser):
    """Build or extend an arg parser for refresh subcommand."""
    parser.prog = "refresh"
    parser.description = (
        "Refresh existing Ubuntu Pro contract and update services."
    )
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="refresh [contract|config|messages]"
    )

    parser._optionals.title = "Flags"
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = textwrap.dedent(
        """\
        Refresh three distinct Ubuntu Pro related artifacts in the system:

        * contract: Update contract details from the server.
        * config:   Reload the config file.
        * messages: Update APT and MOTD messages related to UA.

        You can individually target any of the three specific actions,
        by passing it's target to nome to the command.  If no `target`
        is specified, all targets are refreshed.
        """
    )
    parser.add_argument(
        "target",
        choices=["contract", "config", "messages"],
        nargs="?",
        default=None,
        help="Target to refresh.",
    )
    return parser


def action_security_status(args, *, cfg, **kwargs):
    if args.format == "text":
        if args.thirdparty:
            security_status.list_third_party_packages()
        elif args.unavailable:
            security_status.list_unavailable_packages()
        elif args.esm_infra:
            security_status.list_esm_infra_packages(cfg)
        elif args.esm_apps:
            security_status.list_esm_apps_packages(cfg)
        else:
            security_status.security_status(cfg)
    elif args.format == "json":
        print(
            json.dumps(
                security_status.security_status_dict(cfg),
                sort_keys=True,
                cls=util.DatetimeAwareJSONEncoder,
            )
        )
    else:
        print(
            yaml.safe_dump(
                security_status.security_status_dict(cfg),
                default_flow_style=False,
            )
        )
    return 0


def action_fix(args, *, cfg, **kwargs):
    if not re.match(security.CVE_OR_USN_REGEX, args.security_issue):
        msg = (
            'Error: issue "{}" is not recognized.\n'
            'Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"'
        ).format(args.security_issue)
        raise exceptions.UserFacingError(msg)

    fix_status = security.fix_security_issue_id(
        cfg=cfg,
        issue_id=args.security_issue,
        dry_run=args.dry_run,
    )
    return fix_status.value


def detach_parser(parser):
    """Build or extend an arg parser for detach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="detach")
    parser.usage = usage
    parser.prog = "detach"
    parser.description = "Detach this machine from Ubuntu Pro services."
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


def help_parser(parser, cfg: config.UAConfig):
    """Build or extend an arg parser for help subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="help [service]")
    parser.usage = usage
    parser.prog = "help"
    parser.description = (
        "Provide detailed information about Ubuntu Pro services."
    )
    parser._positionals.title = "Arguments"
    parser.add_argument(
        "service",
        action="store",
        nargs="?",
        help="a service to view help output for. One of: {}".format(
            ", ".join(entitlements.valid_services(cfg=cfg))
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


def enable_parser(parser, cfg: config.UAConfig):
    """Build or extend an arg parser for enable subcommand."""
    usage = USAGE_TMPL.format(
        name=NAME, command="enable <service> [<service>]"
    )
    parser.description = "Enable an Ubuntu Pro service."
    parser.usage = usage
    parser.prog = "enable"
    parser._positionals.title = "Arguments"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            "the name(s) of the Ubuntu Pro services to enable."
            " One of: {}".format(
                ", ".join(entitlements.valid_services(cfg=cfg))
            )
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help="do not prompt for confirmation before performing the enable",
    )
    parser.add_argument(
        "--access-only",
        action="store_true",
        help=(
            "do not auto-install packages. Valid for cc-eal, cis and "
            "realtime-kernel."
        ),
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


def disable_parser(parser, cfg: config.UAConfig):
    """Build or extend an arg parser for disable subcommand."""
    usage = USAGE_TMPL.format(
        name=NAME, command="disable <service> [<service>]"
    )
    parser.description = "Disable an Ubuntu Pro service."
    parser.usage = usage
    parser.prog = "disable"
    parser._positionals.title = "Arguments"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            "the name(s) of the Ubuntu Pro services to disable."
            " One of: {}".format(
                ", ".join(entitlements.valid_services(cfg=cfg))
            )
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


def system_parser(parser):
    """Build or extend an arg parser for system subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="system <command>")
    parser.description = (
        "Output system related information related to Pro services"
    )
    parser.prog = "system"
    parser._optionals.title = "Flags"
    subparsers = parser.add_subparsers(
        title="Available Commands", dest="command", metavar=""
    )
    parser_reboot_required = subparsers.add_parser(
        "reboot-required", help="does the system need to be rebooted"
    )
    parser_reboot_required.set_defaults(action=action_system_reboot_required)
    reboot_required_parser(parser_reboot_required)

    return parser


def reboot_required_parser(parser):
    # This formatter_class ensures that our formatting below isn't lost
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="system reboot-required"
    )
    parser.pro = "reboot-required"
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = textwrap.dedent(
        """\
        Report the current reboot-required status for the machine.

        This command will output one of the three following states
        for the machine regarding reboot:

        * no: The machine doesn't require a reboot
        * yes: The machine requires a reboot
        * yes-kernel-livepatches-applied: There are only kernel related
          packages that require a reboot, but Livepatch has already provided
          patches for the current running kernel. The machine still needs a
          reboot, but you can assess if the reboot can be performed in the
          nearest maintenance window.
        """
    )
    return parser


def status_parser(parser):
    """Build or extend an arg parser for status subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="status")
    parser.usage = usage
    parser.description = (
        "Output the status information for Ubuntu Pro services."
    )
    parser.prog = "status"
    # This formatter_class ensures that our formatting below isn't lost
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = textwrap.dedent(
        """\
        Report current status of Ubuntu Pro services on system.

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
        help="Block waiting on pro to complete",
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


def _print_help_for_subcommand(
    cfg: config.UAConfig, cmd_name: str, subcmd_name: str
):
    parser = get_parser(cfg=cfg)
    subparser = parser._get_positional_actions()[0].choices[cmd_name]
    valid_choices = subparser._get_positional_actions()[0].choices.keys()
    if subcmd_name not in valid_choices:
        parser._get_positional_actions()[0].choices[cmd_name].print_help()
        raise exceptions.UserFacingError(
            "\n<command> must be one of: {}".format(", ".join(valid_choices))
        )


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

        if reason is not None and isinstance(reason, CanDisableFailure):
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
        ua_status.status(cfg=cfg)  # Update the status cache

    return ret


def action_config(args, *, cfg, **kwargs):
    """Perform the config action.

    :return: 0 on success, 1 otherwise
    """
    _print_help_for_subcommand(
        cfg, cmd_name="config", subcmd_name=args.command
    )
    return 0


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
            "{key} {value}".format(
                key=args.key, value=getattr(cfg, args.key, None)
            )
        )
        return 0

    col_width = str(max([len(x) for x in config.UA_CONFIGURABLE_KEYS]) + 1)
    row_tmpl = "{key: <" + col_width + "} {value}"

    for key in config.UA_CONFIGURABLE_KEYS:
        print(row_tmpl.format(key=key, value=getattr(cfg, key, None)))

    if (cfg.global_apt_http_proxy or cfg.global_apt_https_proxy) and (
        cfg.ua_apt_http_proxy or cfg.ua_apt_https_proxy
    ):
        print(
            "\nError: Setting global apt proxy and pro scoped apt proxy at the"
            " same time is unsupported. No apt proxy is set."
        )


@assert_root
def action_config_set(args, *, cfg, **kwargs):
    """Perform the 'config set' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.entitlements.livepatch import configure_livepatch_proxy
    from uaclient.snap import configure_snap_proxy

    parser = get_parser(cfg=cfg)
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
        if livepatch_status == ApplicationStatus.ENABLED:
            configure_livepatch_proxy(**kwargs)
    elif set_key in cfg.ua_scoped_proxy_options:
        protocol_type = set_key.split("_")[2]
        if protocol_type == "http":
            validate_url = util.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = util.PROXY_VALIDATION_APT_HTTPS_URL
        util.validate_proxy(protocol_type, set_value, validate_url)
        unset_current = bool(
            cfg.global_apt_http_proxy or cfg.global_apt_https_proxy
        )
        if unset_current:
            print(
                messages.WARNING_APT_PROXY_OVERWRITE.format(
                    current_proxy="pro scoped apt", previous_proxy="global apt"
                )
            )
        configure_apt_proxy(cfg, AptProxyScope.UACLIENT, set_key, set_value)
        cfg.global_apt_http_proxy = None
        cfg.global_apt_https_proxy = None

    elif set_key in (
        cfg.deprecated_global_scoped_proxy_options
        + cfg.global_scoped_proxy_options
    ):
        # setup_apt_proxy is destructive for unprovided values. Source complete
        # current config values from uaclient.conf before applying set_value.

        protocol_type = "https" if "https" in set_key else "http"
        if protocol_type == "http":
            validate_url = util.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = util.PROXY_VALIDATION_APT_HTTPS_URL

        if set_key in cfg.deprecated_global_scoped_proxy_options:
            print(
                messages.WARNING_APT_PROXY_SETUP.format(
                    protocol_type=protocol_type
                )
            )
            set_key = "global_" + set_key

        util.validate_proxy(protocol_type, set_value, validate_url)

        unset_current = bool(cfg.ua_apt_http_proxy or cfg.ua_apt_https_proxy)

        if unset_current:
            print(
                messages.WARNING_APT_PROXY_OVERWRITE.format(
                    current_proxy="global apt", previous_proxy="pro scoped apt"
                )
            )
        configure_apt_proxy(cfg, AptProxyScope.GLOBAL, set_key, set_value)
        cfg.ua_apt_http_proxy = None
        cfg.ua_apt_https_proxy = None

    elif set_key in (
        "update_messaging_timer",
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
    elif set_key == "apt_news":
        set_value = set_value.lower() == "true"
        if set_value:
            apt_news.update_apt_news(cfg)
        else:
            state_files.apt_news_contents_file.delete()

    setattr(cfg, set_key, set_value)


@assert_root
def action_config_unset(args, *, cfg, **kwargs):
    """Perform the 'config unset' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.apt import AptProxyScope
    from uaclient.entitlements.livepatch import unconfigure_livepatch_proxy
    from uaclient.snap import unconfigure_snap_proxy

    if args.key not in config.UA_CONFIGURABLE_KEYS:
        parser = get_parser(cfg=cfg)
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
        if livepatch_status == ApplicationStatus.ENABLED:
            unconfigure_livepatch_proxy(protocol_type=protocol_type)
    elif args.key in cfg.ua_scoped_proxy_options:
        configure_apt_proxy(cfg, AptProxyScope.UACLIENT, args.key, None)
    elif args.key in (
        cfg.deprecated_global_scoped_proxy_options
        + cfg.global_scoped_proxy_options
    ):
        if args.key in cfg.deprecated_global_scoped_proxy_options:
            protocol_type = "https" if "https" in args.key else "http"
            event.info(
                messages.WARNING_APT_PROXY_SETUP.format(
                    protocol_type=protocol_type
                )
            )
            args.key = "global_" + args.key
        configure_apt_proxy(cfg, AptProxyScope.GLOBAL, args.key, None)

    setattr(cfg, args.key, None)
    return 0


def _create_enable_disable_unattached_msg(command, service_names, cfg):
    """Generates a custom message for enable/disable commands when unattached.

    Takes into consideration if the services exist or not, and notify the user
    accordingly."""
    (entitlements_found, entitlements_not_found) = get_valid_entitlement_names(
        names=service_names, cfg=cfg
    )
    if entitlements_found and entitlements_not_found:
        msg = messages.MIXED_SERVICES_FAILURE_UNATTACHED
        msg = msg.format(
            valid_service=", ".join(entitlements_found),
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="",
        )
    elif entitlements_found:
        msg = messages.VALID_SERVICE_FAILURE_UNATTACHED.format(
            valid_service=", ".join(entitlements_found)
        )
    else:
        msg = messages.INVALID_SERVICE_OP_FAILURE.format(
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="See {}".format(defaults.BASE_UA_URL),
        )
    return msg


@verify_json_format_args
@assert_root
@assert_attached(_create_enable_disable_unattached_msg)
@assert_lock_file("pro disable")
def action_disable(args, *, cfg, **kwargs):
    """Perform the disable action on a list of entitlements.

    @return: 0 on success, 1 otherwise
    """
    names = getattr(args, "service", [])
    entitlements_found, entitlements_not_found = get_valid_entitlement_names(
        names, cfg
    )
    ret = True

    for ent_name in entitlements_found:
        ent_cls = entitlements.entitlement_factory(cfg=cfg, name=ent_name)
        ent = ent_cls(cfg, assume_yes=args.assume_yes)

        ret &= _perform_disable(ent, cfg, assume_yes=args.assume_yes)

    if entitlements_not_found:
        valid_names = (
            "Try "
            + ", ".join(entitlements.valid_services(cfg=cfg, allow_beta=True))
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
            invalid_service=", ".join(entitlements_not_found),
            service_msg=service_msg,
        )

    event.process_events()
    return 0 if ret else 1


@verify_json_format_args
@assert_root
@assert_attached(_create_enable_disable_unattached_msg)
@assert_lock_file("pro enable")
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
        names, cfg
    )
    ret = True
    for ent_name in entitlements_found:
        try:
            ent_ret, reason = actions.enable_entitlement_by_name(
                cfg,
                ent_name,
                assume_yes=args.assume_yes,
                allow_beta=args.beta,
                access_only=args.access_only,
            )
            ua_status.status(cfg=cfg)  # Update the status cache

            if (
                not ent_ret
                and reason is not None
                and isinstance(reason, CanEnableFailure)
            ):
                if reason.message is not None:
                    event.info(reason.message.msg)
                    event.error(
                        error_msg=reason.message.msg,
                        error_code=reason.message.name,
                        service=ent_name,
                    )
                if reason.reason == CanEnableFailureReason.IS_BETA:
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
        msg = create_enable_entitlements_not_found_message(
            entitlements_not_found, cfg=cfg, allow_beta=args.beta
        )
        event.services_failed(entitlements_not_found)
        raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)

    event.process_events()
    return 0 if ret else 1


@verify_json_format_args
@assert_root
@assert_attached()
@assert_lock_file("pro detach")
def action_detach(args, *, cfg) -> int:
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    ret = _detach(cfg, assume_yes=args.assume_yes)
    if ret == 0:
        daemon.start()
    event.process_events()
    return ret


def _detach(cfg: config.UAConfig, assume_yes: bool) -> int:
    """Detach the machine from the active Ubuntu Pro subscription,

    :param cfg: a ``config.UAConfig`` instance
    :param assume_yes: Assume a yes answer to any prompts requested.
         In this case, it means automatically disable any service during
         detach.

    @return: 0 on success, 1 otherwise
    """
    to_disable = []
    for ent_name in entitlements_disable_order(cfg):
        try:
            ent_cls = entitlements.entitlement_factory(cfg=cfg, name=ent_name)
        except exceptions.EntitlementNotFoundError:
            continue

        ent = ent_cls(cfg=cfg, assume_yes=assume_yes)
        # For detach, we should not consider that a service
        # cannot be disabled because of dependent services,
        # since we are going to disable all of them anyway
        ret, _ = ent.can_disable(ignore_dependent_services=True)
        if ret:
            to_disable.append(ent)

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
    cfg.machine_token_file.delete()
    update_apt_and_motd_messages(cfg)
    event.info(messages.DETACH_SUCCESS)
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

    daemon.stop()
    daemon.cleanup(cfg)

    status, _ret = actions.status(cfg)
    output = ua_status.format_tabular(status)
    event.info(util.handle_unicode_characters(output))
    event.process_events()


def action_api(args, *, cfg):
    result = call_api(args.endpoint_path, args.options, cfg)
    print(result.to_json())
    return 0 if result.result == "success" else 1


@assert_root
def action_auto_attach(args, *, cfg: config.UAConfig) -> int:
    try:
        _full_auto_attach(
            FullAutoAttachOptions(),
            cfg=cfg,
            mode=event_logger.EventLoggerMode.CLI,
        )
    except exceptions.UrlError:
        event.info(messages.ATTACH_FAILURE.msg)
        return 1
    else:
        _post_cli_attach(cfg)
        return 0


def _magic_attach(args, *, cfg, **kwargs):
    if args.format == "json":
        raise exceptions.MagicAttachInvalidParam(
            param="--format",
            value=args.format,
        )

    event.info("Initiating attach operation...")
    initiate_resp = _initiate(cfg=cfg)

    event.info("\nPlease sign in to your Ubuntu Pro account at this link:")
    event.info("https://ubuntu.com/pro/attach")
    event.info(
        "And provide the following code: {}{}{}".format(
            messages.TxtColor.BOLD,
            initiate_resp.user_code,
            messages.TxtColor.ENDC,
        )
    )

    wait_options = MagicAttachWaitOptions(magic_token=initiate_resp.token)

    try:
        wait_resp = _wait(options=wait_options, cfg=cfg)
    except exceptions.MagicAttachTokenError as e:
        event.info("Failed to perform magic-attach")

        revoke_options = MagicAttachRevokeOptions(
            magic_token=initiate_resp.token
        )
        _revoke(options=revoke_options, cfg=cfg)
        raise e

    event.info("\nAttaching the machine...")
    return wait_resp.contract_token


@assert_not_attached
@assert_root
@assert_lock_file("pro attach")
def action_attach(args, *, cfg):
    if args.token and args.attach_config:
        raise exceptions.UserFacingError(
            msg=messages.ATTACH_TOKEN_ARG_XOR_CONFIG.msg,
            msg_code=messages.ATTACH_TOKEN_ARG_XOR_CONFIG.name,
        )
    elif not args.token and not args.attach_config:
        token = _magic_attach(args, cfg=cfg)
        enable_services_override = None
    elif args.token:
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
        raise exceptions.AttachError()
    else:
        ret = 0
        if enable_services_override is not None and args.auto_enable:
            found, not_found = get_valid_entitlement_names(
                enable_services_override, cfg
            )
            for name in found:
                ent_ret, reason = actions.enable_entitlement_by_name(
                    cfg, name, assume_yes=True, allow_beta=True
                )
                if not ent_ret:
                    ret = 1
                    if (
                        reason is not None
                        and isinstance(reason, CanEnableFailure)
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
                msg = create_enable_entitlements_not_found_message(
                    not_found, cfg=cfg, allow_beta=True
                )
                event.info(msg.msg, file_type=sys.stderr)
                event.error(error_msg=msg.msg, error_code=msg.name)
                ret = 1
        _post_cli_attach(cfg)
        return ret


def action_collect_logs(args, *, cfg: config.UAConfig):
    output_file = args.output or UA_COLLECT_LOGS_FILE
    with tempfile.TemporaryDirectory() as output_dir:
        actions.collect_logs(cfg, output_dir)
        try:
            with tarfile.open(output_file, "w:gz") as results:
                results.add(output_dir, arcname="logs/")
        except PermissionError as e:
            logging.error(e)
            return 1
    return 0


def get_parser(cfg: config.UAConfig):
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
        version=version.get_version(),
        help="show version of {}".format(NAME),
    )
    parser._optionals.title = "Flags"
    subparsers = parser.add_subparsers(
        title="Available Commands", dest="command", metavar=""
    )
    subparsers.required = True
    parser_attach = subparsers.add_parser(
        "attach",
        help="attach this machine to an Ubuntu Pro subscription",
    )
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)

    parser_api = subparsers.add_parser(
        "api",
        help="Calls the Client API endpoints.",
    )
    api_parser(parser_api)
    parser_api.set_defaults(action=action_api)

    parser_auto_attach = subparsers.add_parser(
        "auto-attach", help="automatically attach on supported platforms"
    )
    auto_attach_parser(parser_auto_attach)
    parser_auto_attach.set_defaults(action=action_auto_attach)

    parser_collect_logs = subparsers.add_parser(
        "collect-logs", help="collect Pro logs and debug information"
    )
    collect_logs_parser(parser_collect_logs)
    parser_collect_logs.set_defaults(action=action_collect_logs)

    parser_config = subparsers.add_parser(
        "config", help="manage Ubuntu Pro configuration on this machine"
    )
    config_parser(parser_config)
    parser_config.set_defaults(action=action_config)

    parser_detach = subparsers.add_parser(
        "detach",
        help="remove this machine from an Ubuntu Pro subscription",
    )
    detach_parser(parser_detach)
    parser_detach.set_defaults(action=action_detach)

    parser_disable = subparsers.add_parser(
        "disable",
        help="disable a specific Ubuntu Pro service on this machine",
    )
    disable_parser(parser_disable, cfg=cfg)
    parser_disable.set_defaults(action=action_disable)

    parser_enable = subparsers.add_parser(
        "enable",
        help="enable a specific Ubuntu Pro service on this machine",
    )
    enable_parser(parser_enable, cfg=cfg)
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
        help="show detailed information about Ubuntu Pro services",
    )
    help_parser(parser_help, cfg=cfg)
    parser_help.set_defaults(action=action_help)

    parser_refresh = subparsers.add_parser(
        "refresh", help="refresh Ubuntu Pro services"
    )
    parser_refresh.set_defaults(action=action_refresh)
    refresh_parser(parser_refresh)

    parser_status = subparsers.add_parser(
        "status", help="current status of all Ubuntu Pro services"
    )
    parser_status.set_defaults(action=action_status)
    status_parser(parser_status)

    parser_version = subparsers.add_parser(
        "version", help="show version of {}".format(NAME)
    )
    parser_version.set_defaults(action=print_version)

    parser_system = subparsers.add_parser(
        "system", help="show system information related to Pro services"
    )
    parser_system.set_defaults(action=action_system)
    system_parser(parser_system)

    return parser


def action_status(args, *, cfg):
    if not cfg:
        cfg = config.UAConfig()
    show_all = args.all if args else False
    token = args.simulate_with_token if args else None
    active_value = ua_status.UserFacingConfigStatus.ACTIVE.value
    if cfg.is_attached:
        try:
            if contract.is_contract_changed(cfg):
                cfg.notice_file.try_add(
                    "", messages.NOTICE_REFRESH_CONTRACT_WARNING
                )
            else:
                cfg.notice_file.try_remove(
                    "", messages.NOTICE_REFRESH_CONTRACT_WARNING
                )
        except Exception as e:
            with util.disable_log_to_console():
                err_msg = messages.UPDATE_CHECK_CONTRACT_FAILURE.format(
                    reason=str(e)
                )
                logging.warning(err_msg)
                event.warning(err_msg)
    status, ret = actions.status(
        cfg, simulate_with_token=token, show_all=show_all
    )
    config_active = bool(status["execution_status"] == active_value)

    if args and args.wait and config_active:
        while status["execution_status"] == active_value:
            event.info(".", end="")
            time.sleep(1)
            status, ret = actions.status(
                cfg,
                simulate_with_token=token,
                show_all=show_all,
            )
        event.info("")

    event.set_output_content(status)
    output = ua_status.format_tabular(status)
    event.info(util.handle_unicode_characters(output))
    event.process_events()
    return ret


def action_system(args, *, cfg, **kwargs):
    """Perform the system action.

    :return: 0 on success, 1 otherwise
    """
    _print_help_for_subcommand(
        cfg, cmd_name="system", subcmd_name=args.command
    )
    return 0


def action_system_reboot_required(args, *, cfg: config.UAConfig):
    result = _reboot_required(cfg)
    event.info(result.reboot_required)
    return 0


def print_version(_args=None, cfg=None):
    print(version.get_version())


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


def _action_refresh_messages(_args, cfg: config.UAConfig):
    # Not performing any exception handling here since both of these
    # functions should raise UserFacingError exceptions, which are
    # covered by the main_error_handler decorator
    try:
        update_apt_and_motd_messages(cfg)
        refresh_motd()
        if cfg.apt_news:
            apt_news.update_apt_news(cfg)
    except Exception as exc:
        with util.disable_log_to_console():
            logging.exception(exc)
        raise exceptions.UserFacingError(messages.REFRESH_MESSAGES_FAILURE)
    else:
        print(messages.REFRESH_MESSAGES_SUCCESS)


@assert_root
@assert_lock_file("pro refresh")
def action_refresh(args, *, cfg: config.UAConfig):
    if args.target is None or args.target == "config":
        _action_refresh_config(args, cfg)

    if args.target is None or args.target == "contract":
        _action_refresh_contract(args, cfg)
        cfg.notice_file.remove("", messages.NOTICE_REFRESH_CONTRACT_WARNING)

    if args.target is None or args.target == "messages":
        _action_refresh_messages(args, cfg)

    return 0


def configure_apt_proxy(
    cfg: config.UAConfig,
    scope: AptProxyScope,
    set_key: str,
    set_value: Optional[str],
) -> None:
    """
    Handles setting part the apt proxies - global and uaclient scoped proxies
    """
    if scope == AptProxyScope.GLOBAL:
        http_proxy = cfg.global_apt_http_proxy
        https_proxy = cfg.global_apt_https_proxy
    elif scope == AptProxyScope.UACLIENT:
        http_proxy = cfg.ua_apt_http_proxy
        https_proxy = cfg.ua_apt_https_proxy
    if "https" in set_key:
        https_proxy = set_value
    else:
        http_proxy = set_value
    setup_apt_proxy(
        http_proxy=http_proxy, https_proxy=https_proxy, proxy_scope=scope
    )


def action_help(args, *, cfg):
    service = args.service
    show_all = args.all

    if not service:
        get_parser(cfg=cfg).print_help(show_all=show_all)
        return 0

    if not cfg:
        cfg = config.UAConfig()

    help_response = ua_status.help(cfg, service)

    if args.format == "json":
        print(json.dumps(help_response))
    else:
        for key, value in help_response.items():
            print("{}:\n{}\n".format(key.title(), value))

    return 0


def _warn_about_new_version(cmd_args=None) -> None:
    # If no args, then it was called from the main error handler.
    # We don't want to show this text for the "api" CLI output,
    # or for --format json|yaml
    if (
        cmd_args
        and cmd_args.command == "api"
        or getattr(cmd_args, "format", "") in ("json", "yaml")
    ):
        return

    new_version = version.check_for_new_version()
    if new_version:
        logging.warning(NEW_VERSION_NOTICE.format(version=new_version))


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
                if apt.is_installed("ca-certificates"):
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

            _warn_about_new_version()

            sys.exit(1)
        except exceptions.UserFacingError as exc:
            with util.disable_log_to_console():
                logging.error(exc.msg)

            event.error(
                error_msg=exc.msg,
                error_code=exc.msg_code,
                additional_info=exc.additional_info,
            )
            event.info(info_msg="{}".format(exc.msg), file_type=sys.stderr)
            if not isinstance(exc, exceptions.LockHeldError):
                # Only clear the lock if it is ours.
                lock.clear_lock_file_if_present()
            event.process_events()

            _warn_about_new_version()

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

            _warn_about_new_version()

            sys.exit(1)

    return wrapper


@main_error_handler
def main(sys_argv=None):
    if not sys_argv:
        sys_argv = sys.argv
    is_root = os.getuid() == 0
    cfg = config.UAConfig(root_mode=is_root)
    parser = get_parser(cfg=cfg)
    cli_arguments = sys_argv[1:]
    if not cli_arguments:
        parser.print_usage()
        print(TRY_HELP)
        sys.exit(1)
    args = parser.parse_args(args=cli_arguments)
    set_event_mode(args)

    http_proxy = cfg.http_proxy
    https_proxy = cfg.https_proxy
    util.configure_web_proxy(http_proxy=http_proxy, https_proxy=https_proxy)

    log_level = cfg.log_level
    console_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(console_level, log_level, cfg.log_file)

    logging.debug(
        util.redact_sensitive_logs("Executed with sys.argv: %r" % sys_argv)
    )

    with util.disable_log_to_console():
        cfg.warn_about_invalid_keys()

    pro_environment = [
        "{}={}".format(k, v)
        for k, v in sorted(util.get_pro_environment().items())
    ]
    if pro_environment:
        logging.debug(
            util.redact_sensitive_logs(
                "Executed with environment variables: %r" % pro_environment
            )
        )
    return_value = args.action(args, cfg=cfg)

    _warn_about_new_version(args)

    return return_value


if __name__ == "__main__":
    sys.exit(main())
