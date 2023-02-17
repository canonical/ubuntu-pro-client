import datetime

import mock
import pytest

import uaclient.api.u.unattended_upgrades.status.v1 as api
from uaclient.messages import (
    UNATTENDED_UPGRADES_CFG_LIST_VALUE_EMPTY,
    UNATTENDED_UPGRADES_CFG_VALUE_TURNED_OFF,
    UNATTENDED_UPGRADES_SYSTEMD_JOB_DISABLED,
)

M_PATH = "uaclient.api.u.unattended_upgrades.status.v1"


class TestUnattendedUpgradesGetAptDailyJob:
    @pytest.mark.parametrize(
        "job_state_return,expected_return",
        (
            ((True, True), True),
            ((False, True), False),
            ((True, False), False),
            ((False, False), False),
        ),
    )
    @mock.patch(M_PATH + ".get_systemd_job_state")
    def test_get_apt_daily_job_status(
        self, m_systemd_job_state, job_state_return, expected_return
    ):
        m_systemd_job_state.side_effect = job_state_return
        assert expected_return is api._get_apt_daily_job_status()


class TestIsUnattendedUpgradesRunning:
    @pytest.mark.parametrize(
        "apt_timer_enabled,unattended_upgrades_cfg,expected_ret,expected_msg",
        (
            (False, {}, False, UNATTENDED_UPGRADES_SYSTEMD_JOB_DISABLED),
            (
                True,
                {"test": []},
                False,
                UNATTENDED_UPGRADES_CFG_LIST_VALUE_EMPTY.format(
                    cfg_name="test"
                ),
            ),
            (
                True,
                {"test": ["foo"], "test2": "0"},
                False,
                UNATTENDED_UPGRADES_CFG_VALUE_TURNED_OFF.format(
                    cfg_name="test2"
                ),
            ),
            (
                True,
                {"test": ["foo"], "test2": "1"},
                True,
                None,
            ),
        ),
    )
    def test_is_unattended_upgrades_running(
        self,
        apt_timer_enabled,
        unattended_upgrades_cfg,
        expected_ret,
        expected_msg,
    ):
        assert (
            expected_ret,
            expected_msg,
        ) == api._is_unattended_upgrades_running(
            apt_timer_enabled, unattended_upgrades_cfg
        )


class TestUnattendedUpgradesLastRun:
    @mock.patch("os.path.getctime")
    def test_unattended_upgrades_last_run_when_file_not_present(
        self,
        m_getctime,
    ):
        m_getctime.side_effect = FileNotFoundError()
        assert None is api._get_unattended_upgrades_last_run()


class TestUnattendedUpgradesStatusV1:
    @mock.patch(M_PATH + ".get_apt_config_keys")
    @mock.patch(M_PATH + ".get_apt_config_values")
    @mock.patch(M_PATH + "._is_unattended_upgrades_running")
    @mock.patch(M_PATH + "._get_apt_daily_job_status")
    @mock.patch(M_PATH + "._get_unattended_upgrades_last_run")
    def test_unattended_upgrades_status_v1(
        self,
        m_last_run,
        m_apt_job_status,
        m_is_running,
        m_apt_cfg_values,
        m_apt_cfg_keys,
        FakeConfig,
    ):
        expected_datetime = datetime.datetime(2023, 2, 23, 15, 0, 0, 102490)

        m_is_running.return_value = (True, "")
        m_apt_job_status.return_value = True
        m_last_run.return_value = expected_datetime
        m_apt_cfg_values.return_value = {
            "APT::Periodic::Enable": "",
            "APT::Periodic::Update-Package-Lists": "1",
            "APT::Periodic::Unattended-Upgrade": "1",
            "Unattended-Upgrade::Allowed-Origins": ["test"],
            "Unattended-Upgrade::Mail": "mail",
        }
        m_apt_cfg_keys.return_value = ["Unattended-Upgrade::Mail"]

        actual_return = api._status(FakeConfig())
        assert True is actual_return.apt_periodic_job_enabled
        assert True is actual_return.systemd_apt_timer_enabled
        assert 1 == actual_return.package_lists_refresh_frequency_days
        assert 1 == actual_return.unattended_upgrades_frequency_days
        assert ["test"] == actual_return.unattended_upgrades_allowed_origins
        assert True is actual_return.unattended_upgrades_running
        assert expected_datetime == actual_return.unattended_upgrades_last_run
        assert None is actual_return.unattended_upgrades_disabled_reason
        assert (
            "1"
            == actual_return.meta["raw_config"][
                "APT::Periodic::Unattended-Upgrade"
            ]
        )
        assert "1" == actual_return.meta["raw_config"]["APT::Periodic::Enable"]
        assert (
            "1"
            == actual_return.meta["raw_config"][
                "APT::Periodic::Update-Package-Lists"
            ]
        )
        assert ["test"] == actual_return.meta["raw_config"][
            "Unattended-Upgrade::Allowed-Origins"
        ]
        assert (
            "mail"
            == actual_return.meta["raw_config"]["Unattended-Upgrade::Mail"]
        )

        assert m_is_running.call_count == 1
        assert m_apt_job_status.call_count == 1
        assert m_apt_cfg_values.call_count == 1
        assert m_last_run.call_count == 1
