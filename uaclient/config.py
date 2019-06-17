import copy
from datetime import datetime
import json
import logging
import os
import yaml
from collections import namedtuple

from uaclient import status, util
from uaclient.defaults import CONFIG_DEFAULTS, DEFAULT_CONFIG_FILE
from uaclient import exceptions

try:
    from typing import Any, cast, Dict, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    def cast(_, x):
        return x


DEFAULT_STATUS = {
    'attached': False,
    'expires': status.UserFacingStatus.INAPPLICABLE.value,
    'origin': None,
    'services': [],
    'techSupportLevel': status.UserFacingStatus.INAPPLICABLE.value,
}  # type: Dict[str, Any]

LOG = logging.getLogger(__name__)

PRIVATE_SUBDIR = 'private'


# A data path is a filename, and an attribute ("private") indicating whether it
# should only be readable by root
DataPath = namedtuple('DataPath', ('filename', 'private'))


class UAConfig:

    data_paths = {
        'bound-macaroon': DataPath('bound-macaroon', True),
        'accounts': DataPath('accounts.json', True),
        'account-users': DataPath('account-users.json', True),
        'contract-token': DataPath('contract-token.json', True),
        'local-access': DataPath('local-access', True),
        'machine-contracts': DataPath('machine-contracts.json', True),
        'machine-access-cc-eal': DataPath('machine-access-cc-eal.json', True),
        'machine-access-cis-audit': DataPath(
            'machine-access-cis-audit.json', True),
        'machine-access-esm': DataPath('machine-access-esm.json', True),
        'machine-access-fips': DataPath('machine-access-fips.json', True),
        'machine-access-fips-updates': DataPath(
            'machine-access-fips-updates.json', True),
        'machine-access-livepatch': DataPath(
            'machine-access-livepatch.json', True),
        'machine-access-support': DataPath(
            'machine-access-support.json', True),
        'machine-detach': DataPath('machine-detach.json', True),
        'machine-id': DataPath('machine-id', True),
        'machine-token': DataPath('machine-token.json', True),
        'machine-token-refresh': DataPath('machine-token-refresh.json', True),
        'macaroon': DataPath('sso-macaroon.json', True),
        'root-macaroon': DataPath('root-macaroon.json', True),
        'status-cache': DataPath('status.json', False),
        'oauth': DataPath('sso-oauth.json', True)
    }  # type: Dict[str, DataPath]

    _entitlements = None  # caching to avoid repetitive file reads
    _machine_token = None  # caching to avoid repetitive file reading

    def __init__(self, cfg: 'Dict[str, Any]' = None) -> None:
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
        try:
            return getattr(logging, log_level.upper())
        except AttributeError:
            return getattr(logging, CONFIG_DEFAULTS['log_level'])

    @property
    def log_file(self):
        return self.cfg.get('log_file', CONFIG_DEFAULTS['log_file'])

    @property
    def sso_auth_url(self):
        return self.cfg['sso_auth_url']

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
            entitlement_cfg = {}
            if ent_value.get('entitled'):
                entitlement_cfg = self.read_cache(
                    'machine-access-%s' % entitlement_name, silent=True)
            if not entitlement_cfg:
                # Fallback to machine-token info on unentitled
                entitlement_cfg = {'entitlement': ent_value}
            util.apply_series_overrides(entitlement_cfg)
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

    def data_path(self, key: 'Optional[str]' = None) -> str:
        """Return the file path in the data directory represented by the key"""
        data_dir = self.cfg['data_dir']
        if not key:
            return os.path.join(data_dir, PRIVATE_SUBDIR)
        if key in self.data_paths:
            data_path = self.data_paths[key]
            if data_path.private:
                return os.path.join(
                    data_dir, PRIVATE_SUBDIR, data_path.filename)
            return os.path.join(data_dir, data_path.filename)
        return os.path.join(data_dir, PRIVATE_SUBDIR, key)

    def delete_cache_key(self, key: str) -> None:
        """Remove specific cache file."""
        if not key:
            raise RuntimeError(
                'Invalid or empty key provided to delete_cache_key')
        if key.startswith('machine-access') or key == 'machine-token':
            self._entitlements = None
            self._machine_token = None
        cache_path = self.data_path(key)
        if os.path.exists(cache_path):
            os.unlink(cache_path)

    def delete_cache(self):
        """Remove configuration cached response files class attributes."""
        for path_key in self.data_paths.keys():
            self.delete_cache_key(path_key)

    def read_cache(self, key: str, silent: bool = False) -> 'Optional[Any]':
        cache_path = self.data_path(key)
        try:
            content = util.load_file(cache_path)
        except Exception:
            if not os.path.exists(cache_path) and not silent:
                logging.debug('File does not exist: %s', cache_path)
            return None
        json_content = util.maybe_parse_json(content)
        return json_content if json_content else content

    def write_cache(self, key: str, content: 'Any') -> None:
        filepath = self.data_path(key)
        data_dir = os.path.dirname(filepath)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        if key.startswith('machine-access') or key == 'machine-token':
            self._machine_token = None
            self._entitlements = None
        if not isinstance(content, str):
            content = json.dumps(content)
        mode = 0o600
        if key in self.data_paths:
            if not self.data_paths[key].private:
                mode = 0o644
        util.write_file(filepath, content, mode=mode)

    def _status(self) -> 'Dict[str, Any]':
        """Return configuration status as a dictionary."""
        from uaclient.entitlements import ENTITLEMENT_CLASSES
        response = copy.deepcopy(DEFAULT_STATUS)
        response['attached'] = self.is_attached
        if not self.is_attached:
            return response
        response['account'] = self.accounts[0]['name']
        contractInfo = self.machine_token['machineTokenInfo']['contractInfo']
        response['subscription'] = contractInfo['name']
        if contractInfo.get('effectiveTo'):
            response['expires'] = datetime.strptime(
                contractInfo['effectiveTo'], '%Y-%m-%dT%H:%M:%SZ')
        response['origin'] = contractInfo.get('origin')
        for ent_cls in ENTITLEMENT_CLASSES:
            ent = ent_cls(self)
            contract_status = ent.contract_status().value
            status, details = ent.user_facing_status()
            service_status = {
                'name': ent.name, 'entitled': contract_status,
                'status': status.value, 'statusDetails': details}
            response['services'].append(service_status)
        support = self.entitlements.get('support', {}).get('entitlement')
        if support:
            supportLevel = support.get('affordances', {}).get('supportLevel')
            if not supportLevel:
                supportLevel = DEFAULT_STATUS['techSupportLevel']
            response['techSupportLevel'] = supportLevel
        return response

    def status(self) -> 'Dict[str, Any]':
        """Return status as a dict, using a cache for non-root users"""
        if os.getuid() == 0:
            status = self._status()
            self.write_cache('status-cache', status)
            return status
        cached_status = cast('Dict[str, Any]', self.read_cache('status-cache'))
        if not cached_status:
            return DEFAULT_STATUS
        return cached_status


def parse_config(config_path=None):
    """Parse known UA config file

    Attempt to find configuration in cwd and fallback to DEFAULT_CONFIG_FILE.
    Any missing configuration keys will be set to CONFIG_DEFAULTS.

    Values are overridden by any environment variable with prefix 'UA_'.

    @param config_path: Fullpath to ua configfile. If unspecified, use
        DEFAULT_CONFIG_FILE.

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
        key = key.lower()
        if key.startswith('ua_'):
            env_keys[key[3:]] = value   # Strip leading UA_
    cfg.update(env_keys)
    cfg['log_level'] = cfg['log_level'].upper()
    cfg['data_dir'] = os.path.expanduser(cfg['data_dir'])
    errors = []
    for cfg_key in ('contract_url', 'sso_auth_url'):
        if not util.is_service_url(cfg[cfg_key]):
            errors.append(
                'Invalid url in config. %s: %s' % (cfg_key, cfg[cfg_key]))
    if errors:
        raise exceptions.UserFacingError('\n'.join(errors))
    return cfg
