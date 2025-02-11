"""Tests related to uaclient.entitlement.base module."""

from functools import partial

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

        assert {
            "post_enable": [messages.USG_POST_ENABLE]
        } == entitlement.messaging
