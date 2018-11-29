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
            description=('Remove logs and artifacts so cloud-init re-runs on '
                         'a clean system'))
    parser.add_argument('token', nargs='?', help='Support Token obtained from Ubuntu Advantage dashboard')
    parser.add_argument('--email', action='store', help='Optional email address for Ubuntu SSO login')
    parser.add_argument('--password', action='store', help='Optional password for Ubuntu SSO login')

    parser.add_argument('--otp', action='store', help='Optional one-time password for login to Ubuntu Advantage Dashboard')


def ua_attach(args):
    cfg = config.parse_config()
    data_dir = cfg['data_dir']
    entitlements_path = os.path.join(data_dir, 'entitlements.json')
    if os.path.exists(entitlements_path):
        entitlements = json.loads(util.load_file(entitlements_path))
        print("This machine is already attached to '%s'." %
              entitlements['subscription'])
        return 0
    if not args.token:
        caveat_id = {'version': 1, 'secret': 'encoded-secret'}
        try:
         user_token = sso.prompt_request_macaroon(caveat_id=caveat_id)
        except sso.SSOAuthError as e:
         import pdb; pdb.set_trace()
    else:
        user_token = args.token
    machine_token_path = os.path.join(data_dir, 'machine-token.json')
    contract_client = contract.UAContractClient()
    try:
        token_response = contract_client.request_machine_attach(user_token)
    except (sso.SSOAuthError, util.UrlError) as e:
        logging.error(str(e))
        return 1
    util.write_file(machine_token_path, token_response)
    machine_token = token_response['machine-token']
    entitlements = contract_client.request_entitlements(machine_token)
    print("This machine is now attached to '%s'.\n" %
          entitlements['subscription'])
    get_status()
    util.write_file(entitlements_path, json.dumps(entitlements))
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
    parser_status.set_defaults(action=get_status)
    parser_attach = subparsers.add_parser(
        'attach',
        help='attach this machine to an ubuntu advantage subscription')
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=ua_attach)
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


