"""Tests related to uaclient.entitlement.base module."""

import mock
import os
from io import StringIO

from uaclient import apt
from uaclient import config
from uaclient.entitlements.fips import FIPSEntitlement
from uaclient import status
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


class BaseEnabledFIPSConfig(TestCase):
    """Setup enabled FIPS entitlement."""

    def setUp(self):
        super().setUp()
        tmp_dir = self.tmp_dir()
        self.cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        self.cfg.write_cache('machine-token', FIPS_MACHINE_TOKEN)
        self.cfg.write_cache('machine-access-fips', FIPS_RESOURCE_ENTITLED)
        self.entitlement = FIPSEntitlement(self.cfg)


class TestFIPSEntitlementCanEnable(BaseEnabledFIPSConfig):

    @mock.patch('uaclient.util.is_container', mock.Mock(return_value=False))
    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_true_on_entitlement_inactive(self, m_getuid):
        """When operational status is INACTIVE, can_enable returns True."""
        op_status, op_status_details = self.entitlement.operational_status()
        assert status.INACTIVE == op_status
        assert 'FIPS PPA is not configured' == op_status_details
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert True is self.entitlement.can_enable()
        assert '' == m_stdout.getvalue()

    @mock.patch('uaclient.util.is_container', mock.Mock(return_value=True))
    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_false_on_containers(self, m_getuid):
        """On containers, can_enable is false and operational status n/a."""
        op_status, op_status_details = self.entitlement.operational_status()
        assert status.INAPPLICABLE == op_status
        msg_cant_install = 'Cannot install FIPS on a container'
        assert msg_cant_install == op_status_details
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert False is self.entitlement.can_enable()
        assert msg_cant_install + '\n' == m_stdout.getvalue()


class TestFIPSEntitlementEnable(BaseEnabledFIPSConfig):

    @mock.patch('uaclient.util.get_platform_info', return_value='xenial')
    def test_enable_configures_apt_sources_and_auth_files_and_installs(
            self, _platform_info):
        """When entitled, configure apt repo, auth, pin and install debs."""

        self.entitlement.can_enable = lambda: True

        orig_exists = os.path.exists

        def fake_exists(path):
            if path in (apt.APT_METHOD_HTTPS_FILE, apt.APT_METHOD_HTTPS_FILE):
                return False
            else:
                return orig_exists(path)

        with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt_src:
            with mock.patch('uaclient.apt.add_ppa_pinning') as m_add_pinning:
                with mock.patch('uaclient.util.subp') as m_subp:
                    with mock.patch('os.path.exists', side_effect=fake_exists):
                        self.assertTrue(self.entitlement.enable())

        add_apt_src_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-fips-xenial.list',
                      'http://FIPS', 'TOKEN', None, 'APTKEY')]
        apt_pinning_calls = [
            mock.call('/etc/apt/preferences.d/ubuntu-fips-xenial',
                      'http://FIPS', 1001)]
        install_packages = self.entitlement.packages
        apt_cmd_calls = [
            mock.call(['apt-get', 'update'], capture=True),
            mock.call(['apt-get', 'install'] + install_packages, capture=True)]

        assert add_apt_src_calls == m_add_apt_src.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
        assert apt_cmd_calls == m_subp.call_args_list
