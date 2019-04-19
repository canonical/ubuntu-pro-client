"""Tests related to uaclient.entitlement.base module."""

import pytest

from uaclient import config
from uaclient.entitlements import base
from uaclient import status

try:
    from typing import Tuple  # noqa
except ImportError:
    pass


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


@pytest.fixture
def concrete_entitlement_factory(tmpdir):
    def factory(
            *, entitled: bool, operational_status: 'Tuple[str, str]' = None
    ) -> ConcreteTestEntitlement:
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        machineToken = {
            'machineToken': 'blah',
            'machineTokenInfo': {
                'contractInfo': {
                    'resourceEntitlements': [
                        {'type': 'testconcreteentitlement'}]}}}
        cfg.write_cache('machine-token', machineToken)
        cfg.write_cache('machine-access-testconcreteentitlement',
                        {'entitlement': {'entitled': entitled}})
        return ConcreteTestEntitlement(
            cfg, operational_status=operational_status)
    return factory


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

    def test_can_disable_false_on_unentitled(
            self, capsys, concrete_entitlement_factory):
        """When entitlement contract is not enabled, can_disable is False."""
        entitlement = concrete_entitlement_factory(
            entitled=False, operational_status=(status.INACTIVE, ''))

        assert not entitlement.can_disable()

        expected_stdout = (
            'This subscription is not entitled to Test Concrete Entitlement.\n'
            'See `ua status` or https://ubuntu.com/advantage\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_disable_false_on_entitlement_inactive(
            self, capsys, concrete_entitlement_factory):
        """When operational status is INACTIVE, can_disable returns False."""
        entitlement = concrete_entitlement_factory(
            entitled=True, operational_status=(status.INACTIVE, ''))

        assert not entitlement.can_disable()

        expected_stdout = (
            'Test Concrete Entitlement is not currently enabled.\n'
            'See `ua status`\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_disable_true_on_entitlement_active(
            self, capsys, concrete_entitlement_factory):
        """When operational status is ACTIVE, can_disable returns True."""
        entitlement = concrete_entitlement_factory(
            entitled=True, operational_status=(status.ACTIVE, ''))

        assert entitlement.can_disable()

        stdout, _ = capsys.readouterr()
        assert '' == stdout

    def test_can_enable_false_on_unentitled(
            self, capsys, concrete_entitlement_factory):
        """When entitlement contract is not enabled, can_enable is False."""

        entitlement = concrete_entitlement_factory(
            entitled=False, operational_status=(status.INACTIVE, ''))

        assert not entitlement.can_enable()

        expected_stdout = (
            'This subscription is not entitled to Test Concrete Entitlement.\n'
            'See `ua status` or https://ubuntu.com/advantage\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_enable_false_on_entitlement_active(
            self, capsys, concrete_entitlement_factory):
        """When operational status is ACTIVE, can_enable returns False."""
        entitlement = concrete_entitlement_factory(
            entitled=True, operational_status=(status.ACTIVE, ''))

        assert not entitlement.can_enable()

        expected_stdout = (
            'Test Concrete Entitlement is already enabled.\nSee `ua status`\n')
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_enable_false_on_entitlement_inapplicable(
            self, capsys, concrete_entitlement_factory):
        """When operational status INAPPLICABLE, can_enable returns False."""
        entitlement = concrete_entitlement_factory(
            entitled=True, operational_status=(status.INAPPLICABLE, 'msg'))

        assert not entitlement.can_enable()

        expected_stdout = 'msg\n'
        stdout, _ = capsys.readouterr()
        assert expected_stdout == stdout

    def test_can_enable_true_on_entitlement_inactive(
            self, capsys, concrete_entitlement_factory):
        """When operational status is INACTIVE, can_enable returns True."""
        entitlement = concrete_entitlement_factory(
            entitled=True, operational_status=(status.INACTIVE, ''))

        assert entitlement.can_enable()

        stdout, _ = capsys.readouterr()
        assert '' == stdout

    def test_contract_status_entitled(self, concrete_entitlement_factory):
        """The contract_status returns ENTITLED when entitlement enabled."""
        entitlement = concrete_entitlement_factory(entitled=True)
        assert status.ENTITLED == entitlement.contract_status()

    def test_contract_status_unentitled(self, concrete_entitlement_factory):
        """The contract_status returns NONE when entitlement is unentitled."""
        entitlement = concrete_entitlement_factory(entitled=False)
        assert status.NONE == entitlement.contract_status()
