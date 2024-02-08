"""Client to manage Ubuntu Pro services on a machine."""

import argparse
import json
import logging
import pathlib
import sys
import tarfile
import tempfile
import textwrap
import time
from functools import wraps
from typing import List, Optional, Tuple  # noqa

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
    http,
    lock,
)
from uaclient import log as pro_log
from uaclient import messages, security_status
from uaclient import status as ua_status
from uaclient import timer, util, version
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
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.apt import AptProxyScope, setup_apt_proxy
from uaclient.cli.constants import NAME, USAGE_TMPL
from uaclient.cli.fix import set_fix_parser
from uaclient.data_types import AttachActionsConfigFile, IncorrectTypeError
from uaclient.defaults import PRINT_WRAP_WIDTH
from uaclient.entitlements import (
    create_enable_entitlements_not_found_error,
    entitlements_disable_order,
    get_valid_entitlement_names,
)
from uaclient.entitlements.entitlement_status import (
    ApplicationStatus,
    CanDisableFailure,
    CanEnableFailure,
    CanEnableFailureReason,
)
from uaclient.files import notices, state_files
from uaclient.files.notices import Notice
from uaclient.log import JsonArrayFormatter
from uaclient.timer.update_messaging import refresh_motd, update_motd_messages
from uaclient.yaml import safe_dump, safe_load

UA_AUTH_TOKEN_URL = "https://auth.contracts.canonical.com"

STATUS_FORMATS = ["tabular", "json", "yaml"]

UA_COLLECT_LOGS_FILE = "ua_logs.tar.gz"

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


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
            message = messages.CLI_TRY_HELP
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

            self.description += "\n\n" + messages.PRO_HELP_SERVICE_INFO

        super().print_help(file=file)

    @staticmethod
    def _get_service_descriptions() -> Tuple[List[str], List[str]]:
        cfg = config.UAConfig()

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
            with lock.RetryLock(
                cfg=cfg, lock_holder=lock_holder, sleep_time=1
            ):
                retval = f(*args, cfg=cfg, **kwargs)
            return retval

        return new_f

    return wrapper


def assert_root(f):
    """Decorator asserting root user"""

    @wraps(f)
    def new_f(*args, **kwargs):
        if not util.we_are_currently_root():
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
            raise exceptions.CLIJSONFormatRequireAssumeYes()
        else:
            return f(cmd_args, *args, **kwargs)

    return new_f


def assert_attached(raise_custom_error_function=None):
    """Decorator asserting attached config.
    :param msg_function: Optional function to generate a custom message
    if raising an UnattachedError
    """

    def wrapper(f):
        @wraps(f)
        def new_f(args, cfg, **kwargs):
            if not _is_attached(cfg).is_attached:
                if raise_custom_error_function:
                    command = getattr(args, "command", "")
                    service_names = getattr(args, "service", "")
                    raise_custom_error_function(
                        command=command, service_names=service_names, cfg=cfg
                    )
                else:
                    raise exceptions.UnattachedError()
            return f(args, cfg=cfg, **kwargs)

        return new_f

    return wrapper


def assert_not_attached(f):
    """Decorator asserting unattached config."""

    @wraps(f)
    def new_f(args, cfg, **kwargs):
        if _is_attached(cfg).is_attached:
            raise exceptions.AlreadyAttachedError(
                account_name=cfg.machine_token_file.account.get("name", "")
            )
        return f(args, cfg=cfg, **kwargs)

    return new_f


def api_parser(parser):
    """Build or extend an arg parser for the api subcommand."""
    parser.prog = "api"
    parser.description = messages.CLI_API_DESC
    parser.add_argument(
        "endpoint_path", metavar="endpoint", help=messages.CLI_API_ENDPOINT
    )
    parser.add_argument(
        "--args",
        dest="options",
        default=[],
        nargs="*",
        help=messages.CLI_API_ARGS,
    )
    parser.add_argument(
        "--data", dest="data", default="", help=messages.CLI_API_DATA
    )
    return parser


def auto_attach_parser(parser):
    """Build or extend an arg parser for auto-attach subcommand."""
    parser.prog = "auto-attach"
    parser.description = messages.CLI_AUTO_ATTACH_DESC
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser._optionals.title = messages.CLI_FLAGS
    return parser


def collect_logs_parser(parser):
    """Build or extend an arg parser for 'collect-logs' subcommand."""
    parser.prog = "collect-logs"
    parser.description = messages.CLI_COLLECT_LOGS_DESC
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser.add_argument(
        "-o",
        "--output",
        help=messages.CLI_COLLECT_LOGS_OUTPUT,
    )
    return parser


def config_show_parser(parser, parent_command: str):
    """Build or extend an arg parser for 'config show' subcommand."""
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="{} show [key]".format(parent_command)
    )
    parser.prog = "show"
    parser.description = messages.CLI_CONFIG_SHOW_DESC
    parser.add_argument(
        "key",
        nargs="?",  # action_config_show handles this optional argument
        help=messages.CLI_CONFIG_SHOW_KEY,
    )
    return parser


def config_set_parser(parser, parent_command: str):
    """Build or extend an arg parser for 'config set' subcommand."""
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="{} set <key>=<value>".format(parent_command)
    )
    parser.prog = "aset"
    parser.description = messages.CLI_CONFIG_SET_DESC
    parser._optionals.title = messages.CLI_FLAGS
    parser.add_argument(
        "key_value_pair",
        help=(
            messages.CLI_CONFIG_SET_KEY_VALUE.format(
                options=", ".join(config.UA_CONFIGURABLE_KEYS)
            )
        ),
    )
    return parser


def config_unset_parser(parser, parent_command: str):
    """Build or extend an arg parser for 'config unset' subcommand."""
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="{} unset <key>".format(parent_command)
    )
    parser.prog = "unset"
    parser.description = messages.CLI_CONFIG_UNSET_DESC
    parser.add_argument(
        "key",
        help=(
            messages.CLI_CONFIG_UNSET_KEY.format(
                options=", ".join(config.UA_CONFIGURABLE_KEYS)
            )
        ),
        metavar="key",
    )
    parser._optionals.title = messages.CLI_FLAGS
    return parser


def config_parser(parser):
    """Build or extend an arg parser for config subcommand."""
    command = "config"
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="{} <command>".format(command)
    )
    parser.prog = command
    parser.description = messages.CLI_CONFIG_DESC
    parser._optionals.title = messages.CLI_FLAGS
    subparsers = parser.add_subparsers(
        title=messages.CLI_AVAILABLE_COMMANDS, dest="command", metavar=""
    )
    parser_show = subparsers.add_parser(
        "show", help=messages.CLI_CONFIG_SHOW_DESC
    )
    parser_show.set_defaults(action=action_config_show)
    config_show_parser(parser_show, parent_command=command)

    parser_set = subparsers.add_parser(
        "set", help=messages.CLI_CONFIG_SET_DESC
    )
    parser_set.set_defaults(action=action_config_set)
    config_set_parser(parser_set, parent_command=command)

    parser_unset = subparsers.add_parser(
        "unset", help=messages.CLI_CONFIG_UNSET_DESC
    )
    parser_unset.set_defaults(action=action_config_unset)
    config_unset_parser(parser_unset, parent_command=command)
    return parser


def attach_parser(parser):
    """Build or extend an arg parser for attach subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="attach <token>")
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.prog = "attach"
    parser.description = messages.CLI_ATTACH_DESC
    parser._optionals.title = messages.CLI_FLAGS
    parser.add_argument("token", nargs="?", help=messages.CLI_ATTACH_TOKEN)
    parser.add_argument(
        "--no-auto-enable",
        action="store_false",
        dest="auto_enable",
        help=messages.CLI_ATTACH_NO_AUTO_ENABLE,
    )
    parser.add_argument(
        "--attach-config",
        type=argparse.FileType("r"),
        help=messages.CLI_ATTACH_ATTACH_CONFIG,
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=messages.CLI_FORMAT_DESC.format(default="cli"),
    )
    return parser


def security_status_parser(parser):
    """Build or extend an arg parser for security-status subcommand."""
    parser.prog = "security-status"
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = messages.CLI_SS_DESC

    parser.add_argument(
        "--format",
        help=messages.CLI_FORMAT_DESC.format(default="text"),
        choices=("json", "yaml", "text"),
        default="text",
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--thirdparty",
        help=messages.CLI_SS_THIRDPARTY,
        action="store_true",
    )
    group.add_argument(
        "--unavailable",
        help=messages.CLI_SS_UNAVAILABLE,
        action="store_true",
    )
    group.add_argument(
        "--esm-infra",
        help=messages.CLI_SS_ESM_INFRA,
        action="store_true",
    )
    group.add_argument(
        "--esm-apps",
        help=messages.CLI_SS_ESM_APPS,
        action="store_true",
    )
    return parser


def refresh_parser(parser):
    """Build or extend an arg parser for refresh subcommand."""
    parser.prog = "refresh"
    parser.usage = USAGE_TMPL.format(
        name=NAME, command="refresh [contract|config|messages]"
    )

    parser._optionals.title = messages.CLI_FLAGS
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = messages.CLI_REFRESH_DESC
    parser.add_argument(
        "target",
        choices=["contract", "config", "messages"],
        nargs="?",
        default=None,
        help=messages.CLI_REFRESH_TARGET,
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
            safe_dump(
                security_status.security_status_dict(cfg),
                default_flow_style=False,
            )
        )
    return 0


def detach_parser(parser):
    """Build or extend an arg parser for detach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="detach")
    parser.usage = usage
    parser.prog = "detach"
    parser.description = messages.CLI_DETACH_DESC
    parser._optionals.title = "Flags"
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help=messages.CLI_ASSUME_YES.format(command="detach"),
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=messages.CLI_FORMAT_DESC.format(default="cli"),
    )
    return parser


def help_parser(parser, cfg: config.UAConfig):
    """Build or extend an arg parser for help subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="help [service]")
    parser.usage = usage
    parser.prog = "help"
    parser.description = messages.CLI_HELP_DESC
    parser._positionals.title = messages.CLI_ARGS
    parser.add_argument(
        "service",
        action="store",
        nargs="?",
        help=messages.CLI_HELP_SERVICE.format(
            options=", ".join(entitlements.valid_services(cfg=cfg))
        ),
    )

    parser.add_argument(
        "--format",
        action="store",
        choices=STATUS_FORMATS,
        default=STATUS_FORMATS[0],
        help=(messages.CLI_FORMAT_DESC.format(default=STATUS_FORMATS[0])),
    )

    parser.add_argument(
        "--all", action="store_true", help=messages.CLI_HELP_ALL
    )

    return parser


def enable_parser(parser, cfg: config.UAConfig):
    """Build or extend an arg parser for enable subcommand."""
    usage = USAGE_TMPL.format(
        name=NAME, command="enable <service> [<service>]"
    )
    parser.description = messages.CLI_ENABLE_DESC
    parser.usage = usage
    parser.prog = "enable"
    parser._positionals.title = messages.CLI_ARGS
    parser._optionals.title = messages.CLI_FLAGS
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            messages.CLI_ENABLE_SERVICE.format(
                options=", ".join(entitlements.valid_services(cfg=cfg))
            )
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help=messages.CLI_ASSUME_YES.format(command="enable"),
    )
    parser.add_argument(
        "--access-only",
        action="store_true",
        help=messages.CLI_ENABLE_ACCESS_ONLY,
    )
    parser.add_argument(
        "--beta", action="store_true", help=messages.CLI_ENABLE_BETA
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=messages.CLI_FORMAT_DESC.format(default="cli"),
    )
    parser.add_argument(
        "--variant", action="store", help=messages.CLI_ENABLE_VARIANT
    )
    return parser


def disable_parser(parser, cfg: config.UAConfig):
    """Build or extend an arg parser for disable subcommand."""
    usage = USAGE_TMPL.format(
        name=NAME, command="disable <service> [<service>]"
    )
    parser.description = messages.CLI_DISABLE_DESC
    parser.usage = usage
    parser.prog = "disable"
    parser._positionals.title = messages.CLI_ARGS
    parser._optionals.title = messages.CLI_FLAGS
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            messages.CLI_DISABLE_SERVICE.format(
                options=", ".join(entitlements.valid_services(cfg=cfg))
            )
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help=messages.CLI_ASSUME_YES.format(command="disable"),
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=messages.CLI_FORMAT_DESC.format(default="cli"),
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help=messages.CLI_PURGE,
    )
    return parser


def system_parser(parser):
    """Build or extend an arg parser for system subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="system <command>")
    parser.description = messages.CLI_SYSTEM_DESC
    parser.prog = "system"
    parser._optionals.title = messages.CLI_FLAGS
    subparsers = parser.add_subparsers(
        title=messages.CLI_AVAILABLE_COMMANDS, dest="command", metavar=""
    )
    parser_reboot_required = subparsers.add_parser(
        "reboot-required", help=messages.CLI_SYSTEM_REBOOT_REQUIRED
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
    parser.description = messages.CLI_SYSTEM_REBOOT_REQUIRED_DESC
    return parser


def status_parser(parser):
    """Build or extend an arg parser for status subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="status")
    parser.usage = usage
    parser.prog = "status"
    # This formatter_class ensures that our formatting below isn't lost
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = messages.CLI_STATUS_DESC

    parser.add_argument(
        "--wait",
        action="store_true",
        default=False,
        help=messages.CLI_STATUS_WAIT,
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=STATUS_FORMATS,
        default=STATUS_FORMATS[0],
        help=(messages.CLI_FORMAT_DESC.format(default=STATUS_FORMATS[0])),
    )
    parser.add_argument(
        "--simulate-with-token",
        metavar="TOKEN",
        action="store",
        help=messages.CLI_STATUS_SIMULATE_WITH_TOKEN,
    )
    parser.add_argument(
        "--all", action="store_true", help=messages.CLI_STATUS_ALL
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
        raise exceptions.InvalidArgChoice(
            arg="<command>", choices=", ".join(valid_choices)
        )


def _perform_disable(entitlement, cfg, *, assume_yes, update_status=True):
    """Perform the disable action on a named entitlement.

    :param entitlement_name: the name of the entitlement to enable
    :param cfg: the UAConfig to pass to the entitlement
    :param assume_yes:
        Assume a yes response for any prompts during service enable

    @return: True on success, False otherwise
    """
    # Make sure we have the correct variant of the service
    # This can affect what packages get uninstalled
    variant = entitlement.enabled_variant
    if variant is not None:
        entitlement = variant

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
    :raise UbuntuProError: on invalid keys
    """
    if args.key:  # limit reporting config to a single config key
        if args.key not in config.UA_CONFIGURABLE_KEYS:
            raise exceptions.InvalidArgChoice(
                arg="'{}'".format(args.key),
                choices=", ".join(config.UA_CONFIGURABLE_KEYS),
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
        print(messages.CLI_CONFIG_GLOBAL_XOR_UA_PROXY)


@assert_root
def action_config_set(args, *, cfg, **kwargs):
    """Perform the 'config set' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.livepatch import configure_livepatch_proxy
    from uaclient.snap import configure_snap_proxy

    parser = get_parser(cfg=cfg)
    config_parser = parser._get_positional_actions()[0].choices["config"]
    subparser = config_parser._get_positional_actions()[0].choices["set"]
    try:
        set_key, set_value = args.key_value_pair.split("=")
    except ValueError:
        subparser.print_help()
        raise exceptions.GenericInvalidFormat(
            expected="<key>=<value>", actual=args.key_value_pair
        )
    if set_key not in config.UA_CONFIGURABLE_KEYS:
        subparser.print_help()
        raise exceptions.InvalidArgChoice(
            arg="<key>", choices=", ".join(config.UA_CONFIGURABLE_KEYS)
        )
    if set_key in ("http_proxy", "https_proxy"):
        protocol_type = set_key.split("_")[0]
        if protocol_type == "http":
            validate_url = http.PROXY_VALIDATION_SNAP_HTTP_URL
        else:
            validate_url = http.PROXY_VALIDATION_SNAP_HTTPS_URL
        http.validate_proxy(protocol_type, set_value, validate_url)

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
            validate_url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = http.PROXY_VALIDATION_APT_HTTPS_URL
        http.validate_proxy(protocol_type, set_value, validate_url)
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
            validate_url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = http.PROXY_VALIDATION_APT_HTTPS_URL

        if set_key in cfg.deprecated_global_scoped_proxy_options:
            print(
                messages.WARNING_CONFIG_FIELD_RENAME.format(
                    old="apt_{}_proxy".format(protocol_type),
                    new="global_apt_{}_proxy".format(protocol_type),
                )
            )
            set_key = "global_" + set_key

        http.validate_proxy(protocol_type, set_value, validate_url)

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
            raise exceptions.InvalidPosIntConfigValue(
                key=set_key, value=set_value
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
    from uaclient.livepatch import unconfigure_livepatch_proxy
    from uaclient.snap import unconfigure_snap_proxy

    if args.key not in config.UA_CONFIGURABLE_KEYS:
        parser = get_parser(cfg=cfg)
        config_parser = parser._get_positional_actions()[0].choices["config"]
        subparser = config_parser._get_positional_actions()[0].choices["unset"]
        subparser.print_help()
        raise exceptions.InvalidArgChoice(
            arg="<key>", choices=", ".join(config.UA_CONFIGURABLE_KEYS)
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
                messages.WARNING_CONFIG_FIELD_RENAME.format(
                    old="apt_{}_proxy".format(protocol_type),
                    new="global_apt_{}_proxy".format(protocol_type),
                )
            )
            args.key = "global_" + args.key
        configure_apt_proxy(cfg, AptProxyScope.GLOBAL, args.key, None)

    setattr(cfg, args.key, None)
    return 0


def _raise_enable_disable_unattached_error(command, service_names, cfg):
    """Raises a custom error for enable/disable commands when unattached.

    Takes into consideration if the services exist or not, and notify the user
    accordingly."""
    (entitlements_found, entitlements_not_found) = get_valid_entitlement_names(
        names=service_names, cfg=cfg
    )
    if entitlements_found and entitlements_not_found:
        raise exceptions.UnattachedMixedServicesError(
            valid_service=", ".join(entitlements_found),
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="",
        )
    elif entitlements_found:
        raise exceptions.UnattachedValidServicesError(
            valid_service=", ".join(entitlements_found)
        )
    else:
        raise exceptions.UnattachedInvalidServicesError(
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="",
        )


@verify_json_format_args
@assert_root
@assert_attached(_raise_enable_disable_unattached_error)
@assert_lock_file("pro disable")
def action_disable(args, *, cfg, **kwargs):
    """Perform the disable action on a list of entitlements.

    @return: 0 on success, 1 otherwise
    """
    if args.purge and args.assume_yes:
        raise exceptions.InvalidOptionCombination(
            option1="--purge", option2="--assume-yes"
        )

    names = getattr(args, "service", [])
    entitlements_found, entitlements_not_found = get_valid_entitlement_names(
        names, cfg
    )
    ret = True

    for ent_name in entitlements_found:
        ent_cls = entitlements.entitlement_factory(cfg=cfg, name=ent_name)
        ent = ent_cls(cfg, assume_yes=args.assume_yes, purge=args.purge)

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
        raise exceptions.InvalidServiceOpError(
            operation="disable",
            invalid_service=", ".join(entitlements_not_found),
            service_msg=service_msg,
        )

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    event.process_events()
    return 0 if ret else 1


@verify_json_format_args
@assert_root
@assert_attached(_raise_enable_disable_unattached_error)
@assert_lock_file("pro enable")
def action_enable(args, *, cfg, **kwargs):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    variant = getattr(args, "variant", "")
    access_only = args.access_only

    if variant and access_only:
        raise exceptions.InvalidOptionCombination(
            option1="--access-only", option2="--variant"
        )

    event.info(messages.REFRESH_CONTRACT_ENABLE)
    try:
        contract.refresh(cfg)
    except (exceptions.ConnectivityError, exceptions.UbuntuProError):
        # Inability to refresh is not a critical issue during enable
        LOG.warning("Failed to refresh contract", exc_info=True)
        event.warning(warning_msg=messages.E_REFRESH_CONTRACT_FAILURE)

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
                access_only=access_only,
                variant=variant,
                extra_args=kwargs.get("extra_args"),
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
        except exceptions.UbuntuProError as e:
            event.info(e.msg)
            event.error(
                error_msg=e.msg, error_code=e.msg_code, service=ent_name
            )
            ret = False

    if entitlements_not_found:
        event.services_failed(entitlements_not_found)
        raise create_enable_entitlements_not_found_error(
            entitlements_not_found, cfg=cfg, allow_beta=args.beta
        )

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    event.process_events()
    return 0 if ret else 1


@verify_json_format_args
@assert_root
@assert_attached()
@assert_lock_file("pro detach")
def action_detach(args, *, cfg, **kwargs) -> int:
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    ret = _detach(cfg, assume_yes=args.assume_yes)
    if ret == 0:
        daemon.start()
        timer.stop()
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
        event.info(messages.DETACH_WILL_DISABLE.pluralize(len(to_disable)))
        for ent in to_disable:
            event.info("    {}".format(ent.name))
    if not util.prompt_for_confirmation(assume_yes=assume_yes):
        return 1
    for ent in to_disable:
        _perform_disable(ent, cfg, assume_yes=assume_yes, update_status=False)

    cfg.delete_cache()
    cfg.machine_token_file.delete()
    update_motd_messages(cfg)
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


def action_api(args, *, cfg, **kwargs):
    if args.options and args.data:
        raise exceptions.CLIAPIOptionsXORData()

    result = call_api(args.endpoint_path, args.options, args.data, cfg)
    print(result.to_json())
    return 0 if result.result == "success" else 1


@assert_root
def action_auto_attach(args, *, cfg: config.UAConfig, **kwargs) -> int:
    try:
        _full_auto_attach(
            FullAutoAttachOptions(),
            cfg=cfg,
            mode=event_logger.EventLoggerMode.CLI,
        )
    except exceptions.ConnectivityError:
        event.info(messages.E_ATTACH_FAILURE.msg)
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

    event.info(messages.CLI_MAGIC_ATTACH_INIT)
    initiate_resp = _initiate(cfg=cfg)
    event.info(
        "\n"
        + messages.CLI_MAGIC_ATTACH_SIGN_IN.format(
            user_code=initiate_resp.user_code
        )
    )

    wait_options = MagicAttachWaitOptions(magic_token=initiate_resp.token)

    try:
        wait_resp = _wait(options=wait_options, cfg=cfg)
    except exceptions.MagicAttachTokenError as e:
        event.info(messages.CLI_MAGIC_ATTACH_FAILED)

        revoke_options = MagicAttachRevokeOptions(
            magic_token=initiate_resp.token
        )
        _revoke(options=revoke_options, cfg=cfg)
        raise e

    event.info("\n" + messages.CLI_MAGIC_ATTACH_PROCESSING)
    return wait_resp.contract_token


@assert_not_attached
@assert_root
@assert_lock_file("pro attach")
def action_attach(args, *, cfg, **kwargs):
    if args.token and args.attach_config:
        raise exceptions.CLIAttachTokenArgXORConfig()
    elif not args.token and not args.attach_config:
        token = _magic_attach(args, cfg=cfg)
        enable_services_override = None
    elif args.token:
        token = args.token
        enable_services_override = None
    else:
        try:
            attach_config = AttachActionsConfigFile.from_dict(
                safe_load(args.attach_config)
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
    except exceptions.ConnectivityError:
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
                error = create_enable_entitlements_not_found_error(
                    not_found, cfg=cfg, allow_beta=True
                )
                event.info(error.msg, file_type=sys.stderr)
                event.error(error_msg=error.msg, error_code=error.msg_code)
                ret = 1

        contract_client = contract.UAContractClient(cfg)
        contract_client.update_activity_token()

        _post_cli_attach(cfg)
        return ret


def action_collect_logs(args, *, cfg: config.UAConfig, **kwargs):
    output_file = args.output or UA_COLLECT_LOGS_FILE
    with tempfile.TemporaryDirectory() as output_dir:
        actions.collect_logs(cfg, output_dir)
        try:
            with tarfile.open(output_file, "w:gz") as results:
                results.add(output_dir, arcname="logs/")
        except PermissionError as e:
            LOG.error(e)
            return 1
    return 0


def get_parser(cfg: config.UAConfig):
    base_desc = __doc__
    parser = UAArgumentParser(
        prog=NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=USAGE_TMPL.format(name=NAME, command="<command>"),
        epilog=messages.CLI_HELP_EPILOG.format(name=NAME, command="<command>"),
        base_desc=base_desc,
    )
    parser.add_argument(
        "--debug", action="store_true", help=messages.CLI_ROOT_DEBUG
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version.get_version(),
        help=messages.CLI_ROOT_VERSION.format(name=NAME),
    )
    parser._optionals.title = messages.CLI_FLAGS
    subparsers = parser.add_subparsers(
        title=messages.CLI_AVAILABLE_COMMANDS, dest="command", metavar=""
    )
    subparsers.required = True
    parser_attach = subparsers.add_parser(
        "attach", help=messages.CLI_ROOT_ATTACH
    )
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)

    parser_api = subparsers.add_parser("api", help=messages.CLI_ROOT_API)
    api_parser(parser_api)
    parser_api.set_defaults(action=action_api)

    parser_auto_attach = subparsers.add_parser(
        "auto-attach", help=messages.CLI_ROOT_AUTO_ATTACH
    )
    auto_attach_parser(parser_auto_attach)
    parser_auto_attach.set_defaults(action=action_auto_attach)

    parser_collect_logs = subparsers.add_parser(
        "collect-logs", help=messages.CLI_ROOT_COLLECT_LOGS
    )
    collect_logs_parser(parser_collect_logs)
    parser_collect_logs.set_defaults(action=action_collect_logs)

    parser_config = subparsers.add_parser(
        "config", help=messages.CLI_ROOT_CONFIG
    )
    config_parser(parser_config)
    parser_config.set_defaults(action=action_config)

    parser_detach = subparsers.add_parser(
        "detach", help=messages.CLI_ROOT_DETACH
    )
    detach_parser(parser_detach)
    parser_detach.set_defaults(action=action_detach)

    parser_disable = subparsers.add_parser(
        "disable", help=messages.CLI_ROOT_DISABLE
    )
    disable_parser(parser_disable, cfg=cfg)
    parser_disable.set_defaults(action=action_disable)

    parser_enable = subparsers.add_parser(
        "enable", help=messages.CLI_ROOT_ENABLE
    )
    enable_parser(parser_enable, cfg=cfg)
    parser_enable.set_defaults(action=action_enable)

    set_fix_parser(subparsers)

    parser_security_status = subparsers.add_parser(
        "security-status", help=messages.CLI_ROOT_SECURITY_STATUS
    )
    security_status_parser(parser_security_status)
    parser_security_status.set_defaults(action=action_security_status)

    parser_help = subparsers.add_parser("help", help=messages.CLI_ROOT_HELP)
    help_parser(parser_help, cfg=cfg)
    parser_help.set_defaults(action=action_help)

    parser_refresh = subparsers.add_parser(
        "refresh", help=messages.CLI_ROOT_REFRESH
    )
    parser_refresh.set_defaults(action=action_refresh)
    refresh_parser(parser_refresh)

    parser_status = subparsers.add_parser(
        "status", help=messages.CLI_ROOT_STATUS
    )
    parser_status.set_defaults(action=action_status)
    status_parser(parser_status)

    parser_version = subparsers.add_parser(
        "version", help=messages.CLI_ROOT_VERSION.format(name=NAME)
    )
    parser_version.set_defaults(action=print_version)

    parser_system = subparsers.add_parser(
        "system", help=messages.CLI_ROOT_SYSTEM
    )
    parser_system.set_defaults(action=action_system)
    system_parser(parser_system)

    return parser


def action_status(args, *, cfg: config.UAConfig, **kwargs):
    if not cfg:
        cfg = config.UAConfig()
    show_all = args.all if args else False
    token = args.simulate_with_token if args else None
    active_value = ua_status.UserFacingConfigStatus.ACTIVE.value
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
    output = ua_status.format_tabular(status, show_all=show_all)
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


def action_system_reboot_required(args, *, cfg: config.UAConfig, **kwargs):
    result = _reboot_required(cfg)
    event.info(result.reboot_required)
    return 0


def print_version(_args=None, cfg=None, **kwargs):
    print(version.get_version())


def _action_refresh_config(args, cfg: config.UAConfig):
    try:
        cfg.process_config()
    except RuntimeError as exc:
        LOG.exception(exc)
        raise exceptions.RefreshConfigFailure()
    print(messages.REFRESH_CONFIG_SUCCESS)


@assert_attached()
def _action_refresh_contract(_args, cfg: config.UAConfig):
    try:
        contract.refresh(cfg)
    except exceptions.ConnectivityError:
        raise exceptions.RefreshContractFailure()
    print(messages.REFRESH_CONTRACT_SUCCESS)


def _action_refresh_messages(_args, cfg: config.UAConfig):
    # Not performing any exception handling here since both of these
    # functions should raise UbuntuProError exceptions, which are
    # covered by the main_error_handler decorator
    try:
        update_motd_messages(cfg)
        refresh_motd()
        if cfg.apt_news:
            apt_news.update_apt_news(cfg)
    except Exception as exc:
        LOG.exception(exc)
        raise exceptions.RefreshMessagesFailure()
    else:
        print(messages.REFRESH_MESSAGES_SUCCESS)


@assert_root
@assert_lock_file("pro refresh")
def action_refresh(args, *, cfg: config.UAConfig, **kwargs):
    if args.target is None or args.target == "config":
        _action_refresh_config(args, cfg)

    if args.target is None or args.target == "contract":
        _action_refresh_contract(args, cfg)
        notices.remove(Notice.CONTRACT_REFRESH_WARNING)

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


def action_help(args, *, cfg, **kwargs):
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
        LOG.warning("New version available: %s", new_version)
        event.info(
            messages.WARN_NEW_VERSION_AVAILABLE_CLI.format(
                version=new_version
            ),
            file_type=sys.stderr,
        )


def _warn_about_output_redirection(cmd_args) -> None:
    """Warn users that the user readable output may change."""
    if (
        cmd_args.command in ("status", "security-status")
        and not sys.stdout.isatty()
    ):
        if hasattr(cmd_args, "format") and cmd_args.format in ("json", "yaml"):
            return
        LOG.warning("Not in a tty and human-readable command called")
        event.info(
            messages.WARNING_HUMAN_READABLE_OUTPUT.format(
                command=cmd_args.command
            ),
            file_type=sys.stderr,
        )


def setup_logging(log_level, log_file=None, logger=None):
    """Setup console logging and debug logging to log_file

    It configures the pro client logger.
    If run as non_root and cfg.log_file is provided, it is replaced
    with another non-root log file.
    """
    if log_file is None:
        cfg = config.UAConfig()
        log_file = cfg.log_file
    # if we are running as non-root, change log file
    if not util.we_are_currently_root():
        log_file = pro_log.get_user_log_file()

    if isinstance(log_level, str):
        log_level = log_level.upper()

    if not logger:
        logger = logging.getLogger("ubuntupro")
    logger.setLevel(log_level)

    # Clear all handlers, so they are replaced for this logger
    logger.handlers = []

    # Setup file logging
    log_file_path = pathlib.Path(log_file)
    if not log_file_path.exists():
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        log_file_path.touch(mode=0o640)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonArrayFormatter())
    file_handler.setLevel(log_level)
    file_handler.set_name("upro-file")
    file_handler.addFilter(pro_log.RedactionFilter())
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
            LOG.error("KeyboardInterrupt")
            print(messages.CLI_INTERRUPT_RECEIVED, file=sys.stderr)
            lock.clear_lock_file_if_present()
            sys.exit(1)
        except exceptions.ConnectivityError as exc:
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                tmpl = messages.SSL_VERIFICATION_ERROR_CA_CERTIFICATES
                if apt.is_installed("ca-certificates"):
                    tmpl = messages.SSL_VERIFICATION_ERROR_OPENSSL_CONFIG
                msg = tmpl.format(url=exc.url)
                event.error(error_msg=msg.msg, error_code=msg.name)
                event.info(info_msg=msg.msg, file_type=sys.stderr)
            else:
                LOG.exception(
                    "Failed to access URL: %s", exc.url, exc_info=exc
                )

                msg = messages.E_CONNECTIVITY_ERROR.format(
                    url=exc.url,
                    cause_error=exc.cause_error,
                )
                event.error(error_msg=msg.msg, error_code=msg.name)
                event.info(info_msg=msg.msg, file_type=sys.stderr)

            lock.clear_lock_file_if_present()
            event.process_events()

            _warn_about_new_version()

            sys.exit(1)
        except exceptions.PycurlCACertificatesError as exc:
            tmpl = messages.SSL_VERIFICATION_ERROR_CA_CERTIFICATES
            if apt.is_installed("ca-certificates"):
                tmpl = messages.SSL_VERIFICATION_ERROR_OPENSSL_CONFIG
            msg = tmpl.format(url=exc.url)
            event.error(error_msg=msg.msg, error_code=msg.name)
            event.info(info_msg=msg.msg, file_type=sys.stderr)

            lock.clear_lock_file_if_present()
            event.process_events()

            _warn_about_new_version()

            sys.exit(1)
        except exceptions.UbuntuProError as exc:
            LOG.error(exc.msg)
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
            LOG.exception("Unhandled exception, please file a bug")
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
    setup_logging(
        defaults.CONFIG_DEFAULTS["log_level"],
        defaults.CONFIG_DEFAULTS["log_file"],
    )
    cfg = config.UAConfig()
    setup_logging(cfg.log_level, cfg.log_file)

    if not sys_argv:
        sys_argv = sys.argv

    parser = get_parser(cfg=cfg)
    cli_arguments = sys_argv[1:]
    if not cli_arguments:
        parser.print_usage()
        print(messages.CLI_TRY_HELP)
        sys.exit(1)

    # Grab everything after a "--" if present and handle separately
    if "--" in cli_arguments:
        double_dash_index = cli_arguments.index("--")
        pro_cli_args = cli_arguments[:double_dash_index]
        extra_args = cli_arguments[double_dash_index + 1 :]
    else:
        pro_cli_args = cli_arguments
        extra_args = []

    args = parser.parse_args(args=pro_cli_args)
    if args.debug:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        logging.getLogger("ubuntupro").addHandler(console_handler)

    set_event_mode(args)

    http_proxy = cfg.http_proxy
    https_proxy = cfg.https_proxy
    http.configure_web_proxy(http_proxy=http_proxy, https_proxy=https_proxy)

    LOG.debug("Executed with sys.argv: %r" % sys_argv)

    cfg.warn_about_invalid_keys()

    pro_environment = [
        "{}={}".format(k, v)
        for k, v in sorted(util.get_pro_environment().items())
    ]
    if pro_environment:
        LOG.debug("Executed with environment variables: %r" % pro_environment)

    _warn_about_output_redirection(args)

    return_value = args.action(args, cfg=cfg, extra_args=extra_args)

    _warn_about_new_version(args)

    return return_value


if __name__ == "__main__":
    sys.exit(main())
