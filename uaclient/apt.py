import logging
import os
import platform
import shutil

from uaclient import util

APT_AUTH_FILE = '/etc/apt/auth.conf'
APT_KEYS_DIR = '/etc/apt/trusted.gpg.d'
KEYRINGS_DIR = '/usr/share/keyrings'
APT_METHOD_HTTPS_FILE = '/usr/lib/apt/methods/https'
CA_CERTIFICATES_FILE = '/usr/sbin/update-ca-certificates'


def add_auth_apt_repo(repo_filename, repo_url, credentials, keyring_file=None,
                      fingerprint=None):
    """Add an authenticated apt repo and credentials to the system"""
    logging.info('Enabling authticated apt PPA: %s', repo_url)
    series = platform.dist()[2]
    content = (
        'deb {url}/ubuntu {series} main\n'
        '# deb-src {url}/ubuntu {series} main\n'.format(
            url=repo_url, series=series))
    util.write_file(repo_filename, content)
    # TODO(Confirm that machine-token or entitlement token provides format)
    # which is supported by /etc/apt/auth.conf
    login, password = credentials.split(':')
    if os.path.exists(APT_AUTH_FILE):
        auth_content = util.load_file(APT_AUTH_FILE)
    else:
        auth_content = ''
    _protocol, repo_path = repo_url.split('://')
    auth_content += (
        'machine {repo_path}/ubuntu/ login {login} password'
        ' {password}\n'.format(
            repo_path=repo_path, login=login, password=password))
    util.write_file(APT_AUTH_FILE, auth_content, mode=0o600)
    if keyring_file:
        logging.debug('Copying %s to %s', keyring_file, APT_KEYS_DIR)
        shutil.copy(keyring_file, APT_KEYS_DIR)
    elif fingerprint:
        logging.debug('Importing APT PPA key %s', fingerprint)
        util.subp(
            ['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
             '--receive-keys', fingerprint])


def remove_auth_apt_repo(repo_filename, repo_url, keyring_file=None,
                         fingerprint=None):
    """Remove an authenticated apt repo and credentials to the system"""
    logging.info('Removing authticated apt PPA: %s', repo_url)
    util.del_file(repo_filename)
    if keyring_file:
        util.del_file(keyring_file)
    elif fingerprint:
        util.subp(['apt-key', 'del', fingerprint])
    _protocol, repo_path = repo_url.split('://')
    apt_auth = util.load_file(APT_AUTH_FILE)
    auth_prefix = 'machine {repo_path}/ubuntu/ login'.format(
        repo_path=repo_path)
    content = '\n'.join([
        line for line in apt_auth.split('\n') if auth_prefix not in line])
    if not content:
        os.unlink(APT_AUTH_FILE)
    else:
        util.write_file(APT_AUTH_FILE, content, mode=0o600)


def add_repo_pinning(apt_preference_file, origin, priority):
    """Add an apt preferences file and pin for a PPA."""
    series = platform.dist()[2]
    content = (
        'Package: *\n'
        'Pin: release o={origin}, n={series}\n'
        'Pin-Priority: ${priority}\n'.format(
            origin=origin, priority=priority, series=series))
    util.write_file(apt_preference_file, content)
