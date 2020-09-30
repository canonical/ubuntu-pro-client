import contextlib
import io
import mock
import pytest

from lib.upgrade_lts_contract import process_contract_delta_after_apt_lock


class TestUpgradeLTSContract:
    @mock.patch("lib.upgrade_lts_contract.parse_os_release")
    @mock.patch("lib.upgrade_lts_contract.subp")
    def test_upgrade_abort_when_upgrading_to_trusty(self, m_subp, m_parse_os):
        m_parse_os.return_value = {"VERSION_ID": "14.04"}

        m_subp.return_value = ("", "")

        expected_msg = "\n".join(
            [
                "Starting upgrade-lts-contract.",
                "Unable to execute upgrade-lts-contract.py on trusty",
            ]
        )
        fake_stdout = io.StringIO()
        with pytest.raises(SystemExit) as execinfo:
            with contextlib.redirect_stdout(fake_stdout):
                process_contract_delta_after_apt_lock()

        assert 1 == execinfo.value.code
        assert expected_msg == fake_stdout.getvalue().strip()
        assert 1 == m_parse_os.call_count
        assert 1 == m_subp.call_count

    @mock.patch("lib.upgrade_lts_contract.parse_os_release")
    @mock.patch("lib.upgrade_lts_contract.subp")
    @mock.patch("lib.upgrade_lts_contract.process_entitlements_delta")
    @mock.patch("lib.upgrade_lts_contract.time.sleep")
    def test_upgrade_contract_when_apt_lock_is_held(
        self, m_sleep, m_process_delta, m_subp, m_parse_os
    ):
        m_parse_os.return_value = {"VERSION_ID": "20.04"}

        m_subp.side_effect = [
            ("apt     146195 root", ""),
            ("apt     146195 root", ""),
            ("apt     146195 root", ""),
            ("", ""),
        ]

        m_process_delta.return_value = True
        m_sleep.return_value = True

        base_msg = "".join(
            [
                "Starting upgrade-lts-contract.",
                " Retrying every 10 seconds waiting on released apt lock",
            ]
        )

        expected_msg = "\n".join(
            [
                base_msg,
                "upgrade-lts-contract processing contract deltas: {}".format(
                    "bionic -> focal"
                ),
                "upgrade-lts-contract succeeded after 3 retries",
            ]
        )
        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            process_contract_delta_after_apt_lock()

        assert expected_msg == fake_stdout.getvalue().strip()
        assert 1 == m_parse_os.call_count
        assert 4 == m_subp.call_count
        assert 1 == m_process_delta.call_count
