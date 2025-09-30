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
