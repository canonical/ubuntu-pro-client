"""Tests related to uaclient.apt module."""

import mock

from uaclient.apt import add_auth_apt_repo, valid_apt_credentials
from uaclient import util


class TestValidAptCredentials:

    @mock.patch('uaclient.util.subp')
    @mock.patch('os.path.exists', return_value=False)
    def test_valid_apt_credentials_true_when_missing_apt_helper(
            self, m_exists, m_subp):
        """When apt-helper tool is absent return True without validation."""
        assert True is valid_apt_credentials(
            repo_url='http://fakerepo', series='xenial', credentials='mycreds')
        expected_calls = [mock.call('/usr/lib/apt/apt-helper')]
        assert expected_calls == m_exists.call_args_list
        assert 0 == m_subp.call_count


class TestAddAuthAptRepo:

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    @mock.patch('uaclient.apt.valid_apt_credentials', return_value=True)
    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_add_auth_apt_repo_adds_apt_fingerprint(
            self, m_platform, m_valid_creds, m_get_apt_auth_file, m_subp,
            tmpdir):
        """Call apt-key to add the specified fingerprint."""
        repo_file = tmpdir.join('repo.conf')
        auth_file = tmpdir.join('auth.conf')
        m_get_apt_auth_file.return_value = auth_file

        add_auth_apt_repo(repo_filename=repo_file, repo_url='http://fakerepo',
                          credentials='mycreds', fingerprint='APTKEY')

        apt_cmds = [
            mock.call(['apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com',
                       '--recv-keys', 'APTKEY'], capture=True)]
        assert apt_cmds == m_subp.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    @mock.patch('uaclient.apt.valid_apt_credentials', return_value=True)
    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_add_auth_apt_repo_writes_sources_file(
            self, m_platform, m_valid_creds, m_get_apt_auth_file, m_subp,
            tmpdir):
        """Write a properly configured sources file to repo_filename."""
        repo_file = tmpdir.join('repo.conf')
        auth_file = tmpdir.join('auth.conf')
        m_get_apt_auth_file.return_value = auth_file

        add_auth_apt_repo(repo_filename=repo_file, repo_url='http://fakerepo',
                          credentials='mycreds', fingerprint='APTKEY')

        expected_content = (
            'deb http://fakerepo/ubuntu xenial main\n'
            '# deb-src http://fakerepo/ubuntu xenial main\n')
        assert expected_content == util.load_file(repo_file)

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    @mock.patch('uaclient.apt.valid_apt_credentials', return_value=True)
    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_add_auth_apt_repo_writes_username_password_to_auth_file(
            self, m_platform, m_valid_creds, m_get_apt_auth_file, m_subp,
            tmpdir):
        """Write apt authentication file when credentials are user:pwd."""
        repo_file = tmpdir.join('repo.conf')
        auth_file = tmpdir.join('auth.conf')
        m_get_apt_auth_file.return_value = auth_file

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='user:password', fingerprint='APTKEY')

        expected_content = (
            '\n# This file is created by ubuntu-advantage-tools and will be'
            ' updated\n# by subsequent calls to ua attach|detach [entitlement]'
            '\nmachine fakerepo/ubuntu/ login user password password\n')
        assert expected_content == util.load_file(auth_file)

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    @mock.patch('uaclient.apt.valid_apt_credentials', return_value=True)
    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_add_auth_apt_repo_writes_bearer_resource_token_to_auth_file(
            self, m_platform, m_valid_creds, m_get_apt_auth_file, m_subp,
            tmpdir):
        """Write apt authentication file when credentials are bearer token."""
        repo_file = tmpdir.join('repo.conf')
        auth_file = tmpdir.join('auth.conf')
        m_get_apt_auth_file.return_value = auth_file

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='SOMELONGTOKEN', fingerprint='APTKEY')

        expected_content = (
            '\n# This file is created by ubuntu-advantage-tools and will be'
            ' updated\n# by subsequent calls to ua attach|detach [entitlement]'
            '\nmachine fakerepo/ubuntu/ login bearer password SOMELONGTOKEN\n')
        assert expected_content == util.load_file(auth_file)
