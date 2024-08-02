"""Client to manage Ubuntu Pro services on a machine."""

import logging
import sys

from uaclient import (
    apt,
    defaults,
    event_logger,
    exceptions,
    http,
    lock,
    log,
    messages,
    util,
    version,
)
from uaclient.cli.api import api_command
from uaclient.cli.attach import attach_command
from uaclient.cli.auto_attach import auto_attach_command
from uaclient.cli.collect_logs import collect_logs_command
from uaclient.cli.config import config_command
from uaclient.cli.detach import detach_command
from uaclient.cli.disable import disable_command
from uaclient.cli.enable import enable_command
from uaclient.cli.fix import fix_command
from uaclient.cli.help import help_command
from uaclient.cli.parser import HelpCategory, ProArgumentParser
from uaclient.cli.refresh import refresh_command
from uaclient.cli.security_status import security_status_command
from uaclient.cli.status import status_command
from uaclient.cli.system import system_command
from uaclient.config import UAConfig
from uaclient.log import get_user_or_root_log_file_path

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

NAME = "pro"

COMMANDS = [
    api_command,
    attach_command,
    auto_attach_command,
    collect_logs_command,
    config_command,
    detach_command,
    disable_command,
    enable_command,
    fix_command,
    help_command,
    refresh_command,
    security_status_command,
    status_command,
    system_command,
]


def get_parser():
    parser = ProArgumentParser(
        prog=NAME,
        use_main_help=False,
        epilog=messages.CLI_HELP_EPILOG.format(name=NAME, command="<command>"),
    )
    parser.add_help_entry(
        HelpCategory.FLAGS,
        "-h, --help",
        messages.CLI_HELP_FLAG_DESC.format(name=NAME),
    )

    parser.add_argument(
        "--debug", action="store_true", help=messages.CLI_ROOT_DEBUG
    )
    parser.add_help_entry(
        HelpCategory.FLAGS, "--debug", messages.CLI_ROOT_DEBUG
    )

    parser.add_argument(
        "--version",
        action="version",
        version=version.get_version(),
        help=messages.CLI_ROOT_VERSION.format(name=NAME),
    )
    parser.add_help_entry(
        HelpCategory.FLAGS,
        "--version",
        messages.CLI_ROOT_VERSION.format(name=NAME),
    )

    subparsers = parser.add_subparsers(
        title=messages.CLI_AVAILABLE_COMMANDS,
        dest="command",
        metavar="<command>",
    )
    subparsers.required = True

    for command in COMMANDS:
        command.register(subparsers)

    return parser


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
    cfg = UAConfig()
    log.setup_cli_logging(cfg.log_level, cfg.log_file)

    if not sys_argv:
        sys_argv = sys.argv

    parser = get_parser()
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
