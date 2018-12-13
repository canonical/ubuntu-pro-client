import copy
import json
import logging
import os
import six
from subprocess import check_output
import yaml

from uaclient import util

LOG = logging.getLogger(__name__)

PACKAGED_VERSION = '@@PACKAGED_VERSION@@'

DEFAULT_CONFIG_FILE = '/etc/uaclient/uaclient.conf'
BASE_AUTH_URL = 'https://login.ubuntu.com'
BASE_SERVICE_URL = 'https://uaservice.canonical.com'

CONFIG_DEFAULTS = {
    'sso_auth_url': BASE_AUTH_URL,
    'service_url': BASE_SERVICE_URL,
    'data_dir': '~/.local/share/ua-client',
    'log_level': 'info'
}


class ConfigAbsentError(RuntimeError):
    """Raised when no valid config is discovered."""
    pass


class UAConfig(object):

    data_paths = {'accounts': 'accounts.json',
                  'account-contracts': 'account-contracts.json',
                  'account-users': 'account-users.json',
                  'machine-contracts': 'machine-contracts.json',
                  'machine-detach': 'machine-detach.json',
                  'machine-token': 'machine-token.json',
                  'macaroon': 'sso-macaroon.json',
                  'oauth': 'sso-oauth.json'}

    def __init__(self, cfg=None):
        """"""
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = parse_config()

    @property
    def accounts(self):
        """Return the list of accounts that apply to this authorized user."""
        return self.read_cache('accounts')

    @property
    def contract_url(self):
        return self.cfg['contract_url']

    @property
    def data_dir(self):
        return self.cfg['data_dir']

    @property
    def log_level(self):
        return self.cfg['log_level']

    @property
    def sso_auth_url(self):
        return self.cfg['sso_auth_url']

    @property
    def contracts(self):
        """Return the list of contracts that apply to this account."""
        return self.read_cache('account-contracts')

    @property
    def entitlements(self):
        """Return the machine-token if cached in the machine token response."""
        token = self.read_cache('machine-token')
        if not token:
            return None
        return (
            token['machineTokenInfo']['contractInfo']['resourceEntitlements'])

    @property
    def machine_token(self):
        """Return the machine-token if cached in the machine token response."""
        token_response = self.read_cache('machine-token')
        if not token_response:
            return None
        return token_response['machineSecret']

    def data_path(self, key):
        """Return the file path in the data directory represented by the key"""
        if not key:
            return self.cfg['data_dir']
        if key in self.data_paths:
            return os.path.join(self.cfg['data_dir'], self.data_paths[key])
        return os.path.join(self.cfg['data_dir'], key)

    def read_cache(self, key):
        cache_path = self.data_path(key)
        if not os.path.exists(cache_path):
            logging.debug('File does not exist: %s', cache_path)
            return None
        content = util.load_file(cache_path)
        json_content = util.maybe_parse_json(content)
        return json_content if json_content else content

    def write_cache(self, key, content):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        filepath = self.data_path(key)
        if not isinstance(content, six.string_types):
            content = json.dumps(content)
        util.write_file(filepath, content)


def parse_config(config_path=None):
    """Parse known UA config file

    Attempt to find configuration in cwd and fallback to DEFAULT_CONFIG_FILE.
    Any missing configuration keys will be set to CONFIG_DEFAULTS.

    Values are overridden by any environment variable with prefix 'UA_'.

    @param config_path: Fullpath to ua configfile. If unspecified, use
        DEFAULT_CONFIG_FILE.

    @raises: ConfigAbsentError when no config file is discovered.
    @return: Dict of configuration values.
    """
    if not config_path:
        config_path = DEFAULT_CONFIG_FILE
    cfg = copy.copy(CONFIG_DEFAULTS)
    local_cfg = os.path.join(os.getcwd(), os.path.basename(config_path))
    if os.path.exists(local_cfg):
        config_path = local_cfg
    if os.environ.get('UA_CONFIG_FILE'):
        config_path = os.environ.get('UA_CONFIG_FILE')
    LOG.debug('Using UA client configuration file at %s', config_path)
    if os.path.exists(config_path):
        cfg.update(yaml.load(util.load_file(config_path)))
    env_keys = {}
    for key, value in os.environ.items():
        if key.startswith('UA_'):
            env_keys[key.lower()[3:]] = value   # Strip leading UA_
    cfg.update(env_keys)
    cfg['log_level'] = cfg['log_level'].upper()
    cfg['data_dir'] = os.path.expanduser(cfg['data_dir'])
    return cfg


def print_version(_args=None):
    print(get_version())


def get_version(_args=None):
    """Return the package version if set, otherwise return git describe."""
    if PACKAGED_VERSION != '@@PACKAGED_VERSION@@':
        return PACKAGED_VERSION
    return util.decode_binary(check_output([
        'git', 'describe', '--abbrev=8', '--match=[0-9]*', '--long']).strip())
