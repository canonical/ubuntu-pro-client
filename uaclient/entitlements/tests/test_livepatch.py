"""Tests related to uaclient.entitlement.base module."""

import copy
from io import StringIO
import mock
from types import MappingProxyType

import pytest

from uaclient import config
from uaclient.entitlements.livepatch import (
    LivepatchEntitlement, process_config_directives)
from uaclient.entitlements.repo import APT_RETRIES
from uaclient import status
from uaclient.status import ContractStatus


LIVEPATCH_MACHINE_TOKEN = MappingProxyType({
    'machineToken': 'blah',
    'machineTokenInfo': {
        'contractInfo': {
            'resourceEntitlements': [
                {'type': 'livepatch', 'entitled': True}]}}})


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
            'architectures': ['x86_64'],
            'minKernelVersion': '4.3',
            'kernelFlavors': ['generic', 'lowlatency'],
            'tier': 'stable'
        }
    }
})

PLATFORM_INFO_SUPPORTED = MappingProxyType({
    'arch': 'x86_64',
    'kernel': '4.4.0-00-generic',
    'series': 'xenial'
})

M_PATH = 'uaclient.entitlements.livepatch.'  # mock path
M_BASE_PATH = 'uaclient.entitlements.base.UAEntitlement.'


@pytest.fixture
def entitlement(tmpdir):
    """
    A pytest fixture to create a LivepatchEntitlement with some default config

    (Uses the tmpdir fixture for the underlying config cache.)
    """
    cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
    cfg.write_cache('machine-token', dict(LIVEPATCH_MACHINE_TOKEN))
    cfg.write_cache(
        'machine-access-livepatch', dict(LIVEPATCH_RESOURCE_ENTITLED))
    return LivepatchEntitlement(cfg)


class TestLivepatchContractStatus:

    def test_contract_status_entitled(self, entitlement):
        """The contract_status returns ENTITLED when entitled is True."""
        assert ContractStatus.ENTITLED == entitlement.contract_status()

    def test_contract_status_unentitled(self, entitlement):
        """The contract_status returns NONE when entitled is False."""
        entitlement.cfg.write_cache(
            'machine-access-livepatch', {'entitlement': {'entitled': False}})
        assert ContractStatus.UNENTITLED == entitlement.contract_status()


class TestLivepatchOperationalStatus:

    def test_operational_status_inapplicable_on_inapplicable_status(
            self, entitlement):
        """The operational_status details INAPPLICABLE applicability_status"""
        livepatch_bionic = copy.deepcopy(dict(LIVEPATCH_RESOURCE_ENTITLED))
        livepatch_bionic['entitlement']['affordances']['series'] = ['bionic']
        entitlement.cfg.write_cache(
            'machine-access-livepatch', livepatch_bionic)

        with mock.patch('uaclient.util.get_platform_info') as m_platform_info:
            m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
            op_status, details = entitlement.operational_status()
        assert op_status == status.INAPPLICABLE
        assert 'Livepatch is not available for Ubuntu xenial.' == details

    def test_operational_status_inapplicable_on_unentitled(
            self, entitlement):
        """Status inapplicable on absent entitlement contract status."""
        no_entitlements = copy.deepcopy(dict(LIVEPATCH_MACHINE_TOKEN))
        # Delete livepatch entitlement info
        no_entitlements[
            'machineTokenInfo']['contractInfo']['resourceEntitlements'].pop()
        entitlement.cfg.write_cache('machine-token', no_entitlements)

        with mock.patch('uaclient.util.get_platform_info') as m_platform_info:
            m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
            op_status, details = entitlement.operational_status()
        assert op_status == status.INAPPLICABLE
        assert 'Livepatch is not entitled' == details


class TestLivepatchProcessConfigDirectives:

    @pytest.mark.parametrize('directive_key,livepatch_param_tmpl', (
        ('remoteServer', 'remote-server=%s'), ('caCerts', 'ca-certs=%s')))
    def test_call_livepatch_config_command(
            self, directive_key, livepatch_param_tmpl):
        """Livepatch config directives are passed to livepatch config."""
        directive_value = '%s-value' % directive_key
        cfg = {'entitlement': {'directives': {directive_key: directive_value}}}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_config_directives(cfg)
        expected_subp = mock.call(
            ['/snap/bin/canonical-livepatch', 'config',
             livepatch_param_tmpl % directive_value], capture=True)
        assert [expected_subp] == m_subp.call_args_list

    def test_handle_multiple_directives(self):
        """Handle multiple Livepatch directives using livepatch config."""
        cfg = {
            'entitlement': {'directives': {'remoteServer': 'value1',
                                           'caCerts': 'value2',
                                           'ignored': 'ignoredvalue'}}}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_config_directives(cfg)
        expected_calls = [
            mock.call(['/snap/bin/canonical-livepatch', 'config',
                       'ca-certs=value2'], capture=True),
            mock.call(['/snap/bin/canonical-livepatch', 'config',
                       'remote-server=value1'], capture=True)]
        assert expected_calls == m_subp.call_args_list

    @pytest.mark.parametrize('directives', ({}, {'otherkey': 'othervalue'}))
    def test_ignores_other_or_absent(self, directives):
        """Ignore empty or unexpected directives and do not call livepatch."""
        cfg = {'entitlement': {'directives': directives}}
        with mock.patch('uaclient.util.subp') as m_subp:
            process_config_directives(cfg)
        assert 0 == m_subp.call_count


class TestLivepatchEntitlementCanEnable:

    def test_can_enable_true_on_entitlement_inactive(self, entitlement):
        """When operational status is INACTIVE, can_enable returns True."""
        with mock.patch('uaclient.util.get_platform_info') as m_platform:
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                with mock.patch('uaclient.util.is_container') as m_container:
                    m_platform.return_value = PLATFORM_INFO_SUPPORTED
                    m_container.return_value = False
                    assert entitlement.can_enable()
        assert '' == m_stdout.getvalue()
        assert [mock.call()] == m_container.call_args_list

    def test_can_enable_false_on_unsupported_kernel_min_version(
            self, entitlement):
        """"False when on a kernel less or equal to minKernelVersion."""
        unsupported_min_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_min_kernel['kernel'] = '4.2.9-00-generic'
        with mock.patch('uaclient.util.get_platform_info') as m_platform:
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                m_platform.return_value = unsupported_min_kernel
                entitlement = LivepatchEntitlement(
                    entitlement.cfg)
                assert not entitlement.can_enable()
        msg = ('Livepatch is not available for kernel 4.2.9-00-generic.\n'
               'Minimum kernel version required: 4.3\n')
        assert msg == m_stdout.getvalue()

    def test_can_enable_false_on_unsupported_kernel_flavor(self, entitlement):
        """"When on an unsupported kernel, can_enable returns False."""
        unsupported_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_kernel['kernel'] = '4.4.0-140-notgeneric'
        with mock.patch('uaclient.util.get_platform_info') as m_platform:
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                m_platform.return_value = unsupported_kernel
                entitlement = LivepatchEntitlement(
                    entitlement.cfg)
                assert not entitlement.can_enable()
        msg = ('Livepatch is not available for kernel 4.4.0-140-notgeneric.\n'
               'Supported flavors are: generic, lowlatency\n')
        assert msg == m_stdout.getvalue()

    def test_can_enable_false_on_unsupported_architecture(self, entitlement):
        """"When on an unsupported architecture, can_enable returns False."""
        unsupported_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_kernel['arch'] = 'ppc64le'
        with mock.patch('uaclient.util.get_platform_info') as m_platform:
            with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
                m_platform.return_value = unsupported_kernel
                assert not entitlement.can_enable()
        msg = ('Livepatch is not available for platform ppc64le.\n'
               'Supported platforms are: x86_64\n')
        assert msg == m_stdout.getvalue()

    def test_can_enable_false_on_containers(self, entitlement):
        """When is_container is True, can_enable returns False."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            with mock.patch('uaclient.util.get_platform_info') as m_platform:
                with mock.patch('uaclient.util.is_container') as m_container:
                    m_platform.return_value = PLATFORM_INFO_SUPPORTED
                    m_container.return_value = True
                    entitlement = LivepatchEntitlement(
                        entitlement.cfg)
                    assert not entitlement.can_enable()
        msg = 'Cannot install Livepatch on a container\n'
        assert msg == m_stdout.getvalue()


class TestLivepatchProcessContractDeltas:

    @mock.patch(M_PATH + 'LivepatchEntitlement.setup_livepatch_config')
    def test_true_on_parent_process_deltas(
            self, m_setup_livepatch_config, entitlement):
        """When parent's process_contract_deltas returns True do no setup."""
        assert entitlement.process_contract_deltas({}, {}, False)
        assert [] == m_setup_livepatch_config.call_args_list

    @mock.patch(M_PATH + 'LivepatchEntitlement.setup_livepatch_config')
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    @mock.patch(M_PATH + 'LivepatchEntitlement.applicability_status')
    def test_true_on_inactive_livepatch_service(
            self, m_applicability_status, m_application_status,
            m_setup_livepatch_config, entitlement):
        """When livepatch is INACTIVE return True and do no setup."""
        m_applicability_status.return_value = (
            status.ApplicabilityStatus.APPLICABLE, '')
        m_application_status.return_value = (
            status.ApplicationStatus.DISABLED, '')
        deltas = {'entitlement': {'directives': {'caCerts': 'new'}}}
        assert entitlement.process_contract_deltas({}, deltas, False)
        assert [] == m_setup_livepatch_config.call_args_list

    @pytest.mark.parametrize(
        'directives,process_directives,process_token', (
            ({'caCerts': 'new'}, True, False),
            ({'remoteServer': 'new'}, True, False),
            ({'unhandledKey': 'new'}, False, False)))
    @mock.patch(M_PATH + 'LivepatchEntitlement.setup_livepatch_config')
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    def test_setup_performed_when_active_and_supported_deltas(
            self, m_application_status, m_setup_livepatch_config, entitlement,
            directives, process_directives, process_token):
        """Run setup when livepatch ACTIVE and deltas are supported keys."""
        m_application_status.return_value = (
            status.ApplicationStatus.ENABLED, '')
        deltas = {'entitlement': {'directives': directives}}
        assert entitlement.process_contract_deltas({}, deltas, False)
        if any([process_directives, process_token]):
            setup_calls = [
                mock.call(process_directives=process_directives,
                          process_token=process_token)]
        else:
            setup_calls = []
        assert setup_calls == m_setup_livepatch_config.call_args_list

    @pytest.mark.parametrize(
        'deltas,process_directives,process_token', (
            ({'entitlement': {'something': 1}}, False, False),
            ({'resourceToken': 'new'}, False, True)))
    @mock.patch(M_PATH + 'LivepatchEntitlement.setup_livepatch_config')
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    def test_livepatch_disable_and_setup_performed_when_resource_token_changes(
            self, m_application_status, m_setup_livepatch_config, entitlement,
            deltas, process_directives, process_token):
        """Run livepatch calls setup when resourceToken changes."""
        m_application_status.return_value = (
            status.ApplicationStatus.ENABLED, '')
        entitlement.process_contract_deltas({}, deltas, False)
        if any([process_directives, process_token]):
            setup_calls = [
                mock.call(process_directives=process_directives,
                          process_token=process_token)]
        else:
            setup_calls = []
        assert setup_calls == m_setup_livepatch_config.call_args_list


class TestLivepatchEntitlementEnable:

    with_logs = True

    mocks_snapd_install = [
        mock.call(
            ['apt-get', 'install', '--assume-yes', 'snapd'], capture=True,
            retry_sleeps=APT_RETRIES),
        mock.call(['snap', 'wait', 'system', 'seed.loaded'], capture=True),
    ]
    mocks_livepatch_install = [
        mock.call(['snap', 'install', 'canonical-livepatch'], capture=True,
                  retry_sleeps=[0.5, 1, 5]),
    ]
    mocks_install = mocks_snapd_install + mocks_livepatch_install
    mocks_config = [
        mock.call(
            ['/snap/bin/canonical-livepatch', 'config',
             'remote-server=https://alt.livepatch.com'], capture=True),
        mock.call(
            ['/snap/bin/canonical-livepatch', 'disable']),
        mock.call(
            ['/snap/bin/canonical-livepatch', 'enable', 'TOKEN'], capture=True)
    ]

    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=False)
    def test_enable_false_when_can_enable_false(
            self, m_can_enable, caplog_text, entitlement):
        """When can_enable returns False enable returns False."""
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert not entitlement.enable()
        assert '' == caplog_text()
        assert '' == m_stdout.getvalue()  # No additional prints
        assert [mock.call(silent=mock.ANY)] == m_can_enable.call_args_list

    @pytest.mark.parametrize('silent_if_inapplicable', (True, False, None))
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=False)
    def test_enable_passes_silent_if_inapplicable_through(
            self, m_can_enable, caplog_text, entitlement,
            silent_if_inapplicable):
        """When can_enable returns False enable returns False."""
        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs['silent_if_inapplicable'] = silent_if_inapplicable
        entitlement.enable(**kwargs)

        expected_call = mock.call(silent=bool(silent_if_inapplicable))
        assert [expected_call] == m_can_enable.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.which', return_value=False)
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=True)
    def test_enable_installs_snapd_and_livepatch_snap_when_absent(
            self, m_can_enable, m_app_status, m_which, m_subp, entitlement):
        """Install snapd and canonical-livepatch snap when not on system."""
        m_app_status.return_value = status.ApplicationStatus.ENABLED, 'enabled'
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert entitlement.enable()
        assert self.mocks_install + self.mocks_config in m_subp.call_args_list
        msg = ('Installing snapd...\n'
               'Installing canonical-livepatch snap...\n'
               'Canonical livepatch enabled.\n')
        assert msg == m_stdout.getvalue()
        expected_calls = [mock.call('/snap/bin/canonical-livepatch'),
                          mock.call('snap')]
        assert expected_calls == m_which.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.which', side_effect=lambda cmd: cmd == 'snap')
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=True)
    def test_enable_installs_only_livepatch_snap_when_absent_but_snapd_present(
            self, m_can_enable, m_app_status, m_which, m_subp, entitlement):
        """Install canonical-livepatch snap when not present on the system."""
        m_app_status.return_value = status.ApplicationStatus.ENABLED, 'enabled'
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert entitlement.enable()
        assert (self.mocks_livepatch_install + self.mocks_config
                in m_subp.call_args_list)
        msg = ('Installing canonical-livepatch snap...\n'
               'Canonical livepatch enabled.\n')
        assert msg == m_stdout.getvalue()
        expected_calls = [mock.call('/snap/bin/canonical-livepatch'),
                          mock.call('snap')]
        assert expected_calls == m_which.call_args_list

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.which', return_value='/found/livepatch')
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=True)
    def test_enable_does_not_install_livepatch_snap_when_present(
            self, m_can_enable, m_app_status, m_which, m_subp, entitlement):
        """Do not attempt to install livepatch snap when it is present."""
        m_app_status.return_value = status.ApplicationStatus.ENABLED, 'enabled'
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert entitlement.enable()
        assert self.mocks_config == m_subp.call_args_list
        assert 'Canonical livepatch enabled.\n' == m_stdout.getvalue()

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.which', return_value='/found/livepatch')
    @mock.patch(M_PATH + 'LivepatchEntitlement.application_status')
    @mock.patch(M_PATH + 'LivepatchEntitlement.can_enable', return_value=True)
    def test_enable_does_not_disable_inactive_livepatch_snap_when_present(
            self, m_can_enable, m_app_status, m_which, m_subp, entitlement):
        """Do not attempt to disable livepatch snap when it is inactive."""

        m_app_status.return_value = status.ApplicationStatus.DISABLED, 'nope'
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            assert entitlement.enable()
        subp_no_livepatch_disable = [
            mock.call(
                ['/snap/bin/canonical-livepatch', 'config',
                 'remote-server=https://alt.livepatch.com'], capture=True),
            mock.call(
                ['/snap/bin/canonical-livepatch', 'enable', 'TOKEN'],
                capture=True)]
        assert subp_no_livepatch_disable == m_subp.call_args_list
        assert 'Canonical livepatch enabled.\n' == m_stdout.getvalue()
