"""Tests related to uaclient.entitlement.base module."""

from uaclient.entitlements import base
from uaclient.testing.helpers import TestCase


class TestConcreteEntitlement(base.UAEntitlement):

    def __init__(self, cfg=None, disable=None, enable=None,
                 operational_status=None):
        super(TestConcreteEntitlement, self).__init__(cfg)
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

    def test_init_sets_up_uaconfig(self):
        """UAEntitlement sets up a uaconfig instance upon init."""
        entitlement = TestConcreteEntitlement()
        self.assertEqual('/tmp/uaclient', entitlement.cfg.data_dir)
