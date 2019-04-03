"""Tests related to uaclient.entitlement.base module."""

from io import StringIO
import itertools
import mock
import os

import pytest

from uaclient import config
from uaclient.entitlements.fips import FIPSEntitlement
from uaclient.testing.helpers import TestCase


FIPS_MACHINE_TOKEN = {
    'machineToken': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'fips'}]}}}


FIPS_RESOURCE_ENTITLED = {
    'resourceToken': 'TOKEN',
    'entitlement': {
        'obligations': {
            'enableByDefault': True
        },
        'type': 'fips',
        'entitled': True,
        'directives': {
            'aptURL': 'http://FIPS',
            'aptKey': 'APTKEY'
        },
        'affordances': {
            'series': []   # Will match all series
        }
    }
}

M_PATH = 'uaclient.entitlements.fips.FIPSEntitlement.'
M_REPOPATH = 'uaclient.entitlements.repo.'


class TestFIPSEntitlementCanEnable(TestCase):

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_true_on_entitlement_inactive(self, m_getuid):
        """When operational status is INACTIVE, can_enable returns True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', FIPS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-fips', FIPS_RESOURCE_ENTITLED)
        entitlement = FIPSEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertTrue(entitlement.can_enable())
        self.assertEqual('', m_stdout.getvalue())


class TestFIPSEntitlementEnable:

    @mock.patch(
        'uaclient.util.get_platform_info', mock.Mock(return_value='xenial'))
    @mock.patch(M_PATH + 'can_enable', return_value=True)
    def test_enable_configures_apt_sources_and_auth_files(
            self, m_can_enable, tmpdir):
        """When entitled, configure apt repo auth token, pinning and url."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', FIPS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-fips', FIPS_RESOURCE_ENTITLED)
        entitlement = FIPSEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()

        with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt:
            with mock.patch('uaclient.apt.add_ppa_pinning') as m_add_pinning:
                with mock.patch('uaclient.util.subp') as m_subp:
                    with mock.patch(M_REPOPATH + 'os.path.exists'):
                        assert True is entitlement.enable()

        add_apt_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-fips-xenial.list',
                      'http://FIPS', 'TOKEN', None, 'APTKEY')]
        apt_pinning_calls = [
            mock.call('/etc/apt/preferences.d/ubuntu-fips-xenial',
                      'http://FIPS', 'UbuntuFIPS', 1001)]
        subp_calls = [
            mock.call(['apt-get', 'update'], capture=True),
            mock.call(['apt-get', 'install'] + entitlement.packages,
                      capture=True)]

        assert [mock.call()] == m_can_enable.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
        assert subp_calls == m_subp.call_args_list

    @mock.patch(
        'uaclient.util.get_platform_info', return_value='xenial')
    @mock.patch(M_PATH + 'can_enable', mock.Mock(return_value=False))
    def test_enable_returns_false_on_can_enable_false(self, m_platform_info):
        """When can_enable is false enable returns false and noops."""
        entitlement = FIPSEntitlement({})

        assert False is entitlement.enable()
        assert 0 == m_platform_info.call_count

    @mock.patch(
        'uaclient.util.get_platform_info', mock.Mock(return_value='xenial'))
    @mock.patch(M_PATH + 'can_enable', mock.Mock(return_value=True))
    def test_enable_errors_on_repo_pin_but_invalid_origin(
            self, caplog_text, tmpdir):
        """When can_enable is false enable returns false and noops."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', FIPS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-fips', FIPS_RESOURCE_ENTITLED)
        entitlement = FIPSEntitlement(cfg)
        entitlement.origin = None  # invalid value

        with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt:
            with mock.patch('uaclient.apt.add_ppa_pinning') as m_add_pinning:
                with mock.patch(M_REPOPATH + 'os.path.exists'):
                    assert False is entitlement.enable()

        assert 0 == m_add_apt.call_count
        assert 0 == m_add_pinning.call_count
        assert 'ERROR    Cannot setup apt pin' in caplog_text()


class TestFIPSEntitlementDisable:

    # Paramterize True/False for silent and force
    @pytest.mark.parametrize(
        'silent,force', itertools.product([False, True], repeat=2))
    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch(M_PATH + 'can_disable', return_value=False)
    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
            self, m_can_disable, m_platform_info, silent, force):
        """When can_disable is false disable returns false and noops."""
        entitlement = FIPSEntitlement({})

        with mock.patch('uaclient.apt.remove_auth_apt_repo') as m_remove_apt:
            assert False is entitlement.disable(silent, force)
        assert [mock.call(silent, force)] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count

    @mock.patch('uaclient.apt.remove_apt_list_files')
    @mock.patch('uaclient.apt.remove_auth_apt_repo')
    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch(M_PATH + 'can_disable', return_value=True)
    def test_disable_returns_false_and_removes_apt_config_on_force(
            self, m_can_disable, m_platform_info, m_rm_auth, m_rm_list,
            tmpdir, caplog_text):
        """When can_disable, disable removes apt configuration when force."""
        m_platform_info.return_value = 'xenial'
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', FIPS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-fips', FIPS_RESOURCE_ENTITLED)
        entitlement = FIPSEntitlement(cfg)

        original_exists = os.path.exists

        def fake_exists(path):
            if path == '/etc/apt/preferences.d/ubuntu-fips-xenial':
                return True
            return original_exists(path)

        with mock.patch('os.path.exists', side_effect=fake_exists):
            with mock.patch('uaclient.apt.os.unlink') as m_unlink:
                with mock.patch('uaclient.util.subp') as m_subp:
                    assert False is entitlement.disable(True, True)
        assert [mock.call(True, True)] == m_can_disable.call_args_list
        calls = [mock.call('/etc/apt/preferences.d/ubuntu-fips-xenial')]
        assert calls == m_unlink.call_args_list
        auth_call = mock.call(
            '/etc/apt/sources.list.d/ubuntu-fips-xenial.list',
            'http://FIPS', '/etc/apt/trusted.gpg.d/ubuntu-fips-keyring.gpg')
        assert [auth_call] == m_rm_auth.call_args_list
        assert [mock.call('http://FIPS', 'xenial')] == m_rm_list.call_args_list
        apt_cmd = mock.call(
            ['apt-get', 'remove', '--frontend=noninteractive',
             '--assume-yes'] + entitlement.packages)
        assert [apt_cmd] == m_subp.call_args_list

    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch(M_PATH + 'can_disable', return_value=True)
    def test_disable_returns_false_does_nothing_by_default(
            self, m_can_disable, m_platform_info, caplog_text):
        """When can_disable, disable does nothing without force param."""
        entitlement = FIPSEntitlement({})

        with mock.patch('uaclient.apt.remove_auth_apt_repo') as m_remove_apt:
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                assert False is entitlement.disable()
        assert [mock.call(False, False)] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count
        assert 'Warning: no option to disable FIPS\n' == m_stdout.getvalue()
