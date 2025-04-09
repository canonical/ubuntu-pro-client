import datetime

import mock
import pytest

from uaclient import exceptions
from uaclient.update_contract_info import validate_release_series

M_PATH = "uaclient.update_contract_info."


class TestValidateReleaseSeries:
    @pytest.mark.parametrize(
        "only_series,eol,is_valid",
        (
            ("bionic", datetime.date(2023, 5, 31), False),
            ("jammy", datetime.date(2027, 6, 1), True),
            ("noble", datetime.date(2029, 5, 31), True),
        ),
    )
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
        only_series,
        eol,
        is_valid,
        FakeConfig,
        fake_machine_token_file,
    ):
        fake_machine_token_file._entitlements = {
            "support": {
                "entitlement": {"affordances": {"onlySeries": only_series}}
            }
        }
        m_get_distro_info.side_effect = [
            mock.MagicMock(
                series=only_series,
                eol=eol,
            ),
            mock.MagicMock(
                series="jammy",
                eol=datetime.date(2027, 6, 1),
            ),
        ]
        validate_release_series(cfg=FakeConfig(), only_series=only_series)
        if is_valid:
            assert m_get_distro_info.call_count == 2
            assert m_detach.call_count == 0
        else:
            assert m_get_distro_info.call_count == 2
            assert m_detach.call_count == 1

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
    def test_validate_release_series_not_found(
        self,
        m_is_attached,
        m_detach,
        m_get_distro_info,
        m_get_release_info,
        FakeConfig,
    ):
        m_get_distro_info.side_effect = (
            exceptions.MissingSeriesInDistroInfoFile(series="plucky")
        )
        validate_release_series(cfg=FakeConfig(), only_series="plucky")
        assert m_get_distro_info.call_count == 1
        assert m_detach.call_count == 0
