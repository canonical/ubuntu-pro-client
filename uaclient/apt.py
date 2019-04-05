import glob
import logging
import os
import shutil

from uaclient import util

APT_CONFIG_AUTH_FILE = 'Dir::Etc::netrc/'
APT_CONFIG_AUTH_PARTS_DIR = 'Dir::Etc::netrcparts/'
APT_CONFIG_LISTS_DIR = 'Dir::State::lists/'
APT_KEYS_DIR = '/etc/apt/trusted.gpg.d'
KEYRINGS_DIR = '/usr/share/keyrings'
APT_METHOD_HTTPS_FILE = '/usr/lib/apt/methods/https'
CA_CERTIFICATES_FILE = '/usr/sbin/update-ca-certificates'

APT_AUTH_HEADER = """
# This file is created by ubuntu-advantage-tools and will be updated
# by subsequent calls to ua attach|detach [entitlement]
"""


class InvalidAPTCredentialsError(RuntimeError):
    """Raised when invalid token is provided for APT access"""
    pass


def valid_apt_credentials(repo_url, series, credentials):
    """Validate apt credentials for a PPA.

    @param repo_url: private-ppa url path
    @param credentials: PPA credentials string username:password.
    @param series: xenial, bionic ...

    @return: True if valid or unable to validate
    """
    protocol, repo_path = repo_url.split('://')
    if not os.path.exists('/usr/lib/apt/apt-helper'):
        return True   # Do not validate
    try:
        util.subp(['/usr/lib/apt/apt-helper', 'download-file',
                   '%s://%s@%s/ubuntu/dists/%s/Release' % (
                       protocol, credentials, repo_path, series),
                   '/tmp/uaclient-apt-test'],
                  capture=False)  # Hide credentials from logs
        os.unlink('/tmp/uaclient-apt-test')
        return True
    except util.ProcessExecutionError:
        pass
    if os.path.exists('/tmp/uaclient-apt-test'):
        os.unlink('/tmp/uaclient-apt-test')
    return False


def add_auth_apt_repo(repo_filename, repo_url, credentials=None,
                      keyring_file=None, fingerprint=None):
    """Add an authenticated apt repo and credentials to the system.

    @raises: InvalidAPTCredentialsError when the token provided can't access
        the repo PPA.
    """
    series = util.get_platform_info('series')
    if repo_url.endswith('/'):
        repo_url = repo_url[:-1]
    if credentials:
        if not valid_apt_credentials(repo_url, series, credentials):
            raise InvalidAPTCredentialsError(
                'Invalid APT credentials provided for %s' % repo_url)
    logging.info('Enabling authenticated repo: %s', repo_url)
    content = (
        'deb {url}/ubuntu {series} main\n'
        '# deb-src {url}/ubuntu {series} main\n'.format(
            url=repo_url, series=series))
    util.write_file(repo_filename, content)
    if not credentials:
        return
    try:
        login, password = credentials.split(':')
    except ValueError:  # Then we have a bearer token
        login = 'bearer'
        password = credentials
    apt_auth_file = get_apt_auth_file_from_apt_config()
    if os.path.exists(apt_auth_file):
        auth_content = util.load_file(apt_auth_file)
    else:
        auth_content = APT_AUTH_HEADER
    _protocol, repo_path = repo_url.split('://')
    if repo_path.endswith('/'):  # strip trailing slash
        repo_path = repo_path[:-1]
    auth_content += (
        'machine {repo_path}/ubuntu/ login {login} password'
        ' {password}\n'.format(
            repo_path=repo_path, login=login, password=password))
    util.write_file(apt_auth_file, auth_content, mode=0o600)
    if keyring_file:
        logging.debug('Copying %s to %s', keyring_file, APT_KEYS_DIR)
        shutil.copy(keyring_file, APT_KEYS_DIR)
    elif fingerprint:
        logging.debug('Importing APT key %s', fingerprint)
        util.subp(
            ['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
             '--recv-keys', fingerprint], capture=True)


def remove_auth_apt_repo(repo_filename, repo_url, keyring_file=None,
                         fingerprint=None):
    """Remove an authenticated apt repo and credentials to the system"""
    logging.info('Removing authenticated apt repo: %s', repo_url)
    util.del_file(repo_filename)
    if keyring_file:
        util.del_file(keyring_file)
    elif fingerprint:
        util.subp(['apt-key', 'del', fingerprint], capture=True)
    _protocol, repo_path = repo_url.split('://')
    if repo_path.endswith('/'):  # strip trailing slash
        repo_path = repo_path[:-1]
    apt_auth_file = get_apt_auth_file_from_apt_config()
    if os.path.exists(apt_auth_file):
        apt_auth = util.load_file(apt_auth_file)
        auth_prefix = 'machine {repo_path}/ubuntu/ login'.format(
            repo_path=repo_path)
        content = '\n'.join([
            line for line in apt_auth.split('\n') if auth_prefix not in line])
        if not content or content == APT_AUTH_HEADER:
            os.unlink(apt_auth_file)
        else:
            util.write_file(apt_auth_file, content, mode=0o600)


def add_ppa_pinning(apt_preference_file, repo_url, origin, priority):
    """Add an apt preferences file and pin for a PPA."""
    series = util.get_platform_info('series')
    _protocol, repo_path = repo_url.split('://')
    if repo_path.endswith('/'):  # strip trailing slash
        repo_path = repo_path[:-1]
    content = (
        'Package: *\n'
        'Pin: release o={origin}, n={series}\n'
        'Pin-Priority: {priority}\n'.format(
            origin=origin, priority=priority, series=series))
    util.write_file(apt_preference_file, content)


def get_apt_auth_file_from_apt_config():
    """Return to patch to the system configured APT auth file."""
    out, _err = util.subp(
        ['apt-config', 'shell', 'key', APT_CONFIG_AUTH_PARTS_DIR])
    if out:  # then auth.conf.d parts is present
        return out.split("'")[1] + '90ubuntu-advantage'
    else:    # then use configured /etc/apt/auth.conf
        out, _err = util.subp(
            ['apt-config', 'shell', 'key', APT_CONFIG_AUTH_FILE])
        return out.split("'")[1].rstrip('/')


def find_apt_list_files(repo_url, series):
    """List any apt files in APT_CONFIG_LISTS_DIR given repo_url and series."""
    _protocol, repo_path = repo_url.split('://')
    if repo_path.endswith('/'):  # strip trailing slash
        repo_path = repo_path[:-1]
    lists_dir = '/var/lib/apt/lists'
    out, _err = util.subp(
        ['apt-config', 'shell', 'key', APT_CONFIG_LISTS_DIR])
    if out:  # then lists dir is present in config
        lists_dir = out.split("'")[1]

    aptlist_filename = repo_path.replace('/', '_')
    return sorted(glob.glob(
        os.path.join(lists_dir, aptlist_filename + '_dists_%s*' % series)))


def remove_apt_list_files(repo_url, series):
    """Remove any apt list files present for this repo_url and series."""
    for path in find_apt_list_files(repo_url, series):
        if os.path.exists(path):
            os.unlink(path)


def migrate_apt_sources(cfg=None, platform_info=None):
    """Migrate apt sources list files across upgrade/downgrade boundary.

    Only migrate apt sources if we are attached and an entitlement is
    active. (Meaning they have existing apt policy reference).

    @param cfg: UAClient configuration instance for testing
    @param cfg: platform information dict for testing
    """

    from uaclient import config
    from uaclient import entitlements
    from uaclient import status

    if not platform_info:  # for testing
        platform_info = util.get_platform_info()
    if not cfg:  # for testing
        cfg = config.UAConfig()
    if not cfg.is_attached:
        return
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        if not hasattr(ent_cls, 'repo_url'):
            continue
        entitlement = ent_cls(cfg)
        op_status, _details = entitlement.operational_status()
        if op_status != status.ACTIVE:
            continue
        repo_list_glob = entitlement.repo_list_file_tmpl.format(
            name=entitlement.name, series='*')
        # Remove invalid series list files
        for path in glob.glob(repo_list_glob):
            if platform_info['series'] not in path:
                logging.info('Removing old apt source file: %s', path)
                os.unlink(path)
        pass_affordances, details = entitlement.check_affordances()
        if not pass_affordances:
            logging.info(
                'Disabled %s after package upgrade/downgrade. %s',
                entitlement.title, details)
        entitlement.enable()  # Re-enable on current series


def configure_default_apt_sources(platform_info=None):
    """Configure any default apt sources for uaclient entitlenents.

    Currently only setup unauthenticated esm on trusty.

    @param platform_info: dict of platform information for testing
    """
    from uaclient import entitlements

    if not platform_info:  # for testing
        platform_info = util.get_platform_info()

    esm_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME['esm']
    repo_filename = esm_cls.repo_list_file_tmpl.format(
        name=esm_cls.name, series=platform_info['series'])
    if platform_info['series'] == 'trusty':
        if not os.path.exists(repo_filename):
            logging.info('Providing unauthenticated ESM apt source file: %s',
                         repo_filename)
            add_auth_apt_repo(repo_filename, esm_cls.repo_url)
