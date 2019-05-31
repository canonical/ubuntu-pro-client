import contextlib
import itertools
import mock
import os.path

import pytest

from uaclient import apt
from uaclient import config
from uaclient.entitlements.esm import ESMEntitlement
from uaclient.entitlements.repo import APT_RETRIES


ESM_MACHINE_TOKEN = {
    'machineToken': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'esm', 'entitled': True}]}}}


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
            'suites': ['trusty']
        },
        'affordances': {
            'series': []   # Will match all series
        }
    }
}

M_PATH = 'uaclient.entitlements.esm.ESMEntitlement.'
M_REPOPATH = 'uaclient.entitlements.repo.'
M_GETPLATFORM = M_REPOPATH + 'util.get_platform_info'


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


class TestESMEntitlementEnable:

    def test_enable_configures_apt_sources_and_auth_files(self, entitlement):
        """When entitled, configure apt repo auth token, pinning and url."""
        patched_packages = ['a', 'b']
        original_exists = os.path.exists

        def fake_exists(path):
            if path == '/etc/apt/preferences.d/ubuntu-esm-trusty':
                return True
            if path in (apt.APT_METHOD_HTTPS_FILE, apt.CA_CERTIFICATES_FILE):
                return True
            return original_exists(path)

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch('uaclient.apt.add_auth_apt_repo'))
            m_add_pinning = stack.enter_context(
                mock.patch('uaclient.apt.add_ppa_pinning'))
            m_subp = stack.enter_context(mock.patch('uaclient.util.subp'))
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, 'can_enable'))
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value={'series': 'trusty'}))
            stack.enter_context(
                mock.patch(M_REPOPATH + 'os.path.exists',
                           side_effect=fake_exists))
            m_unlink = stack.enter_context(
                mock.patch('uaclient.apt.os.unlink'))
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), 'packages', m_packages))

            m_can_enable.return_value = True

            assert True is entitlement.enable()

        add_apt_calls = [
            mock.call(
                '/etc/apt/sources.list.d/ubuntu-{}-trusty.list'.format(
                    entitlement.name),
                'http://ESM', 'TOKEN', ['trusty'],
                '/usr/share/keyrings/ubuntu-{}-v2-keyring.gpg'.format(
                    entitlement.name))]
        install_cmd = mock.call(
            ['apt-get', 'install', '--assume-yes'] + patched_packages,
            capture=True, retry_sleeps=APT_RETRIES)

        subp_calls = [
            mock.call(
                ['apt-get', 'update'], capture=True, retry_sleeps=APT_RETRIES),
            install_cmd]

        assert [mock.call(silent=mock.ANY)] == m_can_enable.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert 0 == m_add_pinning.call_count
        assert subp_calls == m_subp.call_args_list
        unlink_calls = [mock.call('/etc/apt/preferences.d/ubuntu-esm-trusty')]
        assert unlink_calls == m_unlink.call_args_list


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
                return_value={'series': 'trusty'})
    @mock.patch(M_PATH + 'can_disable', return_value=True)
    def test_disable_removes_apt_config(
            self, m_can_disable, m_platform_info, m_rm_repo_from_auth,
            entitlement, tmpdir, caplog_text):
        """When can_disable, disable removes apt configuration when forced."""

        with mock.patch('uaclient.util.subp'):
            with mock.patch('uaclient.util.write_file') as m_write:
                assert entitlement.disable(True, True)

        # Disable esm repo again
        write_calls = [mock.call(
            '/etc/apt/preferences.d/ubuntu-esm-trusty',
            'Package: *\nPin: release o=UbuntuESM, n=trusty\n'
            'Pin-Priority: never\n')]
        assert write_calls == m_write.call_args_list
        assert [mock.call(True, True)] == m_can_disable.call_args_list
        auth_call = mock.call('http://ESM')
        assert [auth_call] == m_rm_repo_from_auth.call_args_list
