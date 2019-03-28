"""Tests related to uaclient.entitlement.base module."""

import copy
from io import StringIO
import mock
from nose2.tools.params import params

from uaclient import config
from uaclient.entitlements.livepatch import (
    LivepatchEntitlement, process_directives)
from uaclient import status
from uaclient.testing.helpers import TestCase


LIVEPATCH_MACHINE_TOKEN = {
    'machineSecret': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'livepatch'}]}}}


LIVEPATCH_RESOURCE_ENTITLED = {
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
}


class TestLivepatchContractStatus(TestCase):

    def test_contract_status_entitled(self):
        """The contract_status returns ENTITLED when entitled is True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        cfg.write_cache('machine-access-livepatch',
                        LIVEPATCH_RESOURCE_ENTITLED)
        entitlement = LivepatchEntitlement(cfg)
        self.assertEqual(status.ENTITLED, entitlement.contract_status())

    def test_contract_status_unentitled(self):
        """The contract_status returns NONE when entitled is False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        livepatch_unentitled = copy.deepcopy(LIVEPATCH_RESOURCE_ENTITLED)

        # Make livepatch resource access report not entitled
        livepatch_unentitled['entitlement']['entitled'] = False
        cfg.write_cache('machine-access-livepatch', livepatch_unentitled)
        entitlement = LivepatchEntitlement(cfg)
        self.assertEqual(status.NONE, entitlement.contract_status())


class TestLivepatchOperationalStatus(TestCase):

    def test_operational_status_inapplicable_on_checked_affordances(self):
        """The operational_status details failed check_affordances."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        livepatch_bionic = copy.deepcopy(LIVEPATCH_RESOURCE_ENTITLED)
        livepatch_bionic['entitlement']['affordances']['series'] = ['bionic']
        cfg.write_cache('machine-access-livepatch', livepatch_bionic)
        entitlement = LivepatchEntitlement(cfg)
        with mock.patch('uaclient.util.get_platform_info') as m_platform_info:
            m_platform_info.return_value = 'xenial'
            op_status, details = entitlement.operational_status()
        assert op_status == status.INAPPLICABLE
        assert 'Livepatch is not available for Ubuntu xenial.' == details

    def test_contract_status_unentitled(self):
        """The contract_status returns NONE when entitled is False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        cfg.write_cache('machine-access-livepatch',
                        {'entitlement': {'entitled': False}})
        entitlement = LivepatchEntitlement(cfg)
        self.assertEqual(status.NONE, entitlement.contract_status())


class TestLivepatchProcessDirectives(TestCase):

    @params(('remoteServer', 'remote-server=%s'), ('caCerts', 'ca-certs=%s'))
    def test_process_directives_call_livepatch_config_command(
            self, directive_key, livepatch_param_tmpl):
        """Livepatch config directives are passed to livepatch config."""
        directive_value = '%s-value' % directive_key
        cfg = {directive_key: directive_value}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_directives(cfg)
        livepatch_cmd = ['/snap/bin/canonical-livepatch', 'config',
                         livepatch_param_tmpl % directive_value]
        assert [mock.call(livepatch_cmd)] == m_subp.call_args_list

    def test_process_directives_ignores_other_directives(self):
        """Only Livepatch directives are passed to livepatch config."""
        cfg = {'otherkey': 'othervalue'}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_directives(cfg)
        assert 0 == m_subp.call_count


class TestLivepatchEntitlementCanEnable(TestCase):

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_true_on_entitlement_inactive(self, m_getuid):
        """When operational status is INACTIVE, can_enable returns True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        cfg.write_cache('machine-access-livepatch',
                        LIVEPATCH_RESOURCE_ENTITLED)
        entitlement = LivepatchEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertTrue(entitlement.can_enable())
        self.assertEqual('', m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_false_on_containers(self, m_getuid):
        """When in a is_container is True, can_enable returns False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        cfg.write_cache('machine-access-livepatch',
                        LIVEPATCH_RESOURCE_ENTITLED)
        with mock.patch('uaclient.util.is_container') as m_is_container:
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                m_is_container.return_value = True
                entitlement = LivepatchEntitlement(cfg)
                self.assertFalse(entitlement.can_enable())
        msg = 'Cannot install Livepatch on a container\n'
        assert msg == m_stdout.getvalue()


class TestLivepatchEntitlementEnable(TestCase):
    with_logs = True

    @mock.patch('os.getuid', return_value=1)
    def test_enable_false_when_can_enable_false(self, m_getuid):
        """When can_enable returns False enable returns False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', LIVEPATCH_MACHINE_TOKEN)
        cfg.write_cache('machine-access-livepatch',
                        LIVEPATCH_RESOURCE_ENTITLED)
        entitlement = LivepatchEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.enable())
        msg = 'This command must be run as root (try using sudo)\n'
        assert msg == m_stdout.getvalue()
        assert '' == self.logs
