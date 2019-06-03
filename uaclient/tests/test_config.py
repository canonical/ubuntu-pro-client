import copy
import itertools
import json
import os
import stat

import mock
import pytest

from uaclient import entitlements, status
from uaclient.config import DataPath, PRIVATE_SUBDIR, UAConfig
from uaclient.entitlements import ENTITLEMENT_CLASSES
from uaclient.testing.fakes import FakeConfig


KNOWN_DATA_PATHS = (('bound-macaroon', 'bound-macaroon'),
                    ('accounts', 'accounts.json'))
M_PATH = 'uaclient.entitlements.'


class TestAccounts:

    def test_accounts_returns_empty_list_when_no_cached_account_value(
            self, tmpdir):
        """Config.accounts property returns an empty list when no cache."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})

        assert [] == cfg.accounts

    def test_accounts_extracts_accounts_key_from_account_read_cache(
            self, tmpdir):
        """Config.accounts property extracts the accounts key from cache."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        cfg.write_cache('accounts', {'accounts': ['acct1', 'acct2']})

        assert ['acct1', 'acct2'] == cfg.accounts

    def test_accounts_extracts_accounts_key_from_machine_token_cache(
            self, tmpdir):
        """Use machine_token cached accountInfo when no accounts cache."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        accountInfo = {'id': '1', 'name': 'accountname'}

        cfg.write_cache('machine-token',
                        {'machineTokenInfo': {'accountInfo': accountInfo}})

        assert [accountInfo] == cfg.accounts

    def test_accounts_logs_warning_when_non_dictionary_cache_content(
            self, caplog_text, tmpdir):
        """Config.accounts warns and returns empty list on non-dict cache."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        cfg.write_cache('accounts', 'non-dict-value')

        assert [] == cfg.accounts
        expected_warning = (
            "WARNING  Unexpected type <class 'str'> in cache %s" % (
                tmpdir.join(PRIVATE_SUBDIR, 'accounts.json')))
        assert expected_warning in caplog_text()

    def test_accounts_logs_warning_when_missing_accounts_key_in_cache(
            self, caplog_text, tmpdir):
        """Config.accounts warns when missing 'accounts' key in cache"""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        cfg.write_cache('accounts', {'non-accounts': 'somethingelse'})

        assert [] == cfg.accounts
        expected_warning = (
            "WARNING  Missing 'accounts' key in cache %s" %
            tmpdir.join(PRIVATE_SUBDIR, 'accounts.json'))
        assert expected_warning in caplog_text()

    def test_accounts_logs_warning_when_non_list_accounts_cache_content(
            self, caplog_text, tmpdir):
        """Config.accounts warns on non-list accounts key."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        cfg.write_cache('accounts', {'accounts': 'non-list-value'})

        assert [] == cfg.accounts
        expected_warning = (
            "WARNING  Unexpected 'accounts' type <class 'str'> in cache %s" % (
                tmpdir.join(PRIVATE_SUBDIR, 'accounts.json')))
        assert expected_warning in caplog_text()


class TestDataPath:

    def test_data_path_returns_data_dir_path_without_key(self):
        """The data_path method returns the data_dir when key is absent."""
        cfg = UAConfig({'data_dir': '/my/dir'})
        assert '/my/dir/%s' % PRIVATE_SUBDIR == cfg.data_path()

    @pytest.mark.parametrize('key,path_basename', KNOWN_DATA_PATHS)
    def test_data_path_returns_file_path_with_defined_data_paths(
            self, key, path_basename):
        """When key is defined in Config.data_paths return data_path value."""
        cfg = UAConfig({'data_dir': '/my/dir'})
        private_path = '/my/dir/%s/%s' % (PRIVATE_SUBDIR, path_basename)
        assert private_path == cfg.data_path(key=key)

    @pytest.mark.parametrize('key,path_basename', (
        ('notHere', 'notHere'), ('anything', 'anything')))
    def test_data_path_returns_file_path_with_undefined_data_paths(
            self, key, path_basename):
        """When key is not in Config.data_paths the key is used to data_dir"""
        cfg = UAConfig({'data_dir': '/my/d'})
        assert '/my/d/%s/%s' % (PRIVATE_SUBDIR, key) == cfg.data_path(key=key)

    def test_data_path_returns_public_path_for_public_datapath(self):
        cfg = UAConfig({'data_dir': '/my/d'})
        cfg.data_paths['test_path'] = DataPath('test_path', False)
        assert '/my/d/test_path' == cfg.data_path('test_path')


class TestWriteCache:

    @pytest.mark.parametrize('key,content', (
        ('unknownkey', 'content1'), ('another-one', 'content2')))
    def test_write_cache_write_key_name_in_data_dir_when_data_path_absent(
            self, tmpdir, key, content):
        """When key is not in data_paths, write content to data_dir/key."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        expected_path = tmpdir.join(PRIVATE_SUBDIR, key)

        assert not expected_path.check(), (
            'Found unexpected file %s' % expected_path)
        assert None is cfg.write_cache(key, content)
        assert expected_path.check(), (
            'Missing expected file %s' % expected_path)
        assert content == cfg.read_cache(key)

    def test_write_cache_creates_dir_when_data_dir_does_not_exist(
            self, tmpdir):
        """When data_dir doesn't exist, create it."""
        tmp_subdir = tmpdir.join('does/not/exist')
        cfg = UAConfig({'data_dir': tmp_subdir.strpath})

        assert False is os.path.isdir(tmp_subdir.strpath), (
            'Found unexpected directory %s' % tmp_subdir)
        assert None is cfg.write_cache('somekey', 'someval')
        assert True is os.path.isdir(tmp_subdir.strpath), (
            'Missing expected directory %s' % tmp_subdir)
        assert 'someval' == cfg.read_cache('somekey')

    @pytest.mark.parametrize('key,value', (
        ('dictkey', {'1': 'v1'}), ('listkey', [1, 2, 3])))
    def test_write_cache_writes_json_string_when_content_not_a_string(
            self, tmpdir, key, value):
        """When content is not a string, write a json string."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})

        expected_json_content = json.dumps(value)
        assert None is cfg.write_cache(key, value)
        with open(tmpdir.join(PRIVATE_SUBDIR, key).strpath, 'r') as stream:
            assert expected_json_content == stream.read()
        assert value == cfg.read_cache(key)

    @pytest.mark.parametrize('datapath,mode', (
        (DataPath('path', False), 0o644),
        (DataPath('path', True), 0o600),
    ))
    def test_permissions(self, tmpdir, datapath, mode):
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        cfg.data_paths = {'path': datapath}
        cfg.write_cache('path', '')
        assert mode == stat.S_IMODE(
            os.lstat(cfg.data_path('path')).st_mode)


class TestReadCache:

    @pytest.mark.parametrize('key,path_basename', KNOWN_DATA_PATHS)
    def test_read_cache_returns_none_when_data_path_absent(
            self, tmpdir, key, path_basename):
        """Return None when the specified key data_path is not cached."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        assert None is cfg.read_cache(key)
        assert not tmpdir.join(path_basename).check()

    @pytest.mark.parametrize('key,path_basename', KNOWN_DATA_PATHS)
    def test_read_cache_returns_content_when_data_path_present(
            self, tmpdir, key, path_basename):
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, path_basename)
        with open(data_path.strpath, 'w') as f:
            f.write('content%s' % key)

        assert 'content%s' % key == cfg.read_cache(key)

    @pytest.mark.parametrize('key,path_basename', KNOWN_DATA_PATHS)
    def test_read_cache_returns_stuctured_content_when_json_data_path_present(
            self, tmpdir, key, path_basename):
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, path_basename)
        expected = {key: 'content%s' % key}
        with open(data_path.strpath, 'w') as f:
            f.write(json.dumps(expected))

        assert expected == cfg.read_cache(key)


class TestDeleteCache:

    @pytest.mark.parametrize(
        'property_name,data_path_name,expected_null_value', (
            ('machine_token', 'machine-token', None),
        ))
    def test_delete_cache_properly_clears_all_caches_simple(
            self, tmpdir, property_name, data_path_name, expected_null_value):
        """
        Ensure that delete_cache clears the cache for simple attributes

        (Simple in this context means those that are simply read from the
        filesystem and returned.)
        """
        property_value = 'our-value'
        cfg = UAConfig({'data_dir': tmpdir.strpath})

        data_path = cfg.data_path(data_path_name)
        os.makedirs(os.path.dirname(data_path))
        with open(data_path, 'w') as f:
            f.write(property_value)

        before_prop_value = getattr(cfg, property_name)
        assert before_prop_value == property_value

        cfg.delete_cache()

        after_prop_value = getattr(cfg, property_name)
        assert expected_null_value == after_prop_value

    def test_delete_cache_unsets_entitlements(self, tmpdir):
        """The delete_cache unsets any cached entitlements content."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        token = {
            'machineTokenInfo': {'contractInfo': {'resourceEntitlements': [{
                'type': 'entitlement1', 'entitled': True}]}}}
        cfg.write_cache('machine-token', token)
        previous_entitlements = {
            'entitlement1': {'entitlement':
                                {'type': 'entitlement1', 'entitled': True}}}
        assert previous_entitlements == cfg.entitlements
        cfg.delete_cache()
        assert {} == cfg.entitlements

    def test_delete_cache_removes_any_cached_data_path_files(self, tmpdir):
        """Any cached files defined in cfg.data_paths will be removed."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        # Create half of the cached files, but not all
        odd_keys = list(cfg.data_paths.keys())[::2]
        for odd_key in odd_keys:
            cfg.write_cache(odd_key, odd_key)

        present_files = list(itertools.chain(
            *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]))
        assert len(odd_keys) == len(present_files)
        cfg.delete_cache()
        dirty_files = list(itertools.chain(
            *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]))
        assert 0 == len(dirty_files), '%d files not deleted' % len(dirty_files)

    def test_delete_cache_ignores_files_not_defined_in_data_paths(
            self, tmpdir):
        """Any files in data_dir undefined in cfg.data_paths will remain."""
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        t_file = tmpdir.join(PRIVATE_SUBDIR, 'otherfile')
        os.makedirs(os.path.dirname(t_file.strpath))
        with open(t_file.strpath, 'w') as f:
            f.write('content')
        assert [os.path.basename(t_file.strpath)] == os.listdir(
            tmpdir.join(PRIVATE_SUBDIR).strpath)
        cfg.delete_cache()
        assert [os.path.basename(t_file.strpath)] == os.listdir(
            tmpdir.join(PRIVATE_SUBDIR).strpath)


class TestStatus:

    @mock.patch('uaclient.config.os.getuid', return_value=0)
    def test_root_unattached(self, _m_getuid):
        """Test we get the correct status dict when unattached"""
        cfg = FakeConfig({})
        expected = {
            'attached': False,
            'expires': status.INAPPLICABLE,
            'services': [],
            'techSupportLevel': status.INAPPLICABLE,
        }
        assert expected == cfg.status()

    @mock.patch('uaclient.config.os.getuid', return_value=0)
    def test_root_attached(self, _m_getuid):
        """Test we get the correct status dict when attached with basic conf"""
        cfg = FakeConfig.for_attached_machine()
        expected_services = [{'entitled': status.NONE,
                              'name': cls.name,
                              'status': status.INAPPLICABLE,
                              'statusDetails': mock.ANY}
                             for cls in entitlements.ENTITLEMENT_CLASSES]
        expected = {
            'account': 'test_account',
            'attached': True,
            'expires': status.INAPPLICABLE,
            'services': expected_services,
            'subscription': 'test_contract',
            'techSupportLevel': status.INAPPLICABLE,
        }
        assert expected == cfg.status()
        # cfg.status() idempotent
        assert expected == cfg.status()

    @mock.patch('uaclient.config.os.getuid')
    def test_nonroot_without_cache_is_same_as_unattached_root(self, m_getuid):
        m_getuid.return_value = 1000
        cfg = FakeConfig()

        nonroot_status = cfg.status()

        m_getuid.return_value = 0
        root_unattached_status = cfg.status()

        assert root_unattached_status == nonroot_status

    @mock.patch('uaclient.config.os.getuid')
    def test_root_followed_by_nonroot(self, m_getuid, tmpdir):
        """Ensure that non-root run after root returns data"""
        cfg = UAConfig({'data_dir': tmpdir.strpath})

        # Run as root
        m_getuid.return_value = 0
        before = copy.deepcopy(cfg.status())

        # Replicate an attach by modifying the underlying config and confirm
        # that we see different status
        other_cfg = FakeConfig.for_attached_machine()
        cfg.write_cache('accounts', {'accounts': other_cfg.accounts})
        cfg.write_cache('machine-token', other_cfg.machine_token)
        assert cfg._status() != before

        # Run as regular user and confirm that we see the result from
        # last time we called .status()
        m_getuid.return_value = 1000
        after = cfg.status()

        assert before == after

    @mock.patch('uaclient.config.os.getuid', return_value=0)
    def test_cache_file_is_written_world_readable(self, _m_getuid, tmpdir):
        cfg = UAConfig({'data_dir': tmpdir.strpath})
        cfg.status()

        assert 0o644 == stat.S_IMODE(
            os.lstat(cfg.data_path('status-cache')).st_mode)

    @pytest.mark.parametrize('entitlements', (
        [],
        [{'type': 'support', 'entitled': True,
          'affordances': {'supportLevel': 'anything'}}]))
    @mock.patch('uaclient.config.os.getuid', return_value=0)
    @mock.patch(M_PATH + 'livepatch.LivepatchEntitlement.user_facing_status')
    @mock.patch(M_PATH + 'repo.RepoEntitlement.user_facing_status')
    def test_attached_reports_contract_and_service_status(
            self, m_repo_uf_status, m_livepatch_uf_status, _m_getuid, tmpdir,
            entitlements):
        """When attached, return contract and service user-facing status."""
        m_repo_uf_status.return_value = (
            status.UserFacingStatus.INAPPLICABLE, 'repo details')
        m_livepatch_uf_status.return_value = (
            status.UserFacingStatus.ACTIVE, 'livepatch details')
        token = {
            'machineTokenInfo': {
                'accountInfo': {'id': '1', 'name': 'accountname'},
                'contractInfo': {'name': 'contractname',
                                 'resourceEntitlements': entitlements}}}
        cfg = FakeConfig.for_attached_machine(
            account_name='accountname', machine_token=token)
        if not entitlements:
            support_level = status.INAPPLICABLE
        else:
            support_level = entitlements[0]['affordances']['supportLevel']
        expected = {
            'attached': True, 'account': 'accountname',
            'expires': status.INAPPLICABLE, 'subscription': 'contractname',
            'techSupportLevel': support_level, 'services': []}
        for cls in ENTITLEMENT_CLASSES:
            if cls.name == 'livepatch':
                expected_status = status.UserFacingStatus.ACTIVE.value
                details = 'livepatch details'
            else:
                expected_status = status.UserFacingStatus.INAPPLICABLE.value
                details = 'repo details'
            expected['services'].append(
                {'name': cls.name, 'entitled': status.NONE,
                 'status': expected_status, 'statusDetails': details})
        assert expected == cfg.status()
        assert len(ENTITLEMENT_CLASSES) - 1 == m_repo_uf_status.call_count
        assert 1 == m_livepatch_uf_status.call_count
