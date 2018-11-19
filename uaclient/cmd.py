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
import os
import sys


from uaclient import config
from uaclient import entitlements
from uaclient import status as ua_status


USAGE = '{name} [command] [flags]'.format(name=NAME)
EPILOG = (
    'Use {name} [command] --help for more information about a command.'.format(
        name=NAME))


def attach_parser(parser=None):
    """Build or extend an arg parser for attach subcommand."""
    if not parser:
        parser = argparse.ArgumentParser(
            prog='attach',
            description=('Remove logs and artifacts so cloud-init re-runs on '
                         'a clean system'))

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
    parser_status.set_defaults(action=get_status)
    parser_attach = subparsers.add_parser(
        'attach',
        help='attach this machine to an ubuntu advantage subscription')
    parser_detach = subparsers.add_parser(
        'detach',
         help='remove this machine from an ubuntu advantage subscription')
    parser_enable = subparsers.add_parser(
        'enable',
         help='enable a specific support entitlement on this machine')
    parser_enable = subparsers.add_parser(
        'disable',
         help='disable a specific support entitlement on this machine')
    parser_version = subparsers.add_parser(
        'version', help='Show version of ua-client')
    parser_version.set_defaults(action=config.print_version)
    return parser



STATUS_HEADER_TMPL = """\
Account: {account}
Subscription: {subscription}
Valid until: {expiry}
"""


def get_entitlements():
    """Return a dictionary of entitlement details."""
    return {'account': 'Blackberry Limited',
            'subscription':  'blackberry/desktops',
            'expiry': '2019-12-31'}


def get_status(args=None):
    print(STATUS_HEADER_TMPL.format(**get_entitlements()))

    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls()
        operational_state, status = ent.status()
        print(ua_status.format_entitlement_status(ent))
    print(ua_status.STATUS_TMPL.format(
          name='support',
          contract_state=ua_status.STATUS_COLOR.get(
              ua_status.ESSENTIAL, ua_status.ESSENTIAL),
          status=''))
    print('')


def main(sys_argv=None):
    if not sys_argv:
        sys_argv = sys.argv
    parser = get_parser()
    args = parser.parse_args(args=sys_argv[1:])
    args.action(args)
    return 0


if __name__ == '__main__':
   sys.exit(main())


