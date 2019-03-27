"""Tests related to uaclient.entitlement.base module."""

import mock

from uaclient import config
from uaclient.entitlements.livepatch import LivepatchEntitlement
from uaclient import status
from uaclient.testing.helpers import TestCase


class TestLivepatchContractStatus(TestCase):

    def test_contract_status_entitled(self):
        """The contract_status returns ENTITLED when entitled is True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineSecret': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'livepatch'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-livepatch',
                        {'entitlement': {'entitled': True}})
        entitlement = LivepatchEntitlement(cfg)
        self.assertEqual(status.ENTITLED, entitlement.contract_status())

    def test_contract_status_unentitled(self):
        """The contract_status returns NONE when entitled is False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineSecret': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'livepatch'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-livepatch',
                        {'entitlement': {'entitled': False}})
        entitlement = LivepatchEntitlement(cfg)
        self.assertEqual(status.NONE, entitlement.contract_status())


class TestLivepatchOperationalStatus(TestCase):

    def test_operational_status_inapplicable_on_checked_affordances(self):
        """The operational_status details failed check_affordances."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineSecret': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'livepatch'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-livepatch',
                        {'entitlement': {
                            'entitled': True,
                            'affordances': {'series': ['bionic']}}})
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
        machineToken = {
            'machineSecret': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'livepatch'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-livepatch',
                        {'entitlement': {'entitled': False}})
        entitlement = LivepatchEntitlement(cfg)
        self.assertEqual(status.NONE, entitlement.contract_status())
