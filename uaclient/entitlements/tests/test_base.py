"""Tests related to uaclient.entitlement.base module."""

import pytest

from uaclient import config
from uaclient.entitlements import base
from uaclient import status


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


class TestUaEntitlement:

    def test_entitlement_abstract_class(self):
        """UAEntitlement is abstract requiring concrete methods."""
        with pytest.raises(TypeError) as excinfo:
            base.UAEntitlement()
        expected_msg = (
            "Can't instantiate abstract class UAEntitlement with abstract"
            " methods disable, enable, operational_status")
        assert expected_msg == str(excinfo.value)

    def test_init_default_sets_up_uaconfig(self):
        """UAEntitlement sets up a uaconfig instance upon init."""
        entitlement = ConcreteTestEntitlement()
        assert '/var/lib/ubuntu-advantage' == entitlement.cfg.data_dir

    def test_init_accepts_a_uaconfig(self):
        """An instance of UAConfig can be passed to UAEntitlement."""
        cfg = config.UAConfig(cfg={'data_dir': '/some/path'})
        entitlement = ConcreteTestEntitlement(cfg)
        assert '/some/path' == entitlement.cfg.data_dir

    def test_can_disable_false_on_unentitled(self, tmpdir, capsys):
        """When entitlement contract is not enabled, can_disable is False."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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

        assert not entitlement.can_disable()

        expected_stdout = (
            'This subscription is not entitled to Test Concrete Entitlement.\n'
            'See `ua status` or https://ubuntu.com/advantage\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_disable_false_on_entitlement_inactive(self, tmpdir, capsys):
        """When operational status is INACTIVE, can_disable returns False."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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

        assert not entitlement.can_disable()

        expected_stdout = (
            'Test Concrete Entitlement is not currently enabled.\n'
            'See `ua status`\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_disable_true_on_entitlement_active(self, tmpdir, capsys):
        """When operational status is ACTIVE, can_disable returns True."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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

        assert entitlement.can_disable()

        stdout, _ = capsys.readouterr()
        assert '' == stdout

    def test_can_enable_false_on_unentitled(self, capsys, tmpdir):
        """When entitlement contract is not enabled, can_enable is False."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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

        assert not entitlement.can_enable()

        expected_stdout = (
            'This subscription is not entitled to Test Concrete Entitlement.\n'
            'See `ua status` or https://ubuntu.com/advantage\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_enable_false_on_entitlement_active(self, capsys, tmpdir):
        """When operational status is ACTIVE, can_enable returns False."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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

        assert not entitlement.can_enable()

        expected_stdout = (
            'Test Concrete Entitlement is already enabled.\nSee `ua status`\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_enable_true_on_entitlement_inactive(self, capsys, tmpdir):
        """When operational status is INACTIVE, can_enable returns True."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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

        assert entitlement.can_enable()

        stdout, _ = capsys.readouterr()
        assert '' == stdout

    def test_contract_status_entitled(self, tmpdir):
        """The contract_status returns ENTITLED when entitlement enabled."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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
        assert status.ENTITLED == entitlement.contract_status()

    def test_contract_status_unentitled(self, tmpdir):
        """The contract_status returns NONE when entitlement is unentitled."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
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
        assert status.NONE == entitlement.contract_status()
