import logging

import mock
import pytest

from uaclient.upgrade_lts_contract import process_contract_delta_after_apt_lock


@pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
class TestUpgradeLTSContract:
    @mock.patch("uaclient.upgrade_lts_contract._is_attached")
    def test_unattached_noops(
        self, m_is_attached, capsys, caplog_text, FakeConfig
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=False)
        expected_logs = [
            "Check whether to upgrade-lts-contract",
            "Skipping upgrade-lts-contract. Machine is unattached",
        ]

        process_contract_delta_after_apt_lock(FakeConfig())

        assert 1 == m_is_attached.call_count
        out, _err = capsys.readouterr()
        assert "" == out
        debug_logs = caplog_text()
        for log in expected_logs:
            assert log in debug_logs

    @mock.patch("uaclient.upgrade_lts_contract._is_attached")
    @mock.patch("uaclient.upgrade_lts_contract.system.get_release_info")
    @mock.patch("uaclient.upgrade_lts_contract.system.subp")
    def test_upgrade_cancel_when_past_version_not_supported(
        self,
        m_subp,
        m_get_release_info,
        m_is_attached,
        capsys,
        caplog_text,
        FakeConfig,
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)
        m_get_release_info.return_value = mock.MagicMock(series="groovy")
        m_subp.return_value = ("", "")

        expected_msgs = [
            "Could not find past release for groovy",
        ]
        expected_logs = [
            "Could not find past release for groovy",
            "Check whether to upgrade-lts-contract",
        ]
        with pytest.raises(SystemExit) as execinfo:
            process_contract_delta_after_apt_lock(FakeConfig())

        assert 1 == execinfo.value.code
        assert 1 == m_is_attached.call_count
        assert 1 == m_get_release_info.call_count
        assert 1 == m_subp.call_count
        out, _err = capsys.readouterr()
        assert out == "\n".join(expected_msgs) + "\n"
        debug_logs = caplog_text()
        for log in expected_logs:
            assert log in debug_logs

    @mock.patch("uaclient.upgrade_lts_contract._is_attached")
    @mock.patch("uaclient.upgrade_lts_contract.system.get_release_info")
    @mock.patch("uaclient.upgrade_lts_contract.system.subp")
    @mock.patch(
        "uaclient.upgrade_lts_contract.contract.process_entitlements_delta"
    )
    @mock.patch("uaclient.upgrade_lts_contract.time.sleep")
    def test_upgrade_contract_when_apt_lock_is_held(
        self,
        m_sleep,
        m_process_delta,
        m_subp,
        m_get_release_info,
        m_is_attached,
        capsys,
        caplog_text,
        FakeConfig,
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)
        m_get_release_info.return_value = mock.MagicMock(series="focal")

        m_subp.side_effect = [
            ("apt     146195 root", ""),
            ("apt     146195 root", ""),
            ("apt     146195 root", ""),
            ("", ""),
        ]

        m_process_delta.return_value = True
        m_sleep.return_value = True

        expected_stdout = "\n".join(
            [
                "APT lock is held. Ubuntu Pro configuration will wait until "
                "it is released",
                "Starting upgrade of Ubuntu Pro service configuration",
                "Finished upgrade of Ubuntu Pro service configuration",
                "",
            ]
        )

        with mock.patch(
            "uaclient.upgrade_lts_contract.UAConfig",
            return_value=FakeConfig(),
        ):
            process_contract_delta_after_apt_lock(FakeConfig())

        assert 1 == m_is_attached.call_count
        assert 1 == m_get_release_info.call_count
        assert 4 == m_subp.call_count
        assert 1 == m_process_delta.call_count
        out, _err = capsys.readouterr()
        assert out == expected_stdout
