"""Tests related to uaclient.apt module."""

import glob
import mock
from textwrap import dedent

from uaclient.apt import (
    add_auth_apt_repo, add_ppa_pinning, find_apt_list_files,
    reconfigure_apt_sources, remove_apt_list_files, valid_apt_credentials)
from uaclient import config
from uaclient import util


class TestAddPPAPinning:

    @mock.patch('uaclient.util.get_platform_info')
    def test_write_apt_pin_file_to_apt_preferences(self, m_platform, tmpdir):
        """Write proper apt pin file to specified apt_preference_file."""
        m_platform.return_value = 'xenial'
        pref_file = tmpdir.join('preffile').strpath
        assert None is add_ppa_pinning(
            pref_file, repo_url='http://fakerepo', origin='MYORIG',
            priority=1003)
        expected_pref = dedent('''\
            Package: *
            Pin: release o=MYORIG, n=xenial
            Pin-Priority: 1003\n''')
        assert expected_pref == util.load_file(pref_file)


class TestFindAptListFilesFromRepoSeries:

    @mock.patch('uaclient.util.subp')
    def test_find_all_apt_list_files_from_apt_config_key(self, m_subp, tmpdir):
        """Find all matching apt list files from apt-config dir."""
        m_subp.return_value = ("key='%s'" % tmpdir.strpath, '')
        repo_url = 'http://c.com/fips-updates/'
        _protocol, repo_path = repo_url.split('://')
        prefix = repo_path.rstrip('/').replace('/', '_')
        paths = sorted([
            tmpdir.join(prefix + '_dists_nomatch').strpath,
            tmpdir.join(prefix + '_dists_xenial_InRelease').strpath,
            tmpdir.join(
                prefix + '_dists_xenial_main_binary-amd64_Packages').strpath])
        for path in paths:
            util.write_file(path, '')

        assert paths[1:] == find_apt_list_files(
            repo_url, 'xenial')


class TestRemoveAptListFiles:

    @mock.patch('uaclient.util.subp')
    def test_remove_all_apt_list_files_from_apt_config_key(
            self, m_subp, tmpdir):
        """Remove all matching apt list files from apt-config dir."""
        m_subp.return_value = ("key='%s'" % tmpdir.strpath, '')
        repo_url = 'http://c.com/fips-updates/'
        _protocol, repo_path = repo_url.split('://')
        prefix = repo_path.rstrip('/').replace('/', '_')
        nomatch_file = tmpdir.join(prefix + '_dists_nomatch').strpath
        paths = [
            nomatch_file,
            tmpdir.join(prefix + '_dists_xenial_InRelease').strpath,
            tmpdir.join(
                prefix + '_dists_xenial_main_binary-amd64_Packages').strpath]
        for path in paths:
            util.write_file(path, '')

        assert None is remove_apt_list_files(repo_url, 'xenial')
        assert [nomatch_file] == glob.glob('%s/*' % tmpdir.strpath)


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
        repo_file = tmpdir.join('repo.conf').strpath
        auth_file = tmpdir.join('auth.conf').strpath
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
        repo_file = tmpdir.join('repo.conf').strpath
        auth_file = tmpdir.join('auth.conf').strpath
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
        repo_file = tmpdir.join('repo.conf').strpath
        auth_file = tmpdir.join('auth.conf').strpath
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
        repo_file = tmpdir.join('repo.conf').strpath
        auth_file = tmpdir.join('auth.conf').strpath
        m_get_apt_auth_file.return_value = auth_file

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='SOMELONGTOKEN', fingerprint='APTKEY')

        expected_content = (
            '\n# This file is created by ubuntu-advantage-tools and will be'
            ' updated\n# by subsequent calls to ua attach|detach [entitlement]'
            '\nmachine fakerepo/ubuntu/ login bearer password SOMELONGTOKEN\n')
        assert expected_content == util.load_file(auth_file)


class TestReconfigureAptSources:

    @mock.patch('uaclient.apt.os.path.exists')
    @mock.patch('uaclient.apt.add_auth_apt_repo')
    @mock.patch('uaclient.util.subp')
    def test_no_apt_config_when_not_enabled_and_non_trusty(
            self, m_subp, m_add_apt, m_exists, tmpdir):
        """No apt config when no entitlements enabled and non trusty."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        m_exists.return_value = False
        m_subp.return_value = '500 http://us.archive.ubuntu.com/ubuntu ...', ''
        reconfigure_apt_sources(cfg, {'series': 'xenial', 'release': '16.04'})
        assert [] == m_add_apt.call_args_list
        assert [mock.call(['apt-cache', 'policy'])] == m_subp.call_args_list

    @mock.patch('uaclient.apt.os.path.exists')
    @mock.patch('uaclient.apt.add_auth_apt_repo')
    @mock.patch('uaclient.util.subp')
    def test_esm_apt_config_when_not_enabled_and_trusty(
            self, m_subp, m_add_apt, m_exists, tmpdir):
        """ESM apt config when no entitlements enabled and on trusty."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        m_exists.return_value = False
        m_subp.return_value = '500 http://us.archive.ubuntu.com/ubuntu ...', ''
        reconfigure_apt_sources(cfg, {'series': 'trusty', 'release': '14.04'})
        add_apt_call = mock.call(
            '/etc/apt/sources.list.d/ubuntu-esm-trusty.list',
            'https://esm.ubuntu.com')
        assert [mock.call(['apt-cache', 'policy'])] == m_subp.call_args_list
        assert [add_apt_call] == m_add_apt.call_args_list
