"""Tests related to uaclient.entitlement.base module."""

import mock
from io import StringIO

from uaclient import config
from uaclient import status
from uaclient.entitlements.cc import CommonCriteriaEntitlement
from uaclient.testing.helpers import TestCase


CC_MACHINE_TOKEN = {
    'machineSecret': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'cc'}]}}}


CC_RESOURCE_ENTITLED = {
    'resourceToken': 'TOKEN',
    'entitlement': {
        'obligations': {
            'enableByDefault': False
        },
        'type': 'cc',
        'entitled': True,
        'directives': {
            'aptURL': 'http://CC',
            'aptKey': 'APTKEY'
        },
        'affordances': {
            'series': ['xenial']
        }
    }
}


class TestCommonCriteriaEntitlementCanEnable(TestCase):

    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_true_on_entitlement_inactive(
            self, m_getuid, m_platform_info):
        """When operational status is INACTIVE, can_enable returns True."""
        m_platform_info.return_value = 'xenial'
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', CC_MACHINE_TOKEN)
        cfg.write_cache('machine-access-cc', CC_RESOURCE_ENTITLED)
        entitlement = CommonCriteriaEntitlement(cfg)
        op_status, op_status_details = entitlement.operational_status()
        assert status.INACTIVE == op_status
        details = '%s PPA is not configured' % entitlement.title
        assert details == op_status_details
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert True is entitlement.can_enable()
        assert '' == m_stdout.getvalue()


class TestCommonCriteriaEntitlementEnable(TestCase):

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch('os.getuid', return_value=0)
    def test_enable_configures_apt_sources_and_auth_files(
            self, m_getuid, m_platform_info, m_subp):
        """When entitled, configure apt repo auth token, pinning and url."""
        m_platform_info.return_value = 'xenial'
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', CC_MACHINE_TOKEN)
        cfg.write_cache('machine-access-cc', CC_RESOURCE_ENTITLED)
        entitlement = CommonCriteriaEntitlement(cfg)

        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt:
                with mock.patch('uaclient.apt.add_ppa_pinning') as m_add_pin:
                    assert True is entitlement.enable()

        add_apt_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-cc-xenial.list',
                      'http://CC', 'TOKEN', None, 'APTKEY')]

        subp_apt_cmds = [
            mock.call(['apt-get', 'update'], capture=True),
            mock.call(['apt-get', 'install', 'ubuntu-commoncriteria'])]

        assert add_apt_calls == m_add_apt.call_args_list
        # No apt pinning for cc
        assert [] == m_add_pin.call_args_list
        assert subp_apt_cmds == m_subp.call_args_list
        expected_stdout = (
            'Installing Canonical Common Criteria EAL2 Provisioning packages'
            ' (this may take a while)\nCanonical Common Criteria EAL2'
            ' Provisioning enabled.\n')
        assert expected_stdout == m_stdout.getvalue()
