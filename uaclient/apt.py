import os
import platform
import shutil

from uaclient import util

APT_AUTH_FILE = '/etc/apt/auth.conf'
APT_KEYS_DIR = '/etc/apt/trusted.gpg.d'
KEYRINGS_DIR = '/usr/share/keyrings'
APT_METHOD_HTTPS_FILE = '/usr/lib/apt/methods/https'
CA_CERTIFICATES_FILE = '/usr/sbin/update-ca-certificates'


def add_auth_apt_repo(repo_filename, repo_url, credentials, keyring_file):
    """Add an authenticated apt repo and credentials to the system"""
    series = platform.dist()[2]
    content = (
        'deb {url}/ubuntu {series} main\n'
        '# deb-src {url}/ubuntu {series} main\n'.format(
            url=repo_url, series=series))
    # TODO Confirm that machine-token or entitlement token provides format
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
    util.write_file(APT_AUTH_FILE, content, mode=0o600)
    shutil.copy(keyring_file, APT_KEYS_DIR)


def remove_auth_apt_repo(repo_filename, repo_url, keyring_file):
    """Remove an authenticated apt repo and credentials to the system"""
    util.del_file(repo_filename)
    util.del_file(keyring_file)
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
