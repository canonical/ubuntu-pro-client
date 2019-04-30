"""Tests related to uaclient.entitlement.base module."""

import mock
from io import StringIO

from uaclient import config
from uaclient.entitlements.cis import CISEntitlement
from uaclient.testing.helpers import TestCase


CIS_MACHINE_TOKEN = {
    'machineToken': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'cis-audit', 'entitled': True}]}}}


CIS_RESOURCE_ENTITLED = {
    'resourceToken': 'TOKEN',
    'entitlement': {
        'obligations': {
            'enableByDefault': True
        },
        'type': 'cis-audit',
        'entitled': True,
        'directives': {
            'aptURL': 'http://CIS',
            'aptKey': 'APTKEY',
            'suites': ['xenial']
        },
        'affordances': {
            'series': []   # Will match all series
        }
    }
}


class TestCISEntitlementCanEnable(TestCase):

    def test_can_enable_true_on_entitlement_inactive(self):
        """When operational status is INACTIVE, can_enable returns True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', CIS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-cis-audit', CIS_RESOURCE_ENTITLED)
        entitlement = CISEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertTrue(entitlement.can_enable())
        self.assertEqual('', m_stdout.getvalue())


class TestCISEntitlementEnable(TestCase):

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.get_platform_info')
    def test_enable_configures_apt_sources_and_auth_files(
            self, m_platform_info, m_subp):
        """When entitled, configure apt repo auth token, pinning and url."""

        def fake_platform(key=None):
            info = {
                'series': 'xenial', 'kernel': '4.15.0-00-generic'}
            if key:
                return info[key]
            return info

        m_platform_info.side_effect = fake_platform
        m_subp.return_value = ('fakeout', '')
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        cfg.write_cache('machine-token', CIS_MACHINE_TOKEN)
        cfg.write_cache('machine-access-cis-audit', CIS_RESOURCE_ENTITLED)
        entitlement = CISEntitlement(cfg)
        # Unset static affordance container check
        entitlement.static_affordances = ()

        with mock.patch('uaclient.entitlements.repo.os.path.exists',
                        mock.Mock(return_value=True)):
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt:
                    with mock.patch(
                            'uaclient.apt.add_ppa_pinning') as m_add_pin:
                        self.assertTrue(entitlement.enable())

        add_apt_calls = [
            mock.call(
                '/etc/apt/sources.list.d/ubuntu-cis-audit-xenial.list',
                'http://CIS', 'TOKEN', ['xenial'],
                '/usr/share/keyrings/ubuntu-securitybenchmarks-keyring.gpg')]

        subp_apt_cmds = [
            mock.call(['apt-cache', 'policy']),
            mock.call(['apt-get', 'update'], capture=True),
            mock.call(
                ['apt-get', 'install', '--assume-yes'] + entitlement.packages,
                capture=True)]

        assert add_apt_calls == m_add_apt.call_args_list
        # No apt pinning for cis-audit
        assert [] == m_add_pin.call_args_list
        assert subp_apt_cmds == m_subp.call_args_list
        expected_stdout = (
            'Updating package lists ...\n'
            'Installing Canonical CIS Benchmark Audit Tool packages ...\n'
            'Canonical CIS Benchmark Audit Tool enabled.\n')
        assert expected_stdout == m_stdout.getvalue()
