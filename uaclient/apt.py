import glob
import logging
import os
import re
import shutil
import subprocess

from uaclient import exceptions
from uaclient import status
from uaclient import util

try:
    from typing import List  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

APT_HELPER_TIMEOUT = 20.0    # 20 second timeout used for apt-helper call
APT_AUTH_COMMENT = '  # ubuntu-advantage-tools'
APT_CONFIG_AUTH_FILE = 'Dir::Etc::netrc/'
APT_CONFIG_AUTH_PARTS_DIR = 'Dir::Etc::netrcparts/'
APT_CONFIG_LISTS_DIR = 'Dir::State::lists/'
APT_KEYS_DIR = '/etc/apt/trusted.gpg.d'
KEYRINGS_DIR = '/usr/share/keyrings'
APT_METHOD_HTTPS_FILE = '/usr/lib/apt/methods/https'
CA_CERTIFICATES_FILE = '/usr/sbin/update-ca-certificates'

# Since we generally have a person at the command line prompt. Don't loop
# for 5 minutes like charmhelpers because we expect the human to notice and
# resolve to apt conflict or try again.
# Hope for an optimal first try.
APT_RETRIES = [1.0, 5.0, 10.0]


def assert_valid_apt_credentials(repo_url, username, password):
    """Validate apt credentials for a PPA.

    @param repo_url: private-ppa url path
    @param username: PPA login username.
    @param password: PPA login password or resource token.

    @raises: UserFacingError for invalid credentials, timeout or unexpected
        errors.
    """
    protocol, repo_path = repo_url.split('://')
    if not os.path.exists('/usr/lib/apt/apt-helper'):
        return
    try:
        util.subp(['/usr/lib/apt/apt-helper', 'download-file',
                   '%s://%s:%s@%s/ubuntu/pool/' % (
                       protocol, username, password, repo_path),
                   '/tmp/uaclient-apt-test'], timeout=APT_HELPER_TIMEOUT)
    except util.ProcessExecutionError as e:
        if e.exit_code == 100:
            stderr = str(e.stderr).lower()
            if re.search(r'401\s+unauthorized|httperror401', stderr):
                raise exceptions.UserFacingError(
                    'Invalid APT credentials provided for %s' % repo_url)
            elif re.search(r'connection timed out', stderr):
                raise exceptions.UserFacingError(
                    'Timeout trying to access APT repository at %s' % repo_url)
        raise exceptions.UserFacingError(
            'Unexpected APT error. See /var/log/ubuntu-advantage.log')
    except subprocess.TimeoutExpired:
        raise exceptions.UserFacingError(
            'Cannot validate credentials for APT repo.'
            ' Timeout after %d seconds trying to reach %s.' % (
                APT_HELPER_TIMEOUT, repo_path))
    finally:
        if os.path.exists('/tmp/uaclient-apt-test'):
            os.unlink('/tmp/uaclient-apt-test')


def run_apt_command(cmd, error_msg) -> str:
    """Run an apt command, retrying upon failure APT_RETRIES times.

    :return: stdout from successful run of the apt command.
    :raise UserFacingError: on issues running apt-cache policy.
    """
    try:
        out, _err = util.subp(cmd, capture=True, retry_sleeps=APT_RETRIES)
    except util.ProcessExecutionError as e:
        if 'Could not get lock /var/lib/dpkg/lock' in str(e.stderr):
            error_msg += ' Another process is running APT.'
        raise exceptions.UserFacingError(error_msg)
    return out


def add_auth_apt_repo(repo_filename: str, repo_url: str, credentials: str,
                      suites: 'List[str]', keyring_file: str = None) -> None:
    """Add an authenticated apt repo and credentials to the system.

    @raises: InvalidAPTCredentialsError when the token provided can't access
        the repo PPA.
    """
    try:
        username, password = credentials.split(':')
    except ValueError:  # Then we have a bearer token
        username = 'bearer'
        password = credentials
    series = util.get_platform_info()['series']
    if repo_url.endswith('/'):
        repo_url = repo_url[:-1]
    assert_valid_apt_credentials(repo_url, username, password)

    # Does this system have updates suite enabled?
    updates_enabled = False
    policy = run_apt_command(
        ['apt-cache', 'policy'], status.MESSAGE_APT_POLICY_FAILED)
    for line in policy.splitlines():
        # We only care about $suite-updates lines
        if 'a={}-updates'.format(series) not in line:
            continue
        # We only care about $suite-updates from the Ubuntu archive
        if 'o=Ubuntu,' not in line:
            continue
        updates_enabled = True
        break

    logging.info('Enabling authenticated repo: %s', repo_url)
    content = ''
    for suite in suites:
        if series not in suite:
            continue   # Only enable suites matching this current series
        maybe_comment = ''
        if '-updates' in suite and not updates_enabled:
            logging.debug(
                'Not enabling apt suite "%s" because "%s-updates" is not'
                ' enabled', suite, series)
            maybe_comment = '# '
        content += ('{maybe_comment}deb {url}/ubuntu {suite} main\n'
                    '# deb-src {url}/ubuntu {suite} main\n'.format(
                        maybe_comment=maybe_comment, url=repo_url, suite=suite)
                    )
    util.write_file(repo_filename, content)
    add_apt_auth_conf_entry(repo_url, username, password)
    if keyring_file:
        logging.debug('Copying %s to %s', keyring_file, APT_KEYS_DIR)
        shutil.copy(keyring_file, APT_KEYS_DIR)


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
    new_lines.append('')
    util.write_file(apt_auth_file, '\n'.join(new_lines), mode=0o600)


def remove_repo_from_apt_auth_file(repo_url):
    """Remove a repo from the shared apt auth file"""
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


def remove_auth_apt_repo(repo_filename: str, repo_url: str,
                         keyring_file: str = None) -> None:
    """Remove an authenticated apt repo and credentials to the system"""
    logging.info('Removing authenticated apt repo: %s', repo_url)
    util.del_file(repo_filename)
    if keyring_file:
        util.del_file(keyring_file)
    remove_repo_from_apt_auth_file(repo_url)


def restore_commented_apt_list_file(filename: str) -> None:
    """Uncomment commented deb lines in the given file."""
    file_content = util.load_file(filename)
    file_content = file_content.replace('# deb ', 'deb ')
    util.write_file(filename, file_content)


def add_ppa_pinning(apt_preference_file, repo_url, origin, priority):
    """Add an apt preferences file and pin for a PPA."""
    series = util.get_platform_info()['series']
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


def clean_apt_sources(*, _entitlements=None):
    """
    Clean apt sources list files written by uaclient

    :param _entitlements:
        The uaclient.entitlements module to use, defaults to
        uaclient.entitlements.  (This is only present for testing, because the
        import happens within the function to avoid circular imports.)
    """
    if _entitlements is None:
        from uaclient import entitlements as _entitlements

    for ent_cls in _entitlements.ENTITLEMENT_CLASSES:
        if not hasattr(ent_cls, 'repo_url'):
            continue
        repo_list_glob = ent_cls.repo_list_file_tmpl.format(
            name=ent_cls.name, series='*')

        # Remove list files
        for path in glob.glob(repo_list_glob):
            logging.info('Removing apt source file: %s', path)
            os.unlink(path)


def get_installed_packages() -> 'List[str]':
    out, _ = util.subp(['dpkg-query', '-W', '--showformat=${Package}\\n'])
    return out.splitlines()
