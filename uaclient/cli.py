#!/usr/bin/env python

"""Client to manage Ubuntu Advantage services on a machine."""

import argparse
from functools import wraps
import json
import logging
import os
import pathlib
import sys
import textwrap

from uaclient import config
from uaclient import contract
from uaclient import entitlements
from uaclient import exceptions
from uaclient import status as ua_status
from uaclient import util
from uaclient import version
from uaclient.clouds import identity

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

STATUS_FORMATS = ["tabular", "json"]


def assert_root(f):
    """Decorator asserting root user"""

    @wraps(f)
    def new_f(*args, **kwargs):
        if os.getuid() != 0:
            raise exceptions.NonRootUserError()
        return f(*args, **kwargs)

    return new_f


def assert_attached(unattached_msg_tmpl=None):
    """Decorator asserting attached config.

    :param unattached_msg_tmpl: Optional msg template to format if raising an
        UnattachedError
    """

    def wrapper(f):
        @wraps(f)
        def new_f(args, cfg):
            if not cfg.is_attached:
                if unattached_msg_tmpl:
                    name = getattr(args, "name", "None")
                    msg = unattached_msg_tmpl.format(name=name)
                    exception = exceptions.UnattachedError(msg)
                else:
                    exception = exceptions.UnattachedError()
                raise exception
            return f(args, cfg)

        return new_f

    return wrapper


def assert_not_attached(f):
    """Decorator asserting unattached config."""

    @wraps(f)
    def new_f(args, cfg):
        if cfg.is_attached:
            raise exceptions.AlreadyAttachedError(cfg)
        return f(args, cfg)

    return new_f


def require_valid_entitlement_name(operation: str):
    """Decorator ensuring that args.name is a valid service.

    :param operation: the operation name to use in error messages
    """

    def wrapper(f):
        @wraps(f)
        def new_f(args, cfg):
            if hasattr(args, "name"):
                name = args.name
                tmpl = ua_status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL
                if name not in entitlements.ENTITLEMENT_CLASS_BY_NAME:
                    raise exceptions.UserFacingError(
                        tmpl.format(operation=operation, name=name)
                    )
            return f(args, cfg)

        return new_f

    return wrapper


def auto_attach_parser(parser):
    """Build or extend an arg parser for auto-attach subcommand."""
    parser.prog = "auto-attach"
    parser.usage = USAGE_TMPL.format(name=NAME, command=parser.prog)
    parser._optionals.title = "Flags"
    return parser


def attach_parser(parser):
    """Build or extend an arg parser for attach subcommand."""
    parser.usage = USAGE_TMPL.format(name=NAME, command="attach <token>")
    parser.prog = "attach"
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
    return parser


def detach_parser(parser):
    """Build or extend an arg parser for detach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="detach")
    parser.usage = usage
    parser.prog = "detach"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help="do not prompt for confirmation before performing the detach",
    )
    return parser


def enable_parser(parser):
    """Build or extend an arg parser for enable subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="enable") + " <name>"
    parser.usage = usage
    parser.prog = "enable"
    parser._positionals.title = "Arguments"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "name",
        action="store",
        help="the name of the Ubuntu Advantage service to enable",
    )
    return parser


def disable_parser(parser):
    """Build or extend an arg parser for disable subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="disable") + " <name>"
    parser.usage = usage
    parser.prog = "disable"
    parser._positionals.title = "Arguments"
    parser._optionals.title = "Flags"
    parser.add_argument(
        "name",
        action="store",
        help="the name of the Ubuntu Advantage service to disable",
    )
    return parser


def status_parser(parser):
    """Build or extend an arg parser for status subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command="status")
    parser.usage = usage
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
        """
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
    parser._optionals.title = "Flags"
    return parser


@assert_root
@require_valid_entitlement_name("disable")
@assert_attached(ua_status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL)
def action_disable(args, cfg):
    """Perform the disable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[args.name]
    entitlement = ent_cls(cfg)
    ret = 0 if entitlement.disable() else 1
    cfg.status()  # Update the status cache
    return ret


def _perform_enable(
    entitlement_name: str,
    cfg: config.UAConfig,
    *,
    silent_if_inapplicable: bool = False
) -> bool:
    """Perform the enable action on a named entitlement.

    (This helper excludes any messaging, so that different enablement code
    paths can message themselves.)

    :param entitlement_name: the name of the entitlement to enable
    :param cfg: the UAConfig to pass to the entitlement
    :param silent_if_inapplicable:
        don't output messages when determining if an entitlement can be
        enabled on this system

    @return: True on success, False otherwise
    """
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[entitlement_name]
    entitlement = ent_cls(cfg)
    ret = entitlement.enable(silent_if_inapplicable=silent_if_inapplicable)
    cfg.status()  # Update the status cache
    return ret


@assert_root
@require_valid_entitlement_name("enable")
@assert_attached(ua_status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL)
def action_enable(args, cfg):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    print(ua_status.MESSAGE_REFRESH_ENABLE)
    try:
        contract.request_updated_contract(cfg)
    except (util.UrlError, exceptions.UserFacingError):
        # Inability to refresh is not a critical issue during enable
        logging.debug(ua_status.MESSAGE_REFRESH_FAILURE, exc_info=True)
    return 0 if _perform_enable(args.name, cfg) else 1


@assert_root
@assert_attached()
def action_detach(args, cfg) -> int:
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
        ent = ent_cls(cfg)
        if ent.can_disable(silent=True):
            to_disable.append(ent)
    if to_disable:
        suffix = "s" if len(to_disable) > 1 else ""
        print("Detach will disable the following service{}:".format(suffix))
        for ent in to_disable:
            print("    {}".format(ent.name))
    if not assume_yes and not util.prompt_for_confirmation():
        return 1
    for ent in to_disable:
        ent.disable(silent=True)
    contract_client = contract.UAContractClient(cfg)
    machine_token = cfg.machine_token["machineToken"]
    contract_id = cfg.machine_token["machineTokenInfo"]["contractInfo"]["id"]
    contract_client.detach_machine_from_contract(machine_token, contract_id)
    cfg.delete_cache()
    print(ua_status.MESSAGE_DETACH_SUCCESS)
    return 0


def _attach_with_token(
    cfg: config.UAConfig, token: str, allow_enable: bool
) -> int:
    """Common functionality to take a token and attach via contract backend"""
    try:
        contract.request_updated_contract(
            cfg, token, allow_enable=allow_enable
        )
    except util.UrlError as exc:
        with util.disable_log_to_console():
            logging.exception(exc)
        print(ua_status.MESSAGE_ATTACH_FAILURE)
        cfg.status()  # Persist updated status in the event of partial attach
        return 1
    except exceptions.UserFacingError as exc:
        logging.warning(exc.msg)
        cfg.status()  # Persist updated status in the event of partial attach
        return 1
    contract_name = cfg.machine_token["machineTokenInfo"]["contractInfo"][
        "name"
    ]
    print(
        ua_status.MESSAGE_ATTACH_SUCCESS_TMPL.format(
            contract_name=contract_name
        )
    )

    action_status(args=None, cfg=cfg)
    return 0


def _get_contract_token_from_cloud_identity(cfg: config.UAConfig) -> str:
    """Detect cloud_type and request a contract token from identity info.

    :param cfg: a ``config.UAConfig`` instance

    :raise NonAutoAttachImageError: When not on an auto-attach image type.
    :raise UrlError: On unexpected connectivity issues to contract
        server or inability to access identity doc from metadata service.
    :raise ContractAPIError: On unexpected errors when talking to the contract
        server.
    :raise NonAutoAttachImageError: If this cloud type does not have
        auto-attach support.

    :return: contract token obtained from identity doc
    """
    try:
        instance = identity.cloud_instance_factory()
    except exceptions.UserFacingError as e:
        if cfg.is_attached:
            # We are attached on non-Pro Image, just report already attached
            raise exceptions.AlreadyAttachedError(cfg)
        # Unattached on non-Pro return UserFacing error msg details
        raise e
    current_iid = identity.get_instance_id()
    if cfg.is_attached:
        prev_iid = cfg.read_cache("instance-id")
        if current_iid == prev_iid:
            raise exceptions.AlreadyAttachedError(cfg)
        print("Re-attaching Ubuntu Advantage subscription on new instance")
        if _detach(cfg, assume_yes=True) != 0:
            raise exceptions.UserFacingError(
                ua_status.MESSAGE_DETACH_AUTOMATION_FAILURE
            )
    contract_client = contract.UAContractClient(cfg)
    try:
        tokenResponse = contract_client.request_auto_attach_contract_token(
            instance=instance
        )
    except contract.ContractAPIError as e:
        if e.code and 400 <= e.code < 500:
            raise exceptions.NonAutoAttachImageError(
                ua_status.MESSAGE_UNSUPPORTED_AUTO_ATTACH
            )
        raise e
    if current_iid:
        cfg.write_cache("instance-id", current_iid)

    return tokenResponse["contractToken"]


@assert_root
def action_auto_attach(args, cfg):
    token = _get_contract_token_from_cloud_identity(cfg)
    return _attach_with_token(cfg, token=token, allow_enable=True)


@assert_not_attached
@assert_root
def action_attach(args, cfg):
    if not args.token:
        raise exceptions.UserFacingError(
            ua_status.MESSAGE_ATTACH_REQUIRES_TOKEN
        )
    return _attach_with_token(
        cfg, token=args.token, allow_enable=args.auto_enable
    )


def get_parser():
    service_line_tmpl = " - {name}: {description}{url}"
    description_lines = [__doc__]
    sorted_classes = sorted(entitlements.ENTITLEMENT_CLASS_BY_NAME.items())
    for name, ent_cls in sorted_classes:
        if ent_cls.help_doc_url:
            url = " ({})".format(ent_cls.help_doc_url)
        else:
            url = ""
        service_line = service_line_tmpl.format(
            name=name, description=ent_cls.description, url=url
        )
        if len(service_line) <= 80:
            description_lines.append(service_line)
        else:
            wrapped_words = []
            line = service_line
            while len(line) > 80:
                [line, wrapped_word] = line.rsplit(" ", 1)
                wrapped_words.insert(0, wrapped_word)
            description_lines.extend([line, "   " + " ".join(wrapped_words)])

    parser = argparse.ArgumentParser(
        prog=NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="\n".join(description_lines),
        usage=USAGE_TMPL.format(name=NAME, command="[command]"),
        epilog=EPILOG_TMPL.format(name=NAME, command="[command]"),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show all debug log messages to console",
    )
    parser._optionals.title = "Flags"
    subparsers = parser.add_subparsers(
        title="Available Commands", dest="command", metavar=""
    )
    subparsers.required = True
    parser_status = subparsers.add_parser(
        "status", help="current status of all Ubuntu Advantage services"
    )
    parser_status.set_defaults(action=action_status)
    status_parser(parser_status)
    parser_attach = subparsers.add_parser(
        "attach",
        help="attach this machine to an Ubuntu Advantage subscription",
    )
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)
    parser_auto_attach = subparsers.add_parser(
        "auto-attach",
        help="automatically attach Ubuntu Advantage on supported platforms",
    )
    auto_attach_parser(parser_auto_attach)
    parser_auto_attach.set_defaults(action=action_auto_attach)
    parser_detach = subparsers.add_parser(
        "detach",
        help="remove this machine from an Ubuntu Advantage subscription",
    )
    detach_parser(parser_detach)
    parser_detach.set_defaults(action=action_detach)
    parser_enable = subparsers.add_parser(
        "enable",
        help="enable a specific Ubuntu Advantage service on this machine",
    )
    enable_parser(parser_enable)
    parser_enable.set_defaults(action=action_enable)
    parser_disable = subparsers.add_parser(
        "disable",
        help="disable a specific Ubuntu Advantage service on this machine",
    )
    disable_parser(parser_disable)
    parser_disable.set_defaults(action=action_disable)
    parser_refresh = subparsers.add_parser(
        "refresh",
        help="refresh Ubuntu Advantage services from contracts server",
    )
    parser_refresh.set_defaults(action=action_refresh)
    parser_version = subparsers.add_parser(
        "version", help="show version of {}".format(NAME)
    )
    parser_version.set_defaults(action=print_version)
    parser_help = subparsers.add_parser(
        "help", help="show this help message and exit"
    )
    parser_help.set_defaults(action=action_help)
    return parser


def action_status(args, cfg):
    if not cfg:
        cfg = config.UAConfig()
    if args and args.format == "json":
        status = cfg.status()
        if status["expires"] != ua_status.UserFacingStatus.INAPPLICABLE.value:
            status["expires"] = str(status["expires"])
        print(json.dumps(status))
    else:
        output = ua_status.format_tabular(cfg.status())
        # Replace our Unicode dash with an ASCII dash if we aren't going to be
        # writing to a utf-8 output; see
        # https://github.com/CanonicalLtd/ubuntu-advantage-client/issues/859
        if (
            sys.stdout.encoding is None
            or "UTF-8" not in sys.stdout.encoding.upper()
        ):
            output = output.replace("\u2014", "-")
        print(output)
    return 0


def print_version(_args=None, _cfg=None):
    print(version.get_version())


@assert_root
@assert_attached()
def action_refresh(args, cfg):
    try:
        contract.request_updated_contract(cfg)
    except util.UrlError as exc:
        with util.disable_log_to_console():
            logging.exception(exc)
        raise exceptions.UserFacingError(ua_status.MESSAGE_REFRESH_FAILURE)
    print(ua_status.MESSAGE_REFRESH_SUCCESS)
    return 0


def action_help(_args, _cfg):
    get_parser().print_help()
    return 0


def setup_logging(console_level, log_level, log_file=None):
    """Setup console logging and debug logging to log_file"""
    if log_file is None:
        log_file = config.CONFIG_DEFAULTS["log_file"]
    console_formatter = util.LogFormatter()
    log_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(log_level)
    # Setup console logging
    stderr_found = False
    for handler in root.handlers:
        if hasattr(handler, "stream") and hasattr(handler.stream, "name"):
            if handler.stream.name == "<stderr>":
                handler.setLevel(console_level)
                handler.setFormatter(console_formatter)
                handler.set_name("console")  # Used to disable console logging
                stderr_found = True
                break
    if not stderr_found:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(console_formatter)
        console.setLevel(console_level)
        console.set_name("console")  # Used to disable console logging
        root.addHandler(console)
    if os.getuid() == 0:
        # Setup readable-by-root-only debug file logging if running as root
        log_file_path = pathlib.Path(log_file)
        log_file_path.touch()
        log_file_path.chmod(0o600)

        filehandler = logging.FileHandler(log_file)
        filehandler.setLevel(log_level)
        filehandler.setFormatter(log_formatter)
        root.addHandler(filehandler)


def main_error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            with util.disable_log_to_console():
                logging.exception("KeyboardInterrupt")
            print("Interrupt received; exiting.", file=sys.stderr)
            sys.exit(1)
        except util.UrlError as exc:
            with util.disable_log_to_console():
                msg_args = {"url": exc.url, "error": exc}
                if exc.url:
                    msg_tmpl = ua_status.LOG_CONNECTIVITY_ERROR_WITH_URL_TMPL
                else:
                    msg_tmpl = ua_status.LOG_CONNECTIVITY_ERROR_TMPL
                logging.exception(msg_tmpl.format(**msg_args))
            print(ua_status.MESSAGE_CONNECTIVITY_ERROR, file=sys.stderr)
            sys.exit(1)
        except exceptions.UserFacingError as exc:
            with util.disable_log_to_console():
                logging.exception(exc.msg)
            print("{}".format(exc.msg), file=sys.stderr)
            sys.exit(exc.exit_code)
        except Exception:
            with util.disable_log_to_console():
                logging.exception("Unhandled exception, please file a bug")
            print(ua_status.MESSAGE_UNEXPECTED_ERROR, file=sys.stderr)
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
    cfg = config.UAConfig()
    log_level = cfg.log_level
    console_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(console_level, log_level, cfg.log_file)
    logging.debug("Executed with sys.argv: %r", sys_argv)
    return args.action(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
