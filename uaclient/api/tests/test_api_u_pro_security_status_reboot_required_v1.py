import mock
import pytest

from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.security_status import RebootStatus

PATH = "uaclient.api.u.pro.security.status.reboot_required.v1."


class TestRebootStatus:
    @pytest.mark.parametrize(
        "reboot_state",
        (
            (RebootStatus.REBOOT_REQUIRED),
            (RebootStatus.REBOOT_NOT_REQUIRED),
            (RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED),
        ),
    )
    @mock.patch(PATH + "get_reboot_status")
    def test_reboot_status_api(self, m_get_reboot_status, reboot_state):
        m_get_reboot_status.return_value = reboot_state
        assert (
            reboot_state.value
            == _reboot_required(mock.MagicMock()).reboot_required
        )
