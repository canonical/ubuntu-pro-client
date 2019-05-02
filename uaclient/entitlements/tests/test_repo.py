import copy
from textwrap import dedent

import mock
import pytest
from types import MappingProxyType

from uaclient import apt
from uaclient import config
from uaclient.entitlements.repo import RepoEntitlement
from uaclient import status
from uaclient import util


M_PATH = 'uaclient.entitlements.repo.'

REPO_MACHINE_TOKEN = {
    'machineToken': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'repotest', 'entitled': True}]}}}
REPO_RESOURCE_ENTITLED = {
    'resourceToken': 'TOKEN',
    'entitlement': {
        'obligations': {
            'enableByDefault': True
        },
        'type': 'repotest',
        'entitled': True,
        'directives': {
            'aptURL': 'http://REPOTEST',
            'aptKey': 'APTKEY',
            'suites': ['xenial']
        },
        'affordances': {
            'series': ['xenial']
        }
    }
}

PLATFORM_INFO_SUPPORTED = MappingProxyType({
    'arch': 'x86_64',
    'kernel': '4.4.0-00-generic',
    'series': 'xenial'
})


class RepoTestEntitlement(RepoEntitlement):
    """Subclass so we can test shared repo functionality"""
    name = 'repotest'
    title = 'Repo Test Class'
    description = 'Repo entitlement for testing'
    repo_url = 'http://example.com/ubuntu'
    repo_key_file = 'test.gpg'


@pytest.fixture
def entitlement(tmpdir):
    """
    A pytest fixture to create a RepoTestEntitlement with some default config

    (Uses the tmpdir fixture for the underlying config cache.)
    """
    cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
    cfg.write_cache('machine-token', dict(REPO_MACHINE_TOKEN))
    cfg.write_cache('machine-access-repotest', dict(REPO_RESOURCE_ENTITLED))
    return RepoTestEntitlement(cfg)


class TestOperationalStatus:

    @mock.patch(M_PATH + 'util.get_platform_info')
    def test_inapplicable_on_failed_check_affordances(
            self, m_platform_info, entitlement):
        """When check_affordances raises a failure, return INAPPLICABLE."""
        platform_unsupported = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        platform_unsupported['series'] = 'trusty'
        m_platform_info.return_value = platform_unsupported
        passed_affordances, details = entitlement.check_affordances()
        assert False is passed_affordances
        assert 'Repo Test Class is not available for Ubuntu trusty.' == details
        op_status, op_details = entitlement.operational_status()
        assert status.INAPPLICABLE == op_status

    @mock.patch(M_PATH + 'util.get_platform_info')
    def test_inapplicable_on_unentitled(
            self, m_platform_info, entitlement):
        """When unentitled raises a failure, return INAPPLICABLE."""
        no_entitlements = copy.deepcopy(dict(REPO_MACHINE_TOKEN))
        # delete all enttlements
        no_entitlements[
            'machineTokenInfo']['contractInfo']['resourceEntitlements'].pop()
        entitlement.cfg.write_cache('machine-token', no_entitlements)
        entitlement.cfg.delete_cache_key('machine-access-repotest')
        m_platform_info.return_value = dict(PLATFORM_INFO_SUPPORTED)
        passed_affordances, _details = entitlement.check_affordances()
        assert True is passed_affordances
        op_status, op_details = entitlement.operational_status()
        assert status.INAPPLICABLE == op_status
        assert 'Repo Test Class is not entitled' == op_details


class TestProcessContractDeltas:

    @pytest.mark.parametrize('orig_access', ({}, {'entitlement': {}}))
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_on_no_deltas(self, m_op_status, orig_access):
        """Return True when no deltas are available to process."""
        entitlement = RepoTestEntitlement()
        assert entitlement.process_contract_deltas(orig_access, {})
        assert [] == m_op_status.call_args_list

    @pytest.mark.parametrize('entitled', (False, util.DROPPED_KEY))
    @mock.patch.object(RepoTestEntitlement, 'disable')
    @mock.patch.object(RepoTestEntitlement, 'can_disable', return_value=True)
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_disable_when_delta_to_unentitled(
            self, m_op_status, m_can_disable, m_disable, entitlement,
            entitled):
        """Disable the service on contract transitions to unentitled."""
        m_op_status.return_value = status.ACTIVE, 'fake active'
        assert entitlement.process_contract_deltas(
            {'entitlement': {'entitled': True}},
            {'entitlement': {'entitled': entitled}})
        assert [mock.call()] == m_op_status.call_args_list
        assert [mock.call()] == m_disable.call_args_list

    @mock.patch.object(RepoTestEntitlement, 'remove_apt_config')
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_no_changes_when_service_inactive_and_not_enable_by_default(
            self, m_op_status, m_remove_apt_config, entitlement):
        """Noop when service is inactive and not enableByDefault."""
        m_op_status.return_value = status.INACTIVE, 'fake inactive'
        assert entitlement.process_contract_deltas(
            {'entitlement': {'entitled': True}},
            {'entitlement': {'obligations': {'enableByDefault': False}},
             'resourceToken': 'TOKEN'})
        assert [mock.call(), mock.call()] == m_op_status.call_args_list
        assert [] == m_remove_apt_config.call_args_list

    @mock.patch.object(RepoTestEntitlement, 'enable')
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_allow_enable_when_inactive_enable_by_default_and_resource_token(
            self, m_op_status, m_enable, entitlement):
        """Update apt when inactive, enableByDefault and allow_enable."""
        m_op_status.return_value = status.INACTIVE, 'fake inactive'
        assert entitlement.process_contract_deltas(
            {'entitlement': {'entitled': True}},
            {'entitlement': {'obligations': {'enableByDefault': True}},
             'resourceToken': 'TOKEN'},
            allow_enable=True)
        assert [mock.call()] == m_op_status.call_args_list
        assert [mock.call()] == m_enable.call_args_list

    @mock.patch.object(RepoTestEntitlement, 'enable')
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_not_allow_enable_logs_message_when_inactive_enable_by_default(
            self, m_op_status, m_enable, entitlement, caplog_text):
        """Log a message when inactive, enableByDefault and allow_enable."""
        m_op_status.return_value = status.INACTIVE, 'fake inactive'
        assert entitlement.process_contract_deltas(
            {'entitlement': {'entitled': True}},
            {'entitlement': {'obligations': {'enableByDefault': True}},
             'resourceToken': 'TOKEN'},
            allow_enable=False)
        assert [mock.call()] == m_op_status.call_args_list
        assert [] == m_enable.call_args_list
        expected_msg = status.MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
            name='repotest')
        assert expected_msg in caplog_text()

    @mock.patch(M_PATH + 'apt.remove_auth_apt_repo')
    @mock.patch.object(RepoTestEntitlement, 'setup_apt_config')
    @mock.patch.object(RepoTestEntitlement, 'remove_apt_config')
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_update_apt_config_when_active(
            self, m_op_status, m_remove_apt_config, m_setup_apt_config,
            m_remove_auth_apt_repo, entitlement):
        """Update_apt_config when service is active and not enableByDefault."""
        m_op_status.return_value = status.ACTIVE, 'fake active'
        assert entitlement.process_contract_deltas(
            {'entitlement': {'entitled': True}},
            {'entitlement': {'obligations': {'enableByDefault': False}},
             'resourceToken': 'TOKEN'})
        assert [mock.call(), mock.call()] == m_op_status.call_args_list
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_setup_apt_config.call_args_list
        assert [] == m_remove_auth_apt_repo.call_args_list

    @mock.patch(M_PATH + 'util.get_platform_info', return_value='trusty')
    @mock.patch(M_PATH + 'apt.remove_auth_apt_repo')
    @mock.patch.object(RepoTestEntitlement, 'setup_apt_config')
    @mock.patch.object(RepoTestEntitlement, 'remove_apt_config')
    @mock.patch.object(RepoTestEntitlement, 'operational_status')
    def test_remove_old_auth_apt_repo_when_active_and_apt_url_delta(
            self, m_op_status, m_remove_apt_config, m_setup_apt_config,
            m_remove_auth_apt_repo, m_platform_info, entitlement):
        """Remove old apt url when aptURL delta occurs on active service."""
        m_op_status.return_value = status.ACTIVE, 'fake active'
        assert entitlement.process_contract_deltas(
            {'entitlement': {
                'entitled': True, 'directives': {'aptURL': 'http://old'}}},
            {'entitlement': {'obligations': {'enableByDefault': False},
                             'directives': {'aptURL': 'http://new'}},
             'resourceToken': 'TOKEN'})
        assert [mock.call(), mock.call()] == m_op_status.call_args_list
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_setup_apt_config.call_args_list
        apt_auth_remove_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-repotest-trusty.list',
                      'http://old')]
        assert apt_auth_remove_calls == m_remove_auth_apt_repo.call_args_list
        apt_auth_remove_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-repotest-trusty.list',
                      'http://old')]
        assert apt_auth_remove_calls == m_remove_auth_apt_repo.call_args_list


class TestRepoEnable:

    @pytest.mark.parametrize('silent_if_inapplicable', (True, False, None))
    @mock.patch.object(RepoTestEntitlement, 'can_enable', return_value=False)
    def test_enable_passes_silent_if_inapplicable_through(
            self, m_can_enable, caplog_text, tmpdir, silent_if_inapplicable):
        """When can_enable returns False enable returns False."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        entitlement = RepoTestEntitlement(cfg)

        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs['silent_if_inapplicable'] = silent_if_inapplicable
        entitlement.enable(**kwargs)

        expected_call = mock.call(silent=bool(silent_if_inapplicable))
        assert [expected_call] == m_can_enable.call_args_list

    @pytest.mark.parametrize('packages', (['a'], [], None))
    @mock.patch(M_PATH + 'util.subp')
    @mock.patch(M_PATH + 'apt.add_auth_apt_repo')
    @mock.patch(M_PATH + 'os.path.exists', return_value=True)
    @mock.patch(M_PATH + 'util.get_platform_info')
    @mock.patch.object(RepoTestEntitlement, 'can_enable', return_value=True)
    def test_enable_calls_adds_apt_repo_and_calls_apt_update(
            self, m_can_enable, m_platform, m_exists, m_apt_add, m_subp,
            entitlement, capsys, caplog_text, tmpdir, packages):
        """On enable add authenticated apt repo and refresh package lists."""
        m_platform.return_value = 'xenial'  # from 'series' param

        expected_apt_calls = [mock.call(['apt-get', 'update'], capture=True)]
        expected_output = dedent("""\
        Updating package lists ...
        Repo Test Class enabled.
        """)
        if packages is not None:
            entitlement.packages = packages
            if len(packages) > 0:
                expected_apt_calls.append(
                    mock.call(['apt-get', 'install', '--assume-yes',
                              ' '.join(packages)], capture=True))
                expected_output = dedent("""\
                    Updating package lists ...
                    Installing Repo Test Class packages ...
                    Repo Test Class enabled.
                    """)
        entitlement.enable()

        expected_calls = [mock.call(apt.APT_METHOD_HTTPS_FILE),
                          mock.call(apt.CA_CERTIFICATES_FILE)]
        assert expected_calls in m_exists.call_args_list
        assert expected_apt_calls == m_subp.call_args_list
        assert [mock.call(
            '/etc/apt/sources.list.d/ubuntu-repotest-xenial.list',
            'http://REPOTEST', 'TOKEN', ['xenial'],
            '/usr/share/keyrings/test.gpg')] == m_apt_add.call_args_list
        stdout, _ = capsys.readouterr()
        assert expected_output == stdout
