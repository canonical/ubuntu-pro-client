import itertools
import mock
import os.path

import pytest

from uaclient import config
from uaclient.entitlements.esm import ESMEntitlement


ESM_MACHINE_TOKEN = {
    'machineToken': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'esm'}]}}}


ESM_RESOURCE_ENTITLED = {
    'resourceToken': 'TOKEN',
    'entitlement': {
        'obligations': {
            'enableByDefault': True
        },
        'type': 'esm',
        'entitled': True,
        'directives': {
            'aptURL': 'http://ESM',
            'aptKey': 'APTKEY',
            'suites': ['xenial']
        },
        'affordances': {
            'series': []   # Will match all series
        }
    }
}

M_PATH = 'uaclient.entitlements.esm.ESMEntitlement.'
M_REPOPATH = 'uaclient.entitlements.repo.'


@pytest.fixture
def entitlement(tmpdir):
    """
    A pytest fixture to create a ESMEntitlement with some default config

    (Uses the tmpdir fixture for the underlying config cache.)
    """
    cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
    cfg.write_cache('machine-token', dict(ESM_MACHINE_TOKEN))
    cfg.write_cache('machine-access-esm', dict(ESM_RESOURCE_ENTITLED))
    return ESMEntitlement(cfg)


class TestESMEntitlementDisable:

    # Paramterize True/False for silent and force
    @pytest.mark.parametrize(
        'silent,force', itertools.product([False, True], repeat=2))
    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch(M_PATH + 'can_disable', return_value=False)
    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
            self, m_can_disable, m_platform_info, silent, force):
        """When can_disable is false disable returns false and noops."""
        entitlement = ESMEntitlement({})

        with mock.patch('uaclient.apt.remove_auth_apt_repo') as m_remove_apt:
            assert False is entitlement.disable(silent, force)
        assert [mock.call(silent, force)] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count

    @mock.patch('uaclient.apt.remove_repo_from_apt_auth_file')
    @mock.patch('uaclient.util.get_platform_info',
                return_value={'series': 'xenial'})
    @mock.patch(M_PATH + 'can_disable', return_value=True)
    def test_disable_removes_apt_config(
            self, m_can_disable, m_platform_info, m_rm_repo_from_auth,
            entitlement, tmpdir, caplog_text):
        """When can_disable, disable removes apt configuration when force."""

        original_exists = os.path.exists

        def fake_exists(path):
            if path == '/etc/apt/preferences.d/ubuntu-esm-xenial':
                return True
            return original_exists(path)

        with mock.patch('os.path.exists', side_effect=fake_exists):
            with mock.patch('uaclient.apt.os.unlink') as m_unlink:
                with mock.patch('uaclient.util.subp'):
                    assert entitlement.disable(True, True)

        assert 0 == m_unlink.call_count
        assert [mock.call(True, True)] == m_can_disable.call_args_list
        auth_call = mock.call('http://ESM')
        assert [auth_call] == m_rm_repo_from_auth.call_args_list
