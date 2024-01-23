from functools import partial

import pytest

from uaclient import messages
from uaclient.entitlements.cc import CC_README, CommonCriteriaEntitlement


@pytest.fixture
def cc_entitlement(entitlement_factory):
    return partial(
        entitlement_factory,
        CommonCriteriaEntitlement,
    )


class TestCISEntitlement:
    @pytest.mark.parametrize(
        "access_only,expected",
        (
            (
                True,
                {
                    "pre_install": [messages.CC_PRE_INSTALL],
                    "post_enable": None,
                },
            ),
            (
                False,
                {
                    "pre_install": [messages.CC_PRE_INSTALL],
                    "post_enable": [
                        messages.CC_POST_ENABLE.format(filename=CC_README)
                    ],
                },
            ),
        ),
    )
    def test_messages(self, access_only, expected, cc_entitlement):
        entitlement = cc_entitlement(access_only=access_only)
        assert expected == entitlement.messaging
