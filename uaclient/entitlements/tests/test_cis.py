"""Tests related to uaclient.entitlement.base module."""

from functools import partial

import pytest

from uaclient import messages
from uaclient.entitlements.cis import CISEntitlement


@pytest.fixture
def cis_entitlement(entitlement_factory):
    return partial(
        entitlement_factory,
        CISEntitlement,
    )


class TestCISEntitlement:
    def test_messages(self, cis_entitlement):
        entitlement = cis_entitlement()

        assert {
            "post_enable": [messages.CIS_POST_ENABLE]
        } == entitlement.messaging
