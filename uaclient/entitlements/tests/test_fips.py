"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
from io import StringIO
import itertools
import mock
import os

import pytest

from uaclient import config, status
from uaclient.entitlements.fips import FIPSEntitlement, FIPSUpdatesEntitlement

try:
    from typing import Any, Dict  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


def machine_token(fips_type: str) -> 'Dict[str, Any]':
    return {
        'machineToken': 'blah',
        'machineTokenInfo': {
            'contractInfo': {
                'resourceEntitlements': [
                    {'type': fips_type, 'entitled': True}]}}}


def machine_access(fips_type: str) -> 'Dict[str, Any]':
    return {
        'resourceToken': 'TOKEN',
        'entitlement': {
            'obligations': {
                'enableByDefault': True
            },
            'type': fips_type,
            'entitled': True,
            'directives': {
                'aptURL': 'http://FIPS',
                'aptKey': 'APTKEY',
                'suites': ['xenial']
            },
            'affordances': {
                'series': []   # Will match all series
            }
        }
    }


M_PATH = 'uaclient.entitlements.fips.'
M_REPOPATH = 'uaclient.entitlements.repo.'
M_GETPLATFORM = M_REPOPATH + 'util.get_platform_info'


@pytest.fixture(params=[FIPSEntitlement, FIPSUpdatesEntitlement])
def entitlement(request, tmpdir):
    """
    pytest fixture for a FIPS/FIPS Updates entitlement with some default config

    (Uses the tmpdir fixture for the underlying config cache.)
    """
    cls = request.param
    cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
    cfg.write_cache('machine-token', machine_token(cls.name))
    cfg.write_cache('machine-access-{}'.format(cls.name),
                    machine_access(cls.name))
    return cls(cfg)


class TestFIPSEntitlementCanEnable:

    def test_can_enable_true_on_entitlement_inactive(self, entitlement):
        """When operational status is INACTIVE, can_enable returns True."""
        with mock.patch.object(entitlement, 'operational_status',
                               return_value=(status.INACTIVE, '')):
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                assert True is entitlement.can_enable()
        assert '' == m_stdout.getvalue()


class TestFIPSEntitlementEnable:

    def test_enable_configures_apt_sources_and_auth_files(self, entitlement):
        """When entitled, configure apt repo auth token, pinning and url."""
        patched_packages = ['a', 'b']
        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch('uaclient.apt.add_auth_apt_repo'))
            m_add_pinning = stack.enter_context(
                mock.patch('uaclient.apt.add_ppa_pinning'))
            m_subp = stack.enter_context(mock.patch('uaclient.util.subp'))
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, 'can_enable'))
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value='xenial'))
            stack.enter_context(mock.patch(M_REPOPATH + 'os.path.exists'))
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), 'packages', m_packages))

            m_can_enable.return_value = True

            assert True is entitlement.enable()

        add_apt_calls = [
            mock.call(
                '/etc/apt/sources.list.d/ubuntu-{}-xenial.list'.format(
                    entitlement.name),
                'http://FIPS', 'TOKEN', ['xenial'],
                '/usr/share/keyrings/ubuntu-{}-keyring.gpg'.format(
                    entitlement.name))]
        apt_pinning_calls = [
            mock.call(
                '/etc/apt/preferences.d/ubuntu-{}-xenial'.format(
                    entitlement.name),
                'http://FIPS', entitlement.origin, 1001)]
        install_cmd = mock.call(
            ['apt-get', 'install', '--assume-yes'] + patched_packages,
            capture=True)

        subp_calls = [
            mock.call(['apt-get', 'update'], capture=True), install_cmd]

        assert [mock.call(silent=mock.ANY)] == m_can_enable.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
        assert subp_calls == m_subp.call_args_list

    @mock.patch(
        'uaclient.util.get_platform_info', return_value='xenial')
    def test_enable_returns_false_on_can_enable_false(
            self, m_platform_info, entitlement):
        """When can_enable is false enable returns false and noops."""
        with mock.patch.object(entitlement, 'can_enable', return_value=False):
            assert False is entitlement.enable()
        assert 0 == m_platform_info.call_count

    @mock.patch('uaclient.apt.add_auth_apt_repo')
    @mock.patch(
        'uaclient.util.get_platform_info', return_value='xenial')
    def test_enable_returns_false_on_missing_suites_directive(
            self, m_platform_info, m_add_apt, entitlement):
        """When directives do not contain suites returns false."""
        # Unset suites directive
        fips_entitled_no_suites = copy.deepcopy(
            machine_access(entitlement.name))
        fips_entitled_no_suites['entitlement']['directives']['suites'] = []
        entitlement.cfg.write_cache(
            'machine-access-{}'.format(entitlement.name),
            fips_entitled_no_suites)

        with mock.patch.object(entitlement, 'can_enable', return_value=True):
            assert False is entitlement.enable()
        assert 0 == m_add_apt.call_count

    def test_enable_errors_on_repo_pin_but_invalid_origin(
            self, caplog_text, entitlement):
        """When can_enable is false enable returns false and noops."""
        entitlement.origin = None  # invalid value

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch('uaclient.apt.add_auth_apt_repo'))
            m_add_pinning = stack.enter_context(
                mock.patch('uaclient.apt.add_ppa_pinning'))
            stack.enter_context(mock.patch.object(entitlement, 'can_enable'))
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value='xenial'))
            stack.enter_context(mock.patch(M_REPOPATH + 'os.path.exists'))

            assert False is entitlement.enable()

        assert 0 == m_add_apt.call_count
        assert 0 == m_add_pinning.call_count
        assert 'ERROR    Cannot setup apt pin' in caplog_text()


class TestFIPSEntitlementDisable:

    # Paramterize True/False for silent and force
    @pytest.mark.parametrize(
        'silent,force', itertools.product([False, True], repeat=2))
    @mock.patch('uaclient.util.get_platform_info')
    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
            self, m_platform_info, entitlement, silent, force):
        """When can_disable is false disable returns false and noops."""
        with mock.patch('uaclient.apt.remove_auth_apt_repo') as m_remove_apt:
            with mock.patch.object(entitlement, 'can_disable',
                                   return_value=False) as m_can_disable:
                assert False is entitlement.disable(silent, force)
        assert [mock.call(silent, force)] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count

    @mock.patch('uaclient.apt.remove_apt_list_files')
    @mock.patch('uaclient.apt.remove_auth_apt_repo')
    @mock.patch(
        'uaclient.util.get_platform_info', return_value='xenial')
    def test_disable_returns_false_and_removes_apt_config_on_force(
            self, m_platform_info, m_rm_auth, m_rm_list,
            entitlement, caplog_text):
        """When can_disable, disable removes apt configuration when force."""

        original_exists = os.path.exists
        patched_packages = ['c', 'd']
        preferences_path = '/etc/apt/preferences.d/ubuntu-{}-xenial'.format(
            entitlement.name)

        def fake_exists(path):
            if path == preferences_path:
                return True
            return original_exists(path)

        with contextlib.ExitStack() as stack:
            m_can_disable = stack.enter_context(
                mock.patch.object(
                    entitlement, 'can_disable', return_value=True))
            stack.enter_context(
                mock.patch('os.path.exists', side_effect=fake_exists))
            m_unlink = stack.enter_context(
                mock.patch('uaclient.apt.os.unlink'))
            m_subp = stack.enter_context(mock.patch('uaclient.util.subp'))
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), 'packages', m_packages))

            assert False is entitlement.disable(True, True)
        assert [mock.call(True, True)] == m_can_disable.call_args_list
        calls = [mock.call(preferences_path)]
        assert calls == m_unlink.call_args_list
        auth_call = mock.call(
            '/etc/apt/sources.list.d/ubuntu-{}-xenial.list'.format(
                entitlement.name),
            'http://FIPS',
            '/etc/apt/trusted.gpg.d/ubuntu-{}-keyring.gpg'.format(
                entitlement.name)
        )
        assert [auth_call] == m_rm_auth.call_args_list
        assert [mock.call('http://FIPS', 'xenial')] == m_rm_list.call_args_list
        apt_cmd = mock.call(
            ['apt-get', 'remove', '--assume-yes'] + patched_packages)
        assert [apt_cmd] == m_subp.call_args_list

    @mock.patch('uaclient.util.get_platform_info')
    def test_disable_returns_false_does_nothing_by_default(
            self, m_platform_info, caplog_text, entitlement):
        """When can_disable, disable does nothing without force param."""
        with mock.patch.object(entitlement, 'can_disable',
                               return_value=True) as m_can_disable:
            with mock.patch('uaclient.apt.remove_auth_apt_repo'
                            ) as m_remove_apt:
                with mock.patch('sys.stdout',
                                new_callable=StringIO) as m_stdout:
                    assert False is entitlement.disable()
        assert [mock.call(False, False)] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count
        expected_stdout = 'Warning: no option to disable {}\n'.format(
            entitlement.title)
        assert expected_stdout == m_stdout.getvalue()
