import logging

import mock
import pytest

from uaclient.files.notices import Notice
from uaclient.timer.update_contract_info import (
    update_contract_info,
    validate_release_series,
)

M_PATH = "uaclient.timer.update_contract_info."


@mock.patch(M_PATH + "contract.is_contract_changed", return_value=False)
class TestUpdateContractInfo:
    @pytest.mark.parametrize(
        "contract_changed,is_attached",
        (
            (False, True),
            (True, False),
            (True, True),
            (False, False),
        ),
    )
    @mock.patch(M_PATH + "notices", autospec=True)
    def test_is_contract_changed(
        self,
        m_notices,
        m_contract_changed,
        contract_changed,
        is_attached,
        FakeConfig,
        fake_machine_token_file,
    ):
        m_contract_changed.return_value = contract_changed
        fake_machine_token_file.attached = is_attached
        update_contract_info(cfg=FakeConfig())

        if is_attached:
            if contract_changed:
                assert [
                    mock.call(
                        Notice.CONTRACT_REFRESH_WARNING,
                    )
                ] == m_notices.add.call_args_list
            else:
                assert [
                    mock.call(
                        Notice.CONTRACT_REFRESH_WARNING,
                    )
                ] not in m_notices.add.call_args_list
                assert [
                    mock.call(Notice.CONTRACT_REFRESH_WARNING)
                ] in m_notices.remove.call_args_list
        else:
            assert m_contract_changed.call_count == 0

    @pytest.mark.parametrize(
        "contract_changed",
        (
            False,
            True,
            Exception("Error checking contract info"),
        ),
    )
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch(M_PATH + "notices", autospec=True)
    def test_contract_failure(
        self,
        m_notices,
        m_contract_changed,
        contract_changed,
        caplog_text,
        FakeConfig,
        fake_machine_token_file,
    ):
        m_contract_changed.side_effect = (contract_changed,)
        m_notices.add.side_effect = Exception("Error checking contract info")
        m_notices.remove.side_effect = Exception(
            "Error checking contract info"
        )
        fake_machine_token_file.attached = True

        assert False is update_contract_info(cfg=FakeConfig())
        assert (
            "Failed to check for change in machine contract."
            " Reason: Error checking contract info\n"
        ) in caplog_text()


class TestValidateReleaseSeries:
    @pytest.mark.parametrize("allowed_series", (None, "bionic", "jammy"))
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="jammy"),
    )
    @mock.patch("uaclient.system.get_distro_info")
    @mock.patch(M_PATH + "detach")
    @mock.patch(
        M_PATH + "_is_attached",
        return_value=mock.MagicMock(is_attached=True),
    )
    def test_validate_release_series(
        self,
        m_is_attached,
        m_detach,
        m_get_distro_info,
        m_get_release_info,
        allowed_series,
        FakeConfig,
        fake_machine_token_file,
    ):
        fake_machine_token_file._entitlements = {
            "support": {
                "entitlement": {"affordances": {"onlySeries": allowed_series}}
            }
        }
        m_get_distro_info.side_effect = [
            mock.MagicMock(
                release="20.04",
                series_codename="Bionic Beaver",
                series="bionic",
            ),
            mock.MagicMock(
                release="22.04",
                series_codename="Jammy Jellyfish",
                series="jammy",
            ),
        ]
        validate_release_series(cfg=FakeConfig())
        if allowed_series:
            if allowed_series != "jammy":
                assert m_get_distro_info.call_count == 1
                assert m_detach.call_count == 1
        else:
            assert m_get_distro_info.call_count == 0
            assert m_detach.call_count == 0
