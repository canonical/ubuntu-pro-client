import pytest

from uaclient import messages
from uaclient.entitlements.entitlement_status import (
    CanDisableFailure,
    CanDisableFailureReason,
)


class TestCanDisableFailure:
    @pytest.mark.parametrize(
        "can_disable_failure,expected",
        (
            (
                CanDisableFailure(
                    reason=CanDisableFailureReason.ALREADY_DISABLED,
                    message=None,
                ),
                "",
            ),
            (
                CanDisableFailure(
                    reason=CanDisableFailureReason.NOT_APPLICABLE,
                    message=messages.NamedMessage("test", "test"),
                ),
                "test",
            ),
        ),
    )
    def test_message_value(self, can_disable_failure, expected):
        assert expected == can_disable_failure.message_value
