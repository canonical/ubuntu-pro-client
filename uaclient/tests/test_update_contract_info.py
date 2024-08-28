import mock
import pytest

from uaclient.update_contract_info import validate_release_series

M_PATH = "uaclient.update_contract_info."


class TestValidateReleaseSeries:
    @pytest.mark.parametrize("allowed_series", ("bionic", "jammy"))
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
        validate_release_series(cfg=FakeConfig(), only_series=allowed_series)
        if allowed_series:
            if allowed_series != "jammy":
                assert m_get_distro_info.call_count == 1
                assert m_detach.call_count == 1
        else:
            assert m_get_distro_info.call_count == 0
            assert m_detach.call_count == 0
