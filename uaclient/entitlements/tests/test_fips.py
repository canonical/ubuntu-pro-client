"""Tests related to uaclient.entitlement.base module."""

import mock
from io import StringIO

from uaclient import config
from uaclient.entitlements.fips import FIPSEntitlement
from uaclient.testing.helpers import TestCase


FIPS_MACHINE_TOKEN = {
    'machineSecret': 'blah',
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


class TestFIPSEntitlementEnable(TestCase):

    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch('os.getuid', return_value=0)
    def test_enable_configures_apt_sources_and_auth_files(
            self, m_getuid, m_platform_info):
        """When entitled, configure apt repo auth token, pinning and url."""
        m_platform_info.return_value = 'xenial'
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', FIPS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-fips', FIPS_RESOURCE_ENTITLED)
        entitlement = FIPSEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()

        with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt:
            with mock.patch('uaclient.apt.add_ppa_pinning') as m_add_pinning:
                self.assertTrue(entitlement.enable())

        add_apt_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-fips-xenial.list',
                      'http://FIPS', 'TOKEN', None, 'APTKEY')]
        apt_pinning_calls = [
            mock.call('/etc/apt/preferences.d/ubuntu-fips-xenial',
                      'http://FIPS', 'UbuntuFIPS', 1001)]

        assert add_apt_calls == m_add_apt.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
