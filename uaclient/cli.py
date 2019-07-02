#!/usr/bin/env python

"""\
Client to manage Ubuntu Advantage support services on a machine.

Available services:
 - cc-eal: Canonical Common Criteria EAL2 Provisioning
   (https://ubuntu.com/cc-eal)
 - cis-audit: Canonical CIS Benchmark Audit Tool (https://ubuntu.com/cis)
 - esm: Extended Security Maintenance (https://ubuntu.com/esm)
 - fips: FIPS 140-2 (https://ubuntu.com/fips)
 - fips-updates: FIPS 140-2 with updates
 - lvepatch: Canonical Livepatch (https://ubuntu.com/livepatch)

"""

import argparse
import json
import logging
import os
import pathlib
import sys

from uaclient import config
from uaclient import contract
from uaclient import entitlements
from uaclient import exceptions
from uaclient import sso
from uaclient import status as ua_status
from uaclient import util
from uaclient import version

NAME = 'ubuntu-advantage'

USAGE_TMPL = '{name} {command} [flags]'
EPILOG_TMPL = (
    'Use {name} {command} --help for more information about a command.')

STATUS_HEADER_TMPL = """\
Account: {account}
Subscription: {subscription}
Valid until: {contract_expiry}
Technical support level: {tech_support_level}
"""
UA_AUTH_TOKEN_URL = 'https://auth.contracts.canonical.com'

DEFAULT_LOG_FORMAT = (
    '%(asctime)s - %(filename)s:(%(lineno)d) [%(levelname)s]: %(message)s')

STATUS_FORMATS = ['tabular', 'json']


def assert_attached_root(func):
    """Decorator asserting root user and attached config."""
    def wrapper(args, cfg):
        if os.getuid() != 0:
            raise exceptions.NonRootUserError()
        if not cfg.is_attached:
            raise exceptions.UnattachedError()
        return func(args, cfg)
    return wrapper


def attach_parser(parser=None):
    """Build or extend an arg parser for attach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='attach [token]')
    if not parser:
        parser = argparse.ArgumentParser(
            prog='attach',
            description=('Attach this machine to an existing Ubuntu Advantage'
                         ' support subscription'),
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'attach'
    parser._optionals.title = 'Flags'
    parser.add_argument(
        'token', nargs='?',
        help=(
            'Optional token obtained for Ubuntu Advantage authentication: %s' %
            UA_AUTH_TOKEN_URL))
    parser.add_argument(
        '--email', action='store',
        help='Optional email address for Ubuntu SSO login')
    parser.add_argument(
        '--password', action='store',
        help='Optional password for Ubuntu SSO login')
    parser.add_argument(
        '--otp', action='store',
        help=('Optional one-time password for two-factor authentication'
              ' to Ubuntu SSO'))
    parser.add_argument(
        '--no-auto-enable', action='store_false', dest='auto_enable',
        help='Do not enable any recommended services automatically')
    return parser


def detach_parser(parser=None):
    """Build or extend an arg parser for detach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='detach')
    if not parser:
        parser = argparse.ArgumentParser(
            prog='detach',
            description=(
                'Detach this machine from an existing Ubuntu Advantage'
                ' support subscription'),
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'detach'
    parser._optionals.title = 'Flags'
    return parser


def enable_parser(parser=None):
    """Build or extend an arg parser for enable subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='enable') + ' <name>'
    if not parser:
        parser = argparse.ArgumentParser(
            prog='enable',
            description='Enable a support service on this machine',
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'enable'
    parser._positionals.title = 'Services'
    parser._optionals.title = 'Flags'
    entitlement_names = list(
        cls.name for cls in entitlements.ENTITLEMENT_CLASSES)
    parser.add_argument(
        'name', action='store', choices=entitlement_names,
        help='The name of the support service to enable')
    return parser


def disable_parser(parser=None):
    """Build or extend an arg parser for disable subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='disable') + ' <name>'
    if not parser:
        parser = argparse.ArgumentParser(
            prog='disable',
            description='Disable a support service on this machine',
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'disable'
    parser._positionals.title = 'Services'
    parser._optionals.title = 'Flags'
    entitlement_names = list(
        cls.name for cls in entitlements.ENTITLEMENT_CLASSES)
    parser.add_argument(
        'name', action='store', choices=entitlement_names,
        help='The name of the support service to disable')
    return parser


def status_parser(parser=None):
    """Build or extend an arg parser for status subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='status')
    if not parser:
        parser = argparse.ArgumentParser(
            prog='status',
            description=('Print status information for Ubuntu Advantage'
                         ' support subscription'),
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'status'
    parser.add_argument(
        '--format', action='store', choices=STATUS_FORMATS,
        default=STATUS_FORMATS[0],
        help=('Output status in the request format. Default: %s' %
              STATUS_FORMATS[0]))
    parser._optionals.title = 'Flags'
    return parser


@assert_attached_root
def action_disable(args, cfg):
    """Perform the disable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[args.name]
    entitlement = ent_cls(cfg)
    ret = 0 if entitlement.disable() else 1
    cfg.status()  # Update the status cache
    return ret


def _perform_enable(entitlement_name: str, cfg: config.UAConfig, *,
                    silent_if_inapplicable: bool = False) -> bool:
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


@assert_attached_root
def action_enable(args, cfg):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    print(ua_status.MESSAGE_REFRESH_ENABLE)
    if not contract.request_updated_contract(cfg):
        logging.debug(ua_status.MESSAGE_REFRESH_FAILURE)
    return 0 if _perform_enable(args.name, cfg) else 1


@assert_attached_root
def action_detach(args, cfg):
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls(cfg)
        if ent.can_disable(silent=True):
            ent.disable(silent=True)
    cfg.delete_cache()
    print(ua_status.MESSAGE_DETACH_SUCCESS)
    return 0


def action_attach(args, cfg):
    if cfg.is_attached:
        print("This machine is already attached to '%s'." %
              cfg.accounts[0]['name'])
        return 0
    if os.getuid() != 0:
        raise exceptions.NonRootUserError()
    contract_client = contract.UAContractClient(cfg)
    if not args.token:
        with util.disable_log_to_console():
            bound_macaroon_bytes = sso.discharge_root_macaroon(contract_client)
        if bound_macaroon_bytes is None:
            print('Could not attach machine. Unable to obtain authenticated'
                  ' user token')
            return 1
        bound_macaroon = bound_macaroon_bytes.decode('utf-8')
        cfg.write_cache('bound-macaroon', bound_macaroon)
        try:
            contract_client.request_accounts(macaroon_token=bound_macaroon)
            contract_token = contract.get_contract_token_for_account(
                contract_client, bound_macaroon, cfg.accounts[0]['id'])
        except (sso.SSOAuthError, util.UrlError) as e:
            logging.error(str(e))
            print('Could not attach machine. Unable to obtain authenticated'
                  ' contract token')
            return 1
    else:
        contract_token = args.token
    if not contract_token:
        print('No valid contract token available')
        return 1
    if not contract.request_updated_contract(
            cfg, contract_token, allow_enable=args.auto_enable):
        print(
            ua_status.MESSAGE_ATTACH_FAILURE_TMPL.format(url=cfg.contract_url))
        return 1
    contract_name = (
        cfg.machine_token['machineTokenInfo']['contractInfo']['name'])
    print(
        ua_status.MESSAGE_ATTACH_SUCCESS_TMPL.format(
            contract_name=contract_name))

    action_status(args=None, cfg=cfg)
    return 0


def get_parser():
    parser = argparse.ArgumentParser(
        prog=NAME, formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        usage=USAGE_TMPL.format(name=NAME, command='[command]'),
        epilog=EPILOG_TMPL.format(name=NAME, command='[command]'))
    parser.add_argument(
        '--debug', action='store_true',
        help='Show all debug log messages to console')
    parser._optionals.title = 'Flags'
    subparsers = parser.add_subparsers(
        title='Available Commands', dest='command', metavar='')
    subparsers.required = True
    parser_status = subparsers.add_parser(
        'status', help='current status of all ubuntu advantage services')
    parser_status.set_defaults(action=action_status)
    status_parser(parser_status)
    parser_attach = subparsers.add_parser(
        'attach',
        help='attach this machine to an ubuntu advantage subscription')
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)
    parser_detach = subparsers.add_parser(
        'detach',
        help='remove this machine from an ubuntu advantage subscription')
    detach_parser(parser_detach)
    parser_detach.set_defaults(action=action_detach)
    parser_enable = subparsers.add_parser(
        'enable',
        help='enable a specific support services on this machine')
    enable_parser(parser_enable)
    parser_enable.set_defaults(action=action_enable)
    parser_disable = subparsers.add_parser(
        'disable',
        help='disable a specific support services on this machine')
    disable_parser(parser_disable)
    parser_disable.set_defaults(action=action_disable)
    parser_refresh = subparsers.add_parser(
        'refresh', help=(
            'Refresh ubuntu-advantage services from contracts server.'))
    parser_refresh.set_defaults(action=action_refresh)
    parser_version = subparsers.add_parser(
        'version', help='Show version of ua-client')
    parser_version.set_defaults(action=print_version)
    return parser


def action_status(args, cfg):
    if not cfg:
        cfg = config.UAConfig()
    if args and args.format == 'json':
        status = cfg.status()
        if status['expires'] != ua_status.UserFacingStatus.INAPPLICABLE.value:
            status['expires'] = str(status['expires'])
        print(json.dumps(status))
    else:
        print(ua_status.format_tabular(cfg.status()))
    return 0


def print_version(_args=None, _cfg=None):
    print(version.get_version())


@assert_attached_root
def action_refresh(args, cfg):
    if contract.request_updated_contract(cfg):
        print(ua_status.MESSAGE_REFRESH_SUCCESS)
        logging.debug(ua_status.MESSAGE_REFRESH_SUCCESS)
        return 0
    raise exceptions.UserFacingError(ua_status.MESSAGE_REFRESH_FAILURE)


def setup_logging(console_level, log_level, log_file=None):
    """Setup console logging and debug logging to log_file"""
    if log_file is None:
        log_file = config.CONFIG_DEFAULTS['log_file']
    console_formatter = util.LogFormatter()
    log_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(log_level)
    # Setup console logging
    stderr_found = False
    for handler in root.handlers:
        if hasattr(handler, 'stream') and hasattr(handler.stream, 'name'):
            if handler.stream.name == '<stderr>':
                handler.setLevel(console_level)
                handler.setFormatter(console_formatter)
                handler.set_name('console')  # Used to disable console logging
                stderr_found = True
                break
    if not stderr_found:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(console_formatter)
        console.setLevel(console_level)
        console.set_name('console')  # Used to disable console logging
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
                logging.exception('KeyboardInterrupt')
            print('Interrupt received; exiting.', file=sys.stderr)
            sys.exit(1)
        except exceptions.UserFacingError as exc:
            with util.disable_log_to_console():
                logging.exception(exc.msg)
            print('ERROR: {}'.format(exc.msg), file=sys.stderr)
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
        print('Try \'ubuntu-advantage --help\' for more information.')
        sys.exit(1)
    args = parser.parse_args(args=cli_arguments)
    cfg = config.UAConfig()
    log_level = cfg.log_level
    console_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(console_level, log_level, cfg.log_file)
    return args.action(args, cfg)


if __name__ == '__main__':
    sys.exit(main())
