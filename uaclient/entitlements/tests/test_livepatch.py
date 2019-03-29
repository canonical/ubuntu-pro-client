"""Tests related to uaclient.entitlement.base module."""

import copy
from io import StringIO
import mock
from types import MappingProxyType

import pytest

from uaclient import config
from uaclient.entitlements.livepatch import (
    LivepatchEntitlement, process_directives)
from uaclient import status


LIVEPATCH_MACHINE_TOKEN = MappingProxyType({
    'machineSecret': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'livepatch'}]}}})


LIVEPATCH_RESOURCE_ENTITLED = MappingProxyType({
    'resourceToken': 'TOKEN',
    'entitlement': {
        'obligations': {
            'enableByDefault': False
        },
        'type': 'livepatch',
        'entitled': True,
        'directives': {
            'caCerts': '',
            'remoteServer': 'https://alt.livepatch.com'
        },
        'affordances': {
            'kernelFlavors': ['generic', 'lowlatency'],
            'tier': 'stable'
        }
    }
})

M_PATH = 'uaclient.entitlements.livepatch.'  # mock path


@pytest.fixture
def livepatch_entitlement(tmpdir):
    """
    A pytest fixture to create a LivepatchEntitlement with some default config

    (Uses the tmpdir fixture for the underlying config cache.)
    """
    cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
    cfg.write_cache('machine-token', dict(LIVEPATCH_MACHINE_TOKEN))
    cfg.write_cache('machine-access-livepatch',
                    dict(LIVEPATCH_RESOURCE_ENTITLED))
    return LivepatchEntitlement(cfg)


class TestLivepatchContractStatus:

    def test_contract_status_entitled(self, livepatch_entitlement):
        """The contract_status returns ENTITLED when entitled is True."""
        assert status.ENTITLED == livepatch_entitlement.contract_status()

    def test_contract_status_unentitled(self, livepatch_entitlement):
        """The contract_status returns NONE when entitled is False."""
        livepatch_unentitled = copy.deepcopy(dict(LIVEPATCH_RESOURCE_ENTITLED))

        # Make livepatch resource access report not entitled
        livepatch_unentitled['entitlement']['entitled'] = False
        livepatch_entitlement.cfg.write_cache(
            'machine-access-livepatch', livepatch_unentitled)
        assert status.NONE == livepatch_entitlement.contract_status()


class TestLivepatchOperationalStatus:

    def test_operational_status_inapplicable_on_checked_affordances(
            self, livepatch_entitlement):
        """The operational_status details failed check_affordances."""
        livepatch_bionic = copy.deepcopy(dict(LIVEPATCH_RESOURCE_ENTITLED))
        livepatch_bionic['entitlement']['affordances']['series'] = ['bionic']
        livepatch_entitlement.cfg.write_cache(
            'machine-access-livepatch', livepatch_bionic)

        with mock.patch('uaclient.util.get_platform_info') as m_platform_info:
            m_platform_info.return_value = 'xenial'
            op_status, details = livepatch_entitlement.operational_status()
        assert op_status == status.INAPPLICABLE
        assert 'Livepatch is not available for Ubuntu xenial.' == details

    def test_contract_status_unentitled(self, livepatch_entitlement):
        """The contract_status returns NONE when entitled is False."""
        livepatch_entitlement.cfg.write_cache(
            'machine-access-livepatch', {'entitlement': {'entitled': False}})
        assert status.NONE == livepatch_entitlement.contract_status()


class TestLivepatchProcessDirectives:

    @pytest.mark.parametrize('directive_key,livepatch_param_tmpl', (
        ('remoteServer', 'remote-server=%s'), ('caCerts', 'ca-certs=%s')))
    def test_process_directives_call_livepatch_config_command(
            self, directive_key, livepatch_param_tmpl):
        """Livepatch config directives are passed to livepatch config."""
        directive_value = '%s-value' % directive_key
        cfg = {'entitlement': {'directives': {directive_key: directive_value}}}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_directives(cfg)
        expected_subp = mock.call(
            ['/snap/bin/canonical-livepatch', 'config',
             livepatch_param_tmpl % directive_value], capture=True)
        assert [expected_subp] == m_subp.call_args_list

    def test_process_directives_handles_multiple_directives(self):
        """Handle multiple Livepatch directives using livepatch config."""
        cfg = {
            'entitlement': {'directives': {'remoteServer': 'value1',
                                           'caCerts': 'value2',
                                           'ignored': 'ignoredvalue'}}}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_directives(cfg)
        expected_calls = [
            mock.call(['/snap/bin/canonical-livepatch', 'config',
                       'remote-server=value1'], capture=True),
            mock.call(['/snap/bin/canonical-livepatch', 'config',
                       'ca-certs=value2'], capture=True)]
        assert expected_calls == m_subp.call_args_list

    @pytest.mark.parametrize('directives', ({}, {'otherkey': 'othervalue'}))
    def test_process_directives_ignores_other_or_absent(self, directives):
        """Ignore empty or unexpected directives and do not call livepatch."""
        cfg = {'entitlement': {'directives': directives}}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_directives(cfg)
        assert 0 == m_subp.call_count


@mock.patch('os.getuid', return_value=0)
class TestLivepatchEntitlementCanEnable:

    @mock.patch('uaclient.util.is_container', return_value=False)
    def test_can_enable_true_on_entitlement_inactive(
            self, m_getuid, m_is_container, livepatch_entitlement):
        """When operational status is INACTIVE, can_enable returns True."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert livepatch_entitlement.can_enable()
        assert '' == m_stdout.getvalue()
        assert [mock.call()] == m_is_container.call_args_list

    @mock.patch('uaclient.util.is_container', return_value=True)
    def test_can_enable_false_on_containers(
            self, m_getuid, m_is_container, livepatch_entitlement):
        """When in a is_container is True, can_enable returns False."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            entitlement = LivepatchEntitlement(livepatch_entitlement.cfg)
            assert not entitlement.can_enable()
        msg = 'Cannot install Livepatch on a container\n'
        assert msg == m_stdout.getvalue()


class TestLivepatchEntitlementEnable:

    with_logs = True

    mocks_install = [mock.call(
        ['snap', 'install', 'canonical-livepatch'], capture=True)]
    mocks_config = [
        mock.call(
            ['/snap/bin/canonical-livepatch', 'config',
             'remote-server=https://alt.livepatch.com'], capture=True),
        mock.call(
            ['/snap/bin/canonical-livepatch', 'enable', 'TOKEN'], capture=True)
    ]

    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=False)
    def test_enable_false_when_can_enable_false(
            self, m_can_enable, caplog_text, livepatch_entitlement):
        """When can_enable returns False enable returns False."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert not livepatch_entitlement.enable()
        assert '' == caplog_text()  # No additional logs on can_enable == False
        assert '' == m_stdout.getvalue()  # No additional prints
        assert [mock.call()] == m_can_enable.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.which', return_value=False)
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=True)
    def test_enable_installs_livepatch_snap_when_absent(
            self, m_can_enable, m_which, m_subp, livepatch_entitlement):
        """Install canonical-livepatch snap when not present on the system."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert livepatch_entitlement.enable()
        assert self.mocks_install + self.mocks_config in m_subp.call_args_list
        msg = ('Installing canonical-livepatch snap...\n'
               'Canonical livepatch enabled.\n')
        assert msg == m_stdout.getvalue()
        expected_calls = [mock.call('/snap/bin/canonical-livepatch')]
        assert expected_calls == m_which.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.which', return_value='/found/livepatch')
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=True)
    def test_enable_does_not_install_livepatch_snap_when_present(
            self, m_can_enable, m_which, m_subp, livepatch_entitlement):
        """Do not attempt to install livepatch snap when it is present."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert livepatch_entitlement.enable()
        assert self.mocks_config == m_subp.call_args_list
        assert 'Canonical livepatch enabled.\n' == m_stdout.getvalue()
