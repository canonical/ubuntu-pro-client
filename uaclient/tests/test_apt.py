"""Tests related to uaclient.apt module."""

import copy
import glob
import mock
import os
import stat
from textwrap import dedent

import pytest

from uaclient.apt import (
    APT_AUTH_COMMENT, add_apt_auth_conf_entry, add_auth_apt_repo,
    add_ppa_pinning, find_apt_list_files, get_installed_packages,
    migrate_apt_sources, remove_apt_list_files, remove_auth_apt_repo,
    remove_repo_from_apt_auth_file, valid_apt_credentials)
from uaclient import config
from uaclient import util
from uaclient.entitlements.tests.test_cc import (
    CC_MACHINE_TOKEN, CC_RESOURCE_ENTITLED)


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
            repo_url='http://fakerepo', username='username', password='pass')
        expected_calls = [mock.call('/usr/lib/apt/apt-helper')]
        assert expected_calls == m_exists.call_args_list
        assert 0 == m_subp.call_count

    @mock.patch('uaclient.apt.os.unlink', return_value=True)
    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.os.path.exists', return_value=True)
    def test_valid_apt_credentials_returns_true_on_valid_creds(
            self, m_exists, m_subp, m_unlink):
        """Return true when apt-helper succeeds in authentication to repo."""

        # Success apt-helper response
        m_subp.return_value = 'Get:1 https://fakerepo\nFetched 285 B in 1s', ''

        assert True is valid_apt_credentials(
            repo_url='http://fakerepo', username='user', password='pwd')
        exists_calls = [mock.call('/usr/lib/apt/apt-helper'),
                        mock.call('/tmp/uaclient-apt-test')]
        assert exists_calls == m_exists.call_args_list
        apt_helper_call = mock.call(
            ['/usr/lib/apt/apt-helper', 'download-file',
             'http://user:pwd@fakerepo/ubuntu/pool/',
             '/tmp/uaclient-apt-test'], capture=False)
        assert [apt_helper_call] == m_subp.call_args_list
        assert [mock.call('/tmp/uaclient-apt-test')] == m_unlink.call_args_list

    @mock.patch('uaclient.apt.os.unlink', return_value=True)
    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.os.path.exists', return_value=True)
    def test_valid_apt_credentials_returns_false_on_invalid_creds(
            self, m_exists, m_subp, m_unlink):
        """Return false when apt-helper fails in authentication to repo."""

        # Failure apt-helper response
        m_subp.side_effect = util.ProcessExecutionError(
            cmd='apt-helper died', exit_code=100, stdout='Err:1...',
            stderr='E: Failed to fetch .... 401 Unauthorized')

        assert False is valid_apt_credentials(
            repo_url='http://fakerepo', username='user', password='pwd')
        exists_calls = [mock.call('/usr/lib/apt/apt-helper'),
                        mock.call('/tmp/uaclient-apt-test')]
        assert exists_calls == m_exists.call_args_list
        apt_helper_call = mock.call(
            ['/usr/lib/apt/apt-helper', 'download-file',
             'http://user:pwd@fakerepo/ubuntu/pool/',
             '/tmp/uaclient-apt-test'], capture=False)
        assert [apt_helper_call] == m_subp.call_args_list
        assert [mock.call('/tmp/uaclient-apt-test')] == m_unlink.call_args_list


class TestAddAuthAptRepo:

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
        m_subp.return_value = '500 esm.canonical.com...', ''  # apt policy

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='mycreds', suites=('xenial',))

        expected_content = (
            'deb http://fakerepo/ubuntu xenial main\n'
            '# deb-src http://fakerepo/ubuntu xenial main\n')
        assert expected_content == util.load_file(repo_file)

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    @mock.patch('uaclient.apt.valid_apt_credentials', return_value=True)
    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_add_auth_apt_repo_ignores_suites_not_matching_series(
            self, m_platform, m_valid_creds, m_get_apt_auth_file, m_subp,
            tmpdir):
        """Skip any apt suites that don't match the current series."""
        repo_file = tmpdir.join('repo.conf').strpath
        auth_file = tmpdir.join('auth.conf').strpath
        m_get_apt_auth_file.return_value = auth_file
        # apt policy with xenial-updates enabled
        m_subp.return_value = '500 esm.com xenial-updates/main', ''

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='mycreds',
            suites=('xenial-one', 'xenial-updates', 'trusty-gone'))

        expected_content = dedent("""\
            deb http://fakerepo/ubuntu xenial-one main
            # deb-src http://fakerepo/ubuntu xenial-one main
            deb http://fakerepo/ubuntu xenial-updates main
            # deb-src http://fakerepo/ubuntu xenial-updates main
        """)
        assert expected_content == util.load_file(repo_file)

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    @mock.patch('uaclient.apt.valid_apt_credentials', return_value=True)
    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_add_auth_apt_repo_ignores_updates_suites_on_non_update_machine(
            self, m_platform, m_valid_creds, m_get_apt_auth_file, m_subp,
            tmpdir):
        """Skip any apt suites that don't match the current series."""
        repo_file = tmpdir.join('repo.conf').strpath
        auth_file = tmpdir.join('auth.conf').strpath
        m_get_apt_auth_file.return_value = auth_file
        # apt policy without xenial-updates enabled
        m_subp.return_value = '500 esm.canonical.com xenial/main', ''

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='mycreds',
            suites=('xenial-one', 'xenial-updates', 'trusty-gone'))

        expected_content = dedent("""\
            deb http://fakerepo/ubuntu xenial-one main
            # deb-src http://fakerepo/ubuntu xenial-one main
        """)
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
        m_subp.return_value = '500 esm.canonical.com...', ''  # apt policy

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo',
            credentials='user:password',
            suites=('xenial',))

        expected_content = (
            'machine fakerepo/ login user password password%s\n' %
            APT_AUTH_COMMENT)
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
        m_subp.return_value = '500 esm.canonical.com...', ''  # apt policy

        add_auth_apt_repo(
            repo_filename=repo_file, repo_url='http://fakerepo/',
            credentials='SOMELONGTOKEN', suites=('xenia',))

        expected_content = (
            'machine fakerepo/ login bearer password SOMELONGTOKEN%s\n'
            % APT_AUTH_COMMENT)
        assert expected_content == util.load_file(auth_file)


class TestAddAptAuthConfEntry:

    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    def test_replaces_old_credentials_with_new(
            self, m_get_apt_auth_file, tmpdir):
        """Replace old credentials for this repo_url on the same line."""
        auth_file = tmpdir.join('auth.conf').strpath
        util.write_file(auth_file, dedent("""\
            machine fakerepo1/ login me password password1
            machine fakerepo/ login old password oldpassword
            machine fakerepo2/ login other password otherpass
        """))

        m_get_apt_auth_file.return_value = auth_file

        add_apt_auth_conf_entry(
            login='newlogin', password='newpass', repo_url='http://fakerepo/')

        expected_content = dedent("""\
            machine fakerepo1/ login me password password1
            machine fakerepo/ login newlogin password newpass%s
            machine fakerepo2/ login other password otherpass
        """ % APT_AUTH_COMMENT)
        assert expected_content == util.load_file(auth_file)

    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    def test_insert_repo_subroutes_before_existing_repo_basepath(
            self, m_get_apt_auth_file, tmpdir):
        """Insert new repo_url before first matching url base path."""
        auth_file = tmpdir.join('auth.conf').strpath
        util.write_file(auth_file, dedent("""\
            machine fakerepo1/ login me password password1
            machine fakerepo/ login old password oldpassword
            machine fakerepo2/ login other password otherpass
        """))

        m_get_apt_auth_file.return_value = auth_file

        add_apt_auth_conf_entry(
            login='new', password='newpass',
            repo_url='http://fakerepo/subroute')

        expected_content = dedent("""\
            machine fakerepo1/ login me password password1
            machine fakerepo/subroute/ login new password newpass%s
            machine fakerepo/ login old password oldpassword
            machine fakerepo2/ login other password otherpass
        """ % APT_AUTH_COMMENT)
        assert expected_content == util.load_file(auth_file)


class TestMigrateAptSources:

    @mock.patch('uaclient.apt.os.unlink')
    @mock.patch('uaclient.apt.add_auth_apt_repo')
    def test_no_apt_config_removed_when_upgraded_from_trusty_to_xenial(
            self, m_add_apt, m_unlink, tmpdir):
        """No apt config when connected but no entitlements enabled."""

        # Make CC resource access report not entitled
        cc_unentitled = copy.deepcopy(dict(CC_RESOURCE_ENTITLED))
        cc_unentitled['entitlement']['entitled'] = False

        cfg = config.UAConfig({'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', dict(CC_MACHINE_TOKEN))
        cfg.write_cache('machine-access-cc-eal', cc_unentitled)

        orig_exists = os.path.exists

        apt_files = ['/etc/apt/sources.list.d/ubuntu-cc-eal-trusty.list']

        def fake_apt_list_exists(path):
            if path in apt_files:
                return True
            return orig_exists(path)

        with mock.patch('uaclient.apt.os.path.exists') as m_exists:
            m_exists.side_effect = fake_apt_list_exists
            migrate_apt_sources(
                cfg=cfg,
                platform_info={'series': 'xenial', 'release': '16.04'})
        assert [] == m_add_apt.call_args_list
        # Only exists checks for for cfg.is_attached and can_enable
        assert [] == m_unlink.call_args_list  # remove nothing
        assert [] == m_exists.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch('uaclient.apt.os.unlink')
    @mock.patch('uaclient.apt.add_auth_apt_repo')
    def test_apt_config_migrated_when_enabled_upgraded_from_trusty_to_xenial(
            self, m_add_apt, m_unlink, m_platform_info, m_subp, tmpdir):
        """Apt config is migrated when connected and entitlement is enabled."""

        cfg = config.UAConfig({'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', dict(CC_MACHINE_TOKEN))
        cfg.write_cache('machine-access-cc-eal', dict(CC_RESOURCE_ENTITLED))

        orig_exists = os.path.exists

        glob_files = ['/etc/apt/sources.list.d/ubuntu-cc-eal-trusty.list',
                      '/etc/apt/sources.list.d/ubuntu-cc-eal-xenial.list']

        def fake_platform_info(key=None):
            platform_data = {
                'arch': 'x86_64', 'series': 'xenial', 'release': '16.04',
                'kernel': '4.15.0-40-generic'}
            if key:
                return platform_data[key]
            return platform_data

        def fake_apt_list_exists(path):
            if path in glob_files:
                return True
            return orig_exists(path)

        def fake_glob(regex):
            if regex == '/etc/apt/sources.list.d/ubuntu-cc-eal-*.list':
                return glob_files
            return []

        repo_url = CC_RESOURCE_ENTITLED['entitlement']['directives']['aptURL']
        m_platform_info.side_effect = fake_platform_info
        m_subp.return_value = '500 %s' % repo_url, ''
        with mock.patch('uaclient.apt.glob.glob') as m_glob:
            with mock.patch('uaclient.apt.os.path.exists') as m_exists:
                m_glob.side_effect = fake_glob
                m_exists.side_effect = fake_apt_list_exists
                assert None is migrate_apt_sources(cfg=cfg)
        assert [] == m_add_apt.call_args_list
        # Only exists checks for for cfg.is_attached and can_enable
        unlink_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-cc-eal-trusty.list')]
        assert unlink_calls == m_unlink.call_args_list  # remove nothing
        assert [] == m_exists.call_args_list

    @mock.patch('uaclient.apt.os.unlink')
    @mock.patch('uaclient.apt.add_auth_apt_repo')
    def test_noop_apt_config_when_not_attached(
            self, m_add_apt, m_unlink, tmpdir):
        """Perform not apt config changes when not attached."""
        cfg = config.UAConfig({'data_dir': tmpdir.strpath})
        assert False is cfg.is_attached
        with mock.patch('uaclient.apt.os.path.exists') as m_exists:
            m_exists.return_value = False
            assert None is migrate_apt_sources(
                cfg=cfg,
                platform_info={'series': 'trusty', 'release': '14.04'})
        assert [] == m_add_apt.call_args_list
        assert [] == m_unlink.call_args_list


@pytest.fixture(params=(mock.sentinel.default, None, 'some_string'))
def remove_auth_apt_repo_kwargs(request):
    """
    Parameterized fixture to generate all permutations of kwargs we need

    Note that this tests three states for keyring_file: using the default,
    explicitly passing None and explicitly passing a string.
    """
    keyring_file = request.param
    kwargs = {}
    if keyring_file != mock.sentinel.default:
        kwargs['keyring_file'] = keyring_file
    return kwargs


class TestRemoveAuthAptRepo:

    @mock.patch('uaclient.apt.util.subp')
    @mock.patch('uaclient.apt.remove_repo_from_apt_auth_file')
    @mock.patch('uaclient.apt.util.del_file')
    def test_repo_file_deleted(
            self, m_del_file, _mock, __mock, remove_auth_apt_repo_kwargs):
        """Ensure that repo_filename is deleted, regardless of other params."""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs)

        assert mock.call(repo_filename) in m_del_file.call_args_list

    @mock.patch('uaclient.apt.util.subp')
    @mock.patch('uaclient.apt.util.del_file')
    @mock.patch('uaclient.apt.remove_repo_from_apt_auth_file')
    def test_remove_from_auth_file_called(
            self, m_remove_repo, _mock, __mock, remove_auth_apt_repo_kwargs):
        """Ensure that remove_repo_from_apt_auth_file is called."""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs)

        assert mock.call(repo_url) in m_remove_repo.call_args_list

    @mock.patch('uaclient.apt.util.subp')
    @mock.patch('uaclient.apt.remove_repo_from_apt_auth_file')
    @mock.patch('uaclient.apt.util.del_file')
    def test_keyring_file_deleted_if_given(
            self, m_del_file, _mock, __mock, remove_auth_apt_repo_kwargs):
        """We should always delete the keyring file if it is given"""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs)

        keyring_file = remove_auth_apt_repo_kwargs.get('keyring_file')
        if keyring_file:
            assert mock.call(keyring_file) in m_del_file.call_args_list
        else:
            assert mock.call(keyring_file) not in m_del_file.call_args_list


class TestRemoveRepoFromAptAuthFile:

    @mock.patch('uaclient.apt.os.unlink')
    @mock.patch('uaclient.apt.util.write_file')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    def test_auth_file_doesnt_exist_means_we_dont_remove_or_write_it(
            self, m_get_apt_auth_file, m_write_file, m_unlink, tmpdir):
        """If the auth file doesn't exist, we shouldn't do anything to it"""
        m_get_apt_auth_file.return_value = tmpdir.join('nonexistent').strpath

        remove_repo_from_apt_auth_file('http://url')

        assert 0 == m_write_file.call_count
        assert 0 == m_unlink.call_count

    @pytest.mark.parametrize('trailing_slash', (True, False))
    @pytest.mark.parametrize('repo_url,auth_file_content', (
        ('http://url1', b''),
        ('http://url2', b'machine url2/ login trailing content'),
        ('http://url3', b'machine url3/ login'),
        ('http://url4', b'leading content machine url4/ login'),
        ('http://url4',
         b'leading content machine url4/ login trailing content'),
    ))
    @mock.patch('uaclient.apt.os.unlink')
    @mock.patch('uaclient.apt.util.write_file')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    def test_file_removal(self, m_get_apt_auth_file, m_write_file, m_unlink,
                          tmpdir, trailing_slash, repo_url, auth_file_content):
        """Check that auth file is rm'd if empty or contains just our line"""
        auth_file = tmpdir.join('auth_file')
        auth_file.write(auth_file_content, 'wb')
        m_get_apt_auth_file.return_value = auth_file.strpath

        remove_repo_from_apt_auth_file(
            repo_url + ('' if not trailing_slash else '/'))

        assert 0 == m_write_file.call_count
        assert [mock.call(auth_file.strpath)] == m_unlink.call_args_list

    @pytest.mark.parametrize('trailing_slash', (True, False))
    @pytest.mark.parametrize('repo_url,before_content,after_content', (
        ('http://url1', b'should not be changed', b'should not be changed'),
        ('http://url1', b'line before\nmachine url1/ login', b'line before'),
        ('http://url1', b'machine url1/ login\nline after', b'line after'),
        ('http://url1', b'line before\nmachine url1/ login\nline after',
         b'line before\nline after'),
        ('http://url1', b'unicode \xe2\x98\x83\nmachine url1/ login',
         b'unicode \xe2\x98\x83'),
    ))
    @mock.patch('uaclient.apt.os.unlink')
    @mock.patch('uaclient.apt.get_apt_auth_file_from_apt_config')
    def test_file_rewrite(self, m_get_apt_auth_file, m_unlink, tmpdir,
                          repo_url, before_content, after_content,
                          trailing_slash):
        """Check that auth file is rewritten to only exclude our line"""
        auth_file = tmpdir.join('auth_file')
        auth_file.write(before_content, 'wb')
        m_get_apt_auth_file.return_value = auth_file.strpath

        remove_repo_from_apt_auth_file(
            repo_url + ('' if not trailing_slash else '/'))

        assert 0 == m_unlink.call_count
        assert 0o600 == stat.S_IMODE(os.lstat(auth_file.strpath).st_mode)
        assert after_content == auth_file.read('rb')


class TestGetInstalledPackages:

    @mock.patch('uaclient.apt.util.subp', return_value=('', ''))
    def test_correct_command_called(self, m_subp):
        get_installed_packages()

        expected_call = mock.call(
            ['dpkg-query', '-W', '--showformat="${Package}\\n"'])
        assert [expected_call] == m_subp.call_args_list

    @mock.patch('uaclient.apt.util.subp', return_value=('', ''))
    def test_empty_output_means_empty_list(self, m_subp):
        assert [] == get_installed_packages()

    @mock.patch('uaclient.apt.util.subp', return_value=('a\nb\n', ''))
    def test_lines_are_split(self, m_subp):
        assert ['a', 'b'] == get_installed_packages()

    @mock.patch('uaclient.apt.util.subp', return_value=('a\nb', ''))
    def test_assert_missing_eof_newline_works(self, m_subp):
        assert ['a', 'b'] == get_installed_packages()
