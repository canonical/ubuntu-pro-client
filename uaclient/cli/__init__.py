"""Client to manage Ubuntu Pro services on a machine."""

import argparse
import logging
import sys
from typing import Optional

from uaclient import (
    apt,
    apt_news,
    config,
    defaults,
    entitlements,
    event_logger,
    exceptions,
    http,
    lock,
    log,
    messages,
    util,
    version,
)
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.apt import AptProxyScope, setup_apt_proxy
from uaclient.cli import cli_util
from uaclient.cli.api import api_command
from uaclient.cli.attach import attach_command
from uaclient.cli.auto_attach import auto_attach_command
from uaclient.cli.collect_logs import collect_logs_command
from uaclient.cli.constants import NAME, USAGE_TMPL
from uaclient.cli.detach import detach_command
from uaclient.cli.disable import disable_command
from uaclient.cli.enable import enable_command
from uaclient.cli.fix import fix_command
from uaclient.cli.help import help_command
from uaclient.cli.refresh import refresh_command
from uaclient.cli.security_status import security_status_command
from uaclient.cli.status import status_command
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.files import state_files
from uaclient.log import get_user_or_root_log_file_path

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

COMMANDS = [
    api_command,
    attach_command,
    auto_attach_command,
    collect_logs_command,
    detach_command,
    disable_command,
    enable_command,
    fix_command,
    help_command,
    refresh_command,
    security_status_command,
    status_command,
]


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

    parser_config = subparsers.add_parser(
        "config", help=messages.CLI_ROOT_CONFIG
    )
    config_parser(parser_config)
    parser_config.set_defaults(action=action_config)

    parser_system = subparsers.add_parser(
        "system", help=messages.CLI_ROOT_SYSTEM
    )
    parser_system.set_defaults(action=action_system)
    system_parser(parser_system)

    return parser


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

    # Version is --version
    if cli_arguments[0] == "version":
        cli_arguments[0] = "--version"

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
