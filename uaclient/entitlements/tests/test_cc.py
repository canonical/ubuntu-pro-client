"""Tests related to uaclient.entitlement.base module."""

import itertools
import mock
import os.path
from io import StringIO
from types import MappingProxyType

import pytest

from uaclient import apt
from uaclient import config
from uaclient import status
from uaclient.entitlements.cc import CC_README, CommonCriteriaEntitlement


CC_MACHINE_TOKEN = {
    'machineToken': 'blah',
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
            'architectures': ['x86_64', 'ppc64le', 's390x'],
            'series': ['xenial']
        }
    }
}

PLATFORM_INFO_SUPPORTED = MappingProxyType({
    'arch': 's390x',
    'series': 'xenial'
})


class TestCommonCriteriaEntitlementCanEnable:

    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_true_on_entitlement_inactive(
            self, m_getuid, m_platform_info, tmpdir):
        """When operational status is INACTIVE, can_enable returns True."""
        m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', CC_MACHINE_TOKEN)
        cfg.write_cache('machine-access-cc', CC_RESOURCE_ENTITLED)
        entitlement = CommonCriteriaEntitlement(cfg)
        op_status, op_status_details = entitlement.operational_status()
        assert status.INACTIVE == op_status
        details = '%s is not configured' % entitlement.title
        assert details == op_status_details
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert True is entitlement.can_enable()
        assert '' == m_stdout.getvalue()


class TestCommonCriteriaEntitlementEnable:

    # Paramterize True/False for apt_transport_https and ca_certificates
    @pytest.mark.parametrize('apt_transport_https,ca_certificates',
                             itertools.product([False, True], repeat=2))
    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.get_platform_info')
    @mock.patch('os.getuid', return_value=0)
    def test_enable_configures_apt_sources_and_auth_files(
            self, m_getuid, m_platform_info, m_subp, tmpdir,
            apt_transport_https, ca_certificates):
        """When entitled, configure apt repo auth token, pinning and url."""
        m_subp.return_value = ('fakeout', '')
        original_exists = os.path.exists

        def fake_platform(key=None):
            if key == 'series':
                return PLATFORM_INFO_SUPPORTED[key]
            return PLATFORM_INFO_SUPPORTED

        def exists(path):
            if path == apt.APT_METHOD_HTTPS_FILE:
                return not apt_transport_https
            elif path == apt.CA_CERTIFICATES_FILE:
                return not ca_certificates
            elif not path.startswith(tmpdir.strpath):
                raise Exception(
                    'os.path.exists call outside of tmpdir: {}'.format(path))
            return original_exists(path)

        m_platform_info.side_effect = fake_platform
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        cfg.write_cache('machine-token', CC_MACHINE_TOKEN)
        cfg.write_cache('machine-access-cc', CC_RESOURCE_ENTITLED)
        entitlement = CommonCriteriaEntitlement(cfg)

        with mock.patch('uaclient.apt.add_auth_apt_repo') as m_add_apt:
            with mock.patch('uaclient.apt.add_ppa_pinning') as m_add_pin:
                with mock.patch('uaclient.entitlements.repo.os.path.exists',
                                side_effect=exists):
                    with mock.patch('sys.stdout',
                                    new_callable=StringIO) as m_stdout:
                        assert True is entitlement.enable()

        add_apt_calls = [
            mock.call('/etc/apt/sources.list.d/ubuntu-cc-xenial.list',
                      'http://CC', 'TOKEN', None, 'APTKEY')]

        subp_apt_cmds = [mock.call(['apt-cache', 'policy'])]

        prerequisite_pkgs = []
        if apt_transport_https:
            prerequisite_pkgs.append('apt-transport-https')
        if ca_certificates:
            prerequisite_pkgs.append('ca-certificates')

        if prerequisite_pkgs:
            expected_stdout = (
                'Installing prerequisites: %s\n' % ', '.join(
                    prerequisite_pkgs))
            subp_apt_cmds.append(
                mock.call(
                    ['apt-get', 'install', '--assume-yes'] + prerequisite_pkgs,
                    capture=True))
        else:
            expected_stdout = ''

        subp_apt_cmds.extend([
            mock.call(['apt-get', 'update'], capture=True),
            mock.call(
                ['apt-get', 'install', '--assume-yes'] + entitlement.packages,
                capture=True)])

        assert add_apt_calls == m_add_apt.call_args_list
        # No apt pinning for cc
        assert [] == m_add_pin.call_args_list
        assert subp_apt_cmds == m_subp.call_args_list
        expected_stdout += (
            'Updating package lists ...\n'
            'Installing Canonical Common Criteria EAL2 Provisioning'
            ' packages ...\nCanonical Common Criteria EAL2 Provisioning'
            ' enabled.\nPlease follow instructions in %s to configure EAL2\n'
            % CC_README)
        assert expected_stdout == m_stdout.getvalue()
