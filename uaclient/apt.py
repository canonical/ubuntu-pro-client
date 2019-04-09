import glob
import logging
import os
import re
import shutil

from uaclient import util

APT_AUTH_COMMENT = '  # ubuntu-advantage-tools'
APT_CONFIG_AUTH_FILE = 'Dir::Etc::netrc/'
APT_CONFIG_AUTH_PARTS_DIR = 'Dir::Etc::netrcparts/'
APT_CONFIG_LISTS_DIR = 'Dir::State::lists/'
APT_KEYS_DIR = '/etc/apt/trusted.gpg.d'
KEYRINGS_DIR = '/usr/share/keyrings'
APT_METHOD_HTTPS_FILE = '/usr/lib/apt/methods/https'
CA_CERTIFICATES_FILE = '/usr/sbin/update-ca-certificates'


class InvalidAPTCredentialsError(RuntimeError):
    """Raised when invalid token is provided for APT access"""
    pass


def valid_apt_credentials(repo_url, username, password):
    """Validate apt credentials for a PPA.

    @param repo_url: private-ppa url path
    @param username: PPA login username.
    @param password: PPA login password or resource token.

    @return: True if valid or unable to validate
    """
    protocol, repo_path = repo_url.split('://')
    if not os.path.exists('/usr/lib/apt/apt-helper'):
        return True   # Do not validate
    try:
        util.subp(['/usr/lib/apt/apt-helper', 'download-file',
                   '%s://%s:%s@%s/ubuntu/pool/' % (
                       protocol, username, password, repo_path),
                   '/tmp/uaclient-apt-test'],
                  capture=False)  # Hide credentials from logs
        return True
    except util.ProcessExecutionError:
        pass
    finally:
        if os.path.exists('/tmp/uaclient-apt-test'):
            os.unlink('/tmp/uaclient-apt-test')
    return False


def add_auth_apt_repo(repo_filename, repo_url, credentials, suites,
                      keyring_file=None, fingerprint=None):
    """Add an authenticated apt repo and credentials to the system.

    @raises: InvalidAPTCredentialsError when the token provided can't access
        the repo PPA.
    """
    try:
        username, password = credentials.split(':')
    except ValueError:  # Then we have a bearer token
        username = 'bearer'
        password = credentials
    series = util.get_platform_info('series')
    if repo_url.endswith('/'):
        repo_url = repo_url[:-1]
    if not valid_apt_credentials(repo_url, username, password):
        raise InvalidAPTCredentialsError(
            'Invalid APT credentials provided for %s' % repo_url)

    updates_enabled = True   # TODO determine from apt-cache policy

    logging.info('Enabling authenticated repo: %s', repo_url)
    content = ''
    for suite in suites:
        if series not in suite:
            continue   # Only enable suites matching this current series
        if '-updates' in suite and not updates_enabled:
            logging.debug(
                'Not enabling apt suite "%s" because "%s-updates" is not'
                ' enabled', suite, series)
            continue
        content += ('deb {url}/ubuntu {suite} main\n'
                    '# deb-src {url}/ubuntu {suite} main\n'.format(
                        url=repo_url, suite=suite))
    util.write_file(repo_filename, content)
    add_apt_auth_conf_entry(repo_url, username, password)
    if keyring_file:
        logging.debug('Copying %s to %s', keyring_file, APT_KEYS_DIR)
        shutil.copy(keyring_file, APT_KEYS_DIR)
    elif fingerprint:
        logging.debug('Importing APT key %s', fingerprint)
        util.subp(
            ['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
             '--recv-keys', fingerprint], capture=True)


def add_apt_auth_conf_entry(repo_url, login, password):
    """Add or replace an apt auth line in apt's auth.conf file or conf.d."""
    apt_auth_file = get_apt_auth_file_from_apt_config()
    _protocol, repo_path = repo_url.split('://')
    if repo_path.endswith('/'):  # strip trailing slash
        repo_path = repo_path[:-1]
    if os.path.exists(apt_auth_file):
        orig_content = util.load_file(apt_auth_file)
    else:
        orig_content = ''
    repo_auth_line = (
        'machine {repo_path}/ login {login} password {password}{cmt}'.format(
            repo_path=repo_path, login=login, password=password,
            cmt=APT_AUTH_COMMENT))
    added_new_auth = False
    new_lines = []
    for line in orig_content.splitlines():
        machine_match = re.match(r'machine\s+(?P<repo_url>[.\-\w]+)/?.*', line)
        if machine_match:
            matched_repo = machine_match.group('repo_url')
            if matched_repo == repo_path:
                # Replace old auth with new auth at same line
                new_lines.append(repo_auth_line)
                added_new_auth = True
                continue
            if matched_repo in repo_path:
                # Insert our repo before. We are a more specific apt repo match
                new_lines.append(repo_auth_line)
                added_new_auth = True
        new_lines.append(line)
    if not added_new_auth:
        new_lines.append(repo_auth_line)
    util.write_file(apt_auth_file, '\n'.join(new_lines), mode=0o600)


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
        auth_prefix = 'machine {repo_path}/ login'.format(
            repo_path=repo_path)
        content = '\n'.join([
            line for line in apt_auth.splitlines() if auth_prefix not in line])
        if not content:
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


def migrate_apt_sources(clean=False, cfg=None, platform_info=None):
    """Migrate apt sources list files across upgrade/downgrade boundary.

    Only migrate apt sources if we are attached and an entitlement is
    active. (Meaning they have existing apt policy reference).

    @param clean: Boolean set True to clean up any apt config files written by
        Ubuntu Advantage Client.
    @param cfg: UAClient configuration instance for testing
    @param platform_info: platform information dict for testing
    """

    from uaclient import config
    from uaclient import entitlements
    from uaclient import status

    if not platform_info:  # for testing
        platform_info = util.get_platform_info()
    if not cfg:  # for testing
        cfg = config.UAConfig()
    if not any([cfg.is_attached, clean]):
        return
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        if not hasattr(ent_cls, 'repo_url'):
            continue
        repo_list_glob = ent_cls.repo_list_file_tmpl.format(
            name=ent_cls.name, series='*')

        # Remove invalid series list files
        for path in glob.glob(repo_list_glob):
            if platform_info['series'] not in path:
                logging.info('Removing old apt source file: %s', path)
                os.unlink(path)
        if clean:
            continue  # Skip any re-enable operations
        entitlement = ent_cls(cfg)
        op_status, _details = entitlement.operational_status()
        if op_status != status.ACTIVE:
            continue
        pass_affordances, details = entitlement.check_affordances()
        if not pass_affordances:
            logging.info(
                'Disabled %s after package upgrade/downgrade. %s',
                entitlement.title, details)
        entitlement.enable()  # Re-enable on current series
