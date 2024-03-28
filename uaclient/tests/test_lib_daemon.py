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
                ["active"] * 2,
                [],
            ),
            # inactive (all cloud-init)
            (
                ["inactive"] * 2,
                [],
            ),
            (
                [None] * 2,
                [],
            ),
            # cloud-config activating, then finishes
            # cloud-init is active
            (
                (["activating", "active"] * 11) + ["active"] * 2,
                [mock.call(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)] * 11,
            ),
            (
                (["activating", "active"] * 11) + ["failed"] + ["active"],
                [mock.call(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)] * 11,
            ),
            # inactive cloud-config, active cloud-init
            (
                (["inactive", "active"] * 6)
                + (["activating", "active"] * 5)
                + ["active"] * 2,
                [mock.call(WAIT_FOR_CLOUD_CONFIG_SLEEP_TIME)] * 11,
            ),
            # inactive cloud-config, activating cloud-init
            (
                (["inactive", "activating"] * 2)
                + (["inactive", "active"] * 4)
                + (["activating", "active"] * 5)
                + ["active"] * 2,
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
