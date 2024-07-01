"""Client to manage Ubuntu Pro services on a machine."""

import argparse
import json
import logging
import sys
import time
from typing import Optional

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
    log,
    messages,
    secret_manager,
    security_status,
    status,
    timer,
    util,
    version,
)
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
from uaclient.cli import cli_util, enable, fix
from uaclient.cli.api import api_command
from uaclient.cli.collect_logs import collect_logs_command
from uaclient.cli.constants import NAME, USAGE_TMPL
from uaclient.cli.disable import disable_command, perform_disable
from uaclient.data_types import AttachActionsConfigFile, IncorrectTypeError
from uaclient.entitlements import (
    create_enable_entitlements_not_found_error,
    entitlements_disable_order,
    get_valid_entitlement_names,
)
from uaclient.entitlements.entitlement_status import (
    ApplicationStatus,
    CanEnableFailure,
)
from uaclient.files import machine_token, state_files
from uaclient.log import get_user_or_root_log_file_path
from uaclient.timer.update_messaging import refresh_motd, update_motd_messages
from uaclient.yaml import safe_dump, safe_load

UA_AUTH_TOKEN_URL = "https://auth.contracts.canonical.com"

STATUS_FORMATS = ["tabular", "json", "yaml"]

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

COMMANDS = [api_command, collect_logs_command, disable_command]


class UAArgumentParser(argparse.ArgumentParser):
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


def auto_attach_parser(parser):
    """Build or extend an arg parser for auto-attach subcommand."""
    parser.prog = "auto-attach"
    parser.description = messages.CLI_AUTO_ATTACH_DESC
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser._optionals.title = messages.CLI_FLAGS
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


@cli_util.assert_root
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
    if not set_value.strip():
        subparser.print_help()
        raise exceptions.EmptyConfigValue(arg=set_key)
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


@cli_util.assert_root
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


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached()
@cli_util.assert_lock_file("pro detach")
def action_detach(args, *, cfg, **kwargs) -> int:
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    ret = _detach(
        cfg, assume_yes=args.assume_yes, json_output=(args.format == "json")
    )
    if ret == 0:
        daemon.start()
        timer.stop()
    event.process_events()
    return ret


def _detach(cfg: config.UAConfig, assume_yes: bool, json_output: bool) -> int:
    """Detach the machine from the active Ubuntu Pro subscription,

    :param cfg: a ``config.UAConfig`` instance
    :param assume_yes: Assume a yes answer to any prompts requested.
         In this case, it means automatically disable any service during
         detach.
    :param json_output: output should be json only

    @return: 0 on success, 1 otherwise
    """
    to_disable = []
    for ent_name in entitlements_disable_order(cfg):
        try:
            ent = entitlements.entitlement_factory(
                cfg=cfg,
                name=ent_name,
            )
        except exceptions.EntitlementNotFoundError:
            continue

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
        perform_disable(
            ent,
            cfg,
            json_output=json_output,
            assume_yes=assume_yes,
            update_status=False,
        )

    machine_token_file = machine_token.get_machine_token_file(cfg)
    machine_token_file.delete()
    state_files.delete_state_files()
    update_motd_messages(cfg)
    event.info(messages.DETACH_SUCCESS)
    return 0


def _post_cli_attach(cfg: config.UAConfig) -> None:
    machine_token_file = machine_token.get_machine_token_file(cfg)
    contract_name = machine_token_file.contract_name

    if contract_name:
        event.info(
            messages.ATTACH_SUCCESS_TMPL.format(contract_name=contract_name)
        )
    else:
        event.info(messages.ATTACH_SUCCESS_NO_CONTRACT_NAME)

    daemon.stop()
    daemon.cleanup(cfg)

    status_dict, _ret = actions.status(cfg)
    output = status.format_tabular(status_dict)
    event.info(util.handle_unicode_characters(output))
    event.process_events()


@cli_util.assert_root
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


@cli_util.assert_not_attached
@cli_util.assert_root
@cli_util.assert_lock_file("pro attach")
def action_attach(args, *, cfg, **kwargs):
    if args.token and args.attach_config:
        raise exceptions.CLIAttachTokenArgXORConfig()
    elif not args.token and not args.attach_config:
        token = _magic_attach(args, cfg=cfg)
        enable_services_override = None
    elif args.token:
        token = args.token
        secret_manager.secrets.add_secret(token)
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
                ent_ret, reason = actions.enable_entitlement_by_name(cfg, name)
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
                    not_found, cfg=cfg
                )
                event.info(error.msg, file_type=sys.stderr)
                event.error(error_msg=error.msg, error_code=error.msg_code)
                ret = 1

        contract_client = contract.UAContractClient(cfg)
        contract_client.update_activity_token()

        _post_cli_attach(cfg)
        return ret


def get_parser(cfg: config.UAConfig):
    parser = UAArgumentParser(
        prog=NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=USAGE_TMPL.format(name=NAME, command="<command>"),
        epilog=messages.CLI_HELP_EPILOG.format(name=NAME, command="<command>"),
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

    for command in COMMANDS:
        command.register(subparsers)

    parser_attach = subparsers.add_parser(
        "attach", help=messages.CLI_ROOT_ATTACH
    )
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)

    parser_auto_attach = subparsers.add_parser(
        "auto-attach", help=messages.CLI_ROOT_AUTO_ATTACH
    )
    auto_attach_parser(parser_auto_attach)
    parser_auto_attach.set_defaults(action=action_auto_attach)

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

    enable.add_parser(subparsers, cfg)
    fix.add_parser(subparsers)

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
    active_value = status.UserFacingConfigStatus.ACTIVE.value
    status_dict, ret = actions.status(
        cfg, simulate_with_token=token, show_all=show_all
    )
    config_active = bool(status_dict["execution_status"] == active_value)

    if args and args.wait and config_active:
        while status_dict["execution_status"] == active_value:
            event.info(".", end="")
            time.sleep(1)
            status_dict, ret = actions.status(
                cfg,
                simulate_with_token=token,
                show_all=show_all,
            )
        event.info("")

    event.set_output_content(status_dict)
    output = status.format_tabular(status_dict, show_all=show_all)
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


@cli_util.assert_attached()
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


@cli_util.assert_root
@cli_util.assert_lock_file("pro refresh")
def action_refresh(args, *, cfg: config.UAConfig, **kwargs):
    if args.target is None or args.target == "config":
        _action_refresh_config(args, cfg)

    if args.target is None or args.target == "contract":
        _action_refresh_contract(args, cfg)

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

    if not service:
        get_parser(cfg=cfg).print_help()
        return 0

    if not cfg:
        cfg = config.UAConfig()

    help_response = status.help(cfg, service)

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
                info_msg=messages.UNEXPECTED_ERROR.format(
                    error_msg=str(e),
                    log_path=get_user_or_root_log_file_path(),
                ).msg,
                file_type=sys.stderr,
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
    log.setup_cli_logging(
        defaults.CONFIG_DEFAULTS["log_level"],
        defaults.CONFIG_DEFAULTS["log_file"],
    )
    cfg = config.UAConfig()
    log.setup_cli_logging(cfg.log_level, cfg.log_file)

    if not sys_argv:
        sys_argv = sys.argv

    parser = get_parser(cfg=cfg)
    cli_arguments = sys_argv[1:]
    if not cli_arguments:
        parser.print_help()
        sys.exit(0)

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
