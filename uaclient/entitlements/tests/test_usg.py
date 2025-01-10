"""Tests related to uaclient.entitlement.base module."""

from functools import partial

import mock
import pytest

from uaclient import messages
from uaclient.entitlements.usg import USGEntitlement


@pytest.fixture
def usg_entitlement(entitlement_factory):
    return partial(
        entitlement_factory,
        USGEntitlement,
    )


class TestUSGEntitlement:
    def test_messages(self, usg_entitlement):
        entitlement = usg_entitlement()

        with mock.patch.object(entitlement, "cis_version", False):
            assert {
                "pre_enable": None,
                "post_enable": [messages.USG_POST_ENABLE],
            } == entitlement.messaging

        with mock.patch.object(entitlement, "cis_version", True):
            assert {
                "pre_enable": [messages.CIS_IS_NOW_USG],
                "post_enable": [messages.USG_POST_ENABLE],
            } == entitlement.messaging
