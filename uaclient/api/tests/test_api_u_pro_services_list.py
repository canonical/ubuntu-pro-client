import mock
import pytest

from uaclient.api.u.pro.services.list.v1 import (
    ServiceInfo,
    ServiceListResult,
    _list,
)

M_PATH = "uaclient.api.u.pro.services.list.v1."

RESPONSE_AVAILABLE_SERVICES = [
    {"name": "livepatch", "available": True},
    {"name": "esm-apps", "available": True},
]


class TestServiceList:
    @pytest.mark.parametrize(
        ["attached_side_effect", "expected_ret"],
        [
            (
                [mock.MagicMock(is_attached=True)],
                ServiceListResult(
                    services=[
                        ServiceInfo(
                            name="esm-apps",
                            desc="Expanded Security Maintenance for Applications",  # noqa: E501
                            available=True,
                            entitled=False,
                        ),
                        ServiceInfo(
                            name="livepatch",
                            desc="Canonical Livepatch service",
                            available=True,
                            entitled=False,
                        ),
                    ]
                ),
            ),
            (
                [mock.MagicMock(is_attached=False)],
                ServiceListResult(
                    services=[
                        ServiceInfo(
                            name="esm-apps",
                            desc="Expanded Security Maintenance for Applications",  # noqa: E501
                            available=True,
                            entitled=None,
                        ),
                        ServiceInfo(
                            name="livepatch",
                            desc="Canonical Livepatch service",
                            available=True,
                            entitled=None,
                        ),
                    ]
                ),
            ),
        ],
    )
    @mock.patch(
        M_PATH + "get_available_resources",
        return_value=RESPONSE_AVAILABLE_SERVICES,
    )
    @mock.patch(M_PATH + "_is_attached")
    def test_service_list(
        self,
        m_is_attached,
        m_available_resources,
        attached_side_effect,
        expected_ret,
        FakeConfig,
        fake_machine_token_file,
    ):
        cfg = FakeConfig()
        fake_machine_token_file.token = {"availableResources": None}
        m_is_attached.side_effect = attached_side_effect
        result = _list(cfg)
        assert result == expected_ret
