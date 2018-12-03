#!/usr/bin/env python

"""\
Client to manage Ubuntu Advantage support entitlements on a machine.

Available entitlements:
 - Ubuntu Extended Security Maintenance archive (https://ubuntu.com/esm)
 - Canonical FIPS 140-2 Certified Modules
 - Canonical FIPS 140-2 Non-Certified Module Updates
 - Canonical Livepatch Service (https://www.ubuntu.com/server/livepatch)

"""

NAME = 'ubuntu-advantage-client'

import argparse
import json
import logging
import os
import sys


from uaclient import config
from uaclient import entitlements
from uaclient import status as ua_status
from uaclient import sso
from uaclient import contract
from uaclient import util


USAGE = '{name} [command] [flags]'.format(name=NAME)
EPILOG = (
    'Use {name} [command] --help for more information about a command.'.format(
        name=NAME))


def attach_parser(parser=None):
    """Build or extend an arg parser for attach subcommand."""
    if not parser:
        parser = argparse.ArgumentParser(
            prog='attach',
            description=('Attach this machine to an existing Ubuntu Advantage'
                         ' support subscription'))
    parser.add_argument('token', nargs='?', help='Support Token obtained from Ubuntu Advantage dashboard')
    parser.add_argument('--email', action='store', help='Optional email address for Ubuntu SSO login')
    parser.add_argument('--password', action='store', help='Optional password for Ubuntu SSO login')

    parser.add_argument('--otp', action='store', help='Optional one-time password for login to Ubuntu Advantage Dashboard')
    return parser


def enable_parser(parser=None):
    """Build or extend an arg parser for enable subcommand."""
    if not parser:
        parser = argparse.ArgumentParser(
            prog='enable',
            description='Enable a support entitlement on this machine')
    entitlement_names = list(
        cls.name for cls in entitlements.ENTITLEMENT_CLASSES)
    parser.add_argument(
        'name', action='store', choices=entitlement_names,
        help='The name of the support entitlement to enable')
    return parser


def disable_parser(parser=None):
    """Build or extend an arg parser for disable subcommand."""
    if not parser:
        parser = argparse.ArgumentParser(
            prog='disable',
            description='Disable a support entitlement on this machine')
    entitlement_names = list(
        cls.name for cls in entitlements.ENTITLEMENT_CLASSES)
    parser.add_argument(
        'name', action='store', choices=entitlement_names,
        help='The name of the support entitlement to disable')
    return parser


def action_disable(args):
    """Perform the disable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    cfg = config.UAConfig()
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[args.name]
    entitlement = ent_cls(cfg)
    return 0 if entitlement.disable() else 1

def action_enable(args):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    cfg = config.UAConfig()
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[args.name]
    entitlement = ent_cls(cfg)
    return 0 if entitlement.enable() else 1


def action_attach(args):
    cfg = config.UAConfig()
    entitlement_status = cfg.entitlements
    if entitlement_status:
        print("This machine is already attached to '%s'." %
              entitlement_status['subscription'])
        return 0
    if os.getuid() != 0:
        print(ua_status.MESSAGE_NONROOT_USER)
        return 1
    if not args.token:
        user_token = sso.prompt_oauth_token()
    else:
        user_token = args.token
    if not user_token:
        print('Could not attach machine. Unable to obtain authenticated user'
              ' token')
        return 1
    contract_client = contract.UAContractClient(cfg)
    try:
        token_response = contract_client.request_machine_attach(
            user_token['token_key'])
    except (sso.SSOAuthError, util.UrlError) as e:
        logging.error(str(e))
        return 1
    machine_token = token_response['machine-token']
    entitlement_status = contract_client.request_status(machine_token)
    print("This machine is now attached to '%s'.\n" %
          entitlement_status['subscription'])
    print_status()
    return 0


def get_parser():
    parser = argparse.ArgumentParser(
        prog=NAME, formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__, usage=USAGE,
         epilog=EPILOG)
    parser.add_argument('--debug', action='store_true', help='Show all debug messages')
    parser._optionals.title = 'Flags'
    subparsers = parser.add_subparsers(
        title='Available Commands', dest='command', metavar='')
    subparsers.required = True
    parser_status = subparsers.add_parser(
        'status', help='current status of all ubuntu advantage entitlements')
    parser_status.set_defaults(action=print_status)
    parser_attach = subparsers.add_parser(
        'attach',
        help='attach this machine to an ubuntu advantage subscription')
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)
    parser_detach = subparsers.add_parser(
        'detach',
         help='remove this machine from an ubuntu advantage subscription')
    parser_enable = subparsers.add_parser(
        'enable',
         help='enable a specific support entitlement on this machine')
    enable_parser(parser_enable)
    parser_enable.set_defaults(action=action_enable)
    parser_disable = subparsers.add_parser(
        'disable',
         help='disable a specific support entitlement on this machine')
    disable_parser(parser_disable)
    parser_disable.set_defaults(action=action_disable)
    parser_version = subparsers.add_parser(
        'version', help='Show version of ua-client')
    parser_version.set_defaults(action=config.print_version)
    return parser



STATUS_HEADER_TMPL = """\
Account: {account}
Subscription: {subscription}
Valid until: {contract-expiry}
"""


def print_status(args=None):
    cfg = config.UAConfig()
    if not cfg.machine_token:
        print('This machine is not attached to a UA subscription.\n'
              'See `ua attach` or https://ubuntu.com/advantage')
        return
    entitlement_status = cfg.entitlements
    if not entitlement_status:
         contract_client = contract.UAContractClient(cfg)
         entitlement_status = contract_client.request_status(machine_token)
    print(STATUS_HEADER_TMPL.format(**entitlement_status))

    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls()
        print(ua_status.format_entitlement_status(ent))
    print(ua_status.STATUS_TMPL.format(
          name='support',
          contract_state=ua_status.STATUS_COLOR.get(
              ua_status.ESSENTIAL, ua_status.ESSENTIAL),
          status=''))
    print('\nEnable entitlements with `ua enable <service>\n')


def setup_logging(level=logging.ERROR):
    fmt = '[%(levelname)s]: %(message)s'
    formatter = logging.Formatter(fmt)
    root = logging.getLogger()
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)
    root.setLevel(level)


def main(sys_argv=None):
    if not sys_argv:
        sys_argv = sys.argv
    parser = get_parser()
    args = parser.parse_args(args=sys_argv[1:])
    log_level = logging.DEBUG if args.debug else logging.ERROR
    setup_logging(log_level)
    return args.action(args)


if __name__ == '__main__':
   sys.exit(main())


