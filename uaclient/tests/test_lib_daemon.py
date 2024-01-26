import mock
import pytest

from lib.daemon import (
    WAIT_FOR_CLOUD_CONFIG_POLL_TIMES,
    WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME,
    _wait_for_cloud_config,
)


class TestWaitForCloudConfig:
    @pytest.mark.parametrize(
        [
            "active_state_side_effect",
            "expected_sleep_calls",
        ],
        (
            # not activating
            (
                ["active"],
                [],
            ),
            (
                ["inactive"],
                [],
            ),
            (
                [None],
                [],
            ),
            # activating, then finishes
            (
                (["activating"] * 11) + ["active"],
                [mock.call(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)] * 11,
            ),
            (
                (["activating"] * 11) + ["failed"],
                [mock.call(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)] * 11,
            ),
            # still activating after polling maximum times
            (
                ["activating"] * (WAIT_FOR_CLOUD_CONFIG_POLL_TIMES + 1000),
                [mock.call(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)]
                * WAIT_FOR_CLOUD_CONFIG_POLL_TIMES,
            ),
        ),
    )
    @mock.patch("lib.daemon.time.sleep")
    @mock.patch("lib.daemon.system.get_systemd_unit_active_state")
    def test_wait_for_cloud_config(
        self,
        m_get_systemd_unit_active_state,
        m_sleep,
        active_state_side_effect,
        expected_sleep_calls,
    ):
        m_get_systemd_unit_active_state.side_effect = active_state_side_effect
        _wait_for_cloud_config()
        assert m_sleep.call_args_list == expected_sleep_calls
