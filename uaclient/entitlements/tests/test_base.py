"""Tests related to uaclient.entitlement.base module."""

import mock
from io import StringIO

from uaclient import config
from uaclient.entitlements import base
from uaclient import status
from uaclient.testing.helpers import TestCase


class ConcreteTestEntitlement(base.UAEntitlement):

    name = 'testconcreteentitlement'
    title = 'Test Concrete Entitlement'

    def __init__(self, cfg=None, disable=None, enable=None,
                 operational_status=None):
        super().__init__(cfg)
        self._disable = disable
        self._enable = enable
        self._operational_status = operational_status

    def disable(self):
        return self._disable

    def enable(self):
        return self._enable

    def operational_status(self):
        return self._operational_status


class TestUaEntitlement(TestCase):

    def test_entitlement_abstract_class(self):
        """UAEntitlement is abstract requiring concrete methods."""
        with self.assertRaises(TypeError) as ctx_mgr:
            base.UAEntitlement()
        self.assertEqual(
            "Can't instantiate abstract class UAEntitlement with abstract"
            " methods disable, enable, operational_status",
            str(ctx_mgr.exception))

    def test_init_default_sets_up_uaconfig(self):
        """UAEntitlement sets up a uaconfig instance upon init."""
        entitlement = ConcreteTestEntitlement()
        self.assertEqual('/var/lib/ubuntu-advantage', entitlement.cfg.data_dir)

    def test_init_accepts_a_uaconfig(self):
        """An instance of UAConfig can be passed to UAEntitlement."""
        cfg = config.UAConfig(cfg={'data_dir': '/some/path'})
        entitlement = ConcreteTestEntitlement(cfg)
        self.assertEqual('/some/path', entitlement.cfg.data_dir)

    @mock.patch('os.getuid', return_value=100)
    def test_can_disable_requires_root(self, m_getuid):
        """Non-root users receive False from UAEntitlement.can_disable."""
        cfg = config.UAConfig(cfg={})
        entitlement = ConcreteTestEntitlement(cfg)
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_disable())
        self.assertEqual(
            'This command must be run as root (try using sudo)\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_disable_false_on_unattached_machine(self, m_getuid):
        """An unattached machine will return False from can_disable."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        entitlement = ConcreteTestEntitlement(cfg)
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_disable())
        self.assertEqual(
            'This machine is not attached to a UA subscription.\n'
            'See `ua attach` or https://ubuntu.com/advantage\n\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_disable_false_on_unentitled(self, m_getuid):
        """When entitlement contract is not enabled, can_disable is False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache(
            'machine-access-testconcreteentitlement',
            {'entitlement': {'entitled': False}})
        entitlement = ConcreteTestEntitlement(
            cfg, operational_status=(status.INACTIVE, ''))
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_disable())
        self.assertEqual(
            'This subscription is not entitled to Test Concrete Entitlement.\n'
            'See `ua status` or https://ubuntu.com/advantage\n\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_disable_false_on_entitlement_inactive(self, m_getuid):
        """When operational status is INACTIVE, can_disable returns False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': True}})
        entitlement = ConcreteTestEntitlement(
            cfg,
            operational_status=(status.INACTIVE, ''))
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_disable())
        self.assertEqual(
            'Test Concrete Entitlement is not currently enabled.\n'
            'See `ua status`\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_disable_true_on_entitlement_active(self, m_getuid):
        """When operational status is ACTIVE, can_disable returns True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': True}})
        entitlement = ConcreteTestEntitlement(
            cfg, operational_status=(status.ACTIVE, ''))
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertTrue(entitlement.can_disable())
        self.assertEqual('', m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=100)
    def test_can_enable_requires_root(self, m_getuid):
        """Non-root users receive False from UAEntitlement.can_enable."""
        cfg = config.UAConfig(cfg={})
        entitlement = ConcreteTestEntitlement(cfg)
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_enable())
        self.assertEqual(
            'This command must be run as root (try using sudo)\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_false_on_unattached_machine(self, m_getuid):
        """An unattached machine will return False from can_enable."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        entitlement = ConcreteTestEntitlement(cfg)
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_enable())
        self.assertEqual(
            'This machine is not attached to a UA subscription.\n'
            'See `ua attach` or https://ubuntu.com/advantage\n\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_false_on_unentitled(self, m_getuid):
        """When entitlement contract is not enabled, can_enable is False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': False}})
        entitlement = ConcreteTestEntitlement(
            cfg, operational_status=(status.INACTIVE, ''))
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_enable())
        self.assertEqual(
            'This subscription is not entitled to Test Concrete Entitlement.\n'
            'See `ua status` or https://ubuntu.com/advantage\n\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_false_on_entitlement_active(self, m_getuid):
        """When operational status is ACTIVE, can_enable returns False."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': True}})
        entitlement = ConcreteTestEntitlement(
            cfg, operational_status=(status.ACTIVE, ''))
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertFalse(entitlement.can_enable())
        self.assertEqual(
            'Test Concrete Entitlement is already enabled.\nSee `ua status`\n',
            m_stdout.getvalue())

    @mock.patch('os.getuid', return_value=0)
    def test_can_enable_true_on_entitlement_inactive(self, m_getuid):
        """When operational status is INACTIVE, can_enable returns True."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': True}})
        entitlement = ConcreteTestEntitlement(
            cfg, operational_status=(status.INACTIVE, ''))
        with mock.patch('sys.stdout', new_callable=StringIO) as m_stdout:
            self.assertTrue(entitlement.can_enable())
        self.assertEqual('', m_stdout.getvalue())

    def test_contract_status_entitled(self):
        """The contract_status returns ENTITLED when entitlement enabled."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': True}})
        entitlement = ConcreteTestEntitlement(cfg)
        self.assertEqual(status.ENTITLED, entitlement.contract_status())

    def test_contract_status_unentitled(self):
        """The contract_status returns NONE when entitlement is unentitled."""
        tmp_dir = self.tmp_dir()
        cfg = config.UAConfig(cfg={'data_dir': tmp_dir})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': False}})
        entitlement = ConcreteTestEntitlement(cfg)
        self.assertEqual(status.NONE, entitlement.contract_status())
