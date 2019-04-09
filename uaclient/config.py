import copy
import json
import logging
import os
import yaml

from uaclient import util
from uaclient.defaults import CONFIG_DEFAULTS, DEFAULT_CONFIG_FILE

LOG = logging.getLogger(__name__)


class ConfigAbsentError(RuntimeError):
    """Raised when no valid config is discovered."""
    pass


class UAConfig(object):

    data_paths = {
        'bound-macaroon': 'bound-macaroon',
        'accounts': 'accounts.json',
        'account-contracts': 'account-contracts.json',
        'account-users': 'account-users.json',
        'contract-token': 'contract-token.json',
        'machine-contracts': 'machine-contracts.json',
        'machine-access-cc': 'machine-access-cc.json',
        'machine-access-cis-audit': 'machine-access-cis-audit.json',
        'machine-access-esm': 'machine-access-esm.json',
        'machine-access-fips': 'machine-access-fips.json',
        'machine-access-fips-updates': 'machine-access-fips-updates.json',
        'machine-access-livepatch': 'machine-access-livepatch.json',
        'machine-access-support': 'machine-access-support.json',
        'machine-detach': 'machine-detach.json',
        'machine-token': 'machine-token.json',
        'macaroon': 'sso-macaroon.json',
        'root-macaroon': 'root-macaroon.json',
        'oauth': 'sso-oauth.json'
    }

    _contracts = None  # caching to avoid repetitive file reads
    _entitlements = None  # caching to avoid repetitive file reads
    _machine_token = None  # caching to avoid repetitive file reading

    def __init__(self, cfg=None):
        """"""
        if cfg:
            self.cfg = cfg
        else:
            self.cfg = parse_config()

    @property
    def accounts(self):
        """Return the list of accounts that apply to this authorized user."""
        accounts = self.read_cache('accounts')
        if not accounts:
            if self.is_attached:
                accountInfo = self.machine_token[
                    'machineTokenInfo']['accountInfo']
                return [accountInfo]
            return []
        warning_msg = None
        if not isinstance(accounts, dict):
            warning_msg = ('Unexpected type %s in cache %s' %
                           (type(accounts), self.data_path('accounts')))
        elif 'accounts' not in accounts:
            warning_msg = ("Missing 'accounts' key in cache %s" %
                           self.data_path('accounts'))
        elif not isinstance(accounts['accounts'], list):
            warning_msg = (
                "Unexpected 'accounts' type %s in cache %s" %
                (type(accounts['accounts']), self.data_path('accounts')))
        if warning_msg:
            LOG.warning(warning_msg)
            return []
        return accounts['accounts']

    @property
    def contract_url(self):
        return self.cfg.get('contract_url', 'https://contracts.canonical.com')

    @property
    def data_dir(self):
        return self.cfg['data_dir']

    @property
    def log_level(self):
        log_level = self.cfg.get('log_level')
        if log_level:
            log_level = getattr(logging, log_level.upper())
        try:
            int(log_level)
        except TypeError:
            return CONFIG_DEFAULTS['log_level']
        return log_level

    @property
    def log_file(self):
        return self.cfg.get('log_file', CONFIG_DEFAULTS['log_file'])

    @property
    def sso_auth_url(self):
        return self.cfg['sso_auth_url']

    @property
    def contracts(self):
        """Return the list of contracts that apply to this account."""
        if not self._contracts:
            self._contracts = self.read_cache('account-contracts')
        return self._contracts or []

    @property
    def entitlements(self):
        """Return a dictionary of entitlements keyed by entitlement name.

        Return an empty dict if no entitlements are present.
        """
        if self._entitlements:
            return self._entitlements
        machine_token = self.machine_token
        if not machine_token:
            return {}

        self._entitlements = {}
        contractInfo = machine_token['machineTokenInfo']['contractInfo']
        ent_by_name = dict(
            (e['type'], e) for e in contractInfo['resourceEntitlements'])
        for entitlement_name, ent_value in ent_by_name.items():
            entitlement_cfg = self.read_cache(
                'machine-access-%s' % entitlement_name, quiet=True)
            if not entitlement_cfg:
                # Fallback to machine-token info on unentitled
                entitlement_cfg = {'entitlement': ent_value}
            self._entitlements[entitlement_name] = entitlement_cfg
        return self._entitlements

    @property
    def is_attached(self):
        """Report whether this machine configuration is attached to UA."""
        return bool(self.machine_token)   # machine_token is removed on detach

    @property
    def machine_token(self):
        """Return the machine-token if cached in the machine token response."""
        if not self._machine_token:
            self._machine_token = self.read_cache('machine-token')
        return self._machine_token

    def data_path(self, key=None):
        """Return the file path in the data directory represented by the key"""
        if not key:
            return self.cfg['data_dir']
        if key in self.data_paths:
            return os.path.join(self.cfg['data_dir'], self.data_paths[key])
        return os.path.join(self.cfg['data_dir'], key)

    def delete_cache(self):
        """Remove all configuration cached response files class attributes."""
        self._contracts = None
        self._entitlements = None
        self._machine_token = None
        for key in self.data_paths.keys():
            cache_path = self.data_path(key)
            if os.path.exists(cache_path):
                os.unlink(cache_path)

    def read_cache(self, key, quiet=False):
        cache_path = self.data_path(key)
        if not os.path.exists(cache_path):
            if not quiet:
                logging.debug('File does not exist: %s', cache_path)
            return None
        content = util.load_file(cache_path)
        json_content = util.maybe_parse_json(content)
        return json_content if json_content else content

    def write_cache(self, key, content):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        filepath = self.data_path(key)
        if not isinstance(content, str):
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
        cfg.update(yaml.safe_load(util.load_file(config_path)))
    env_keys = {}
    for key, value in os.environ.items():
        if key.startswith('UA_'):
            env_keys[key.lower()[3:]] = value   # Strip leading UA_
    cfg.update(env_keys)
    cfg['log_level'] = cfg['log_level'].upper()
    cfg['data_dir'] = os.path.expanduser(cfg['data_dir'])
    return cfg
