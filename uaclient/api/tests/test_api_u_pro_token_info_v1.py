import copy

import mock
import pytest

from uaclient import exceptions, util
from uaclient.api.u.pro.token_info.v1 import (
    AccountInfo,
    ContractInfo,
    ServiceInfo,
    TokenInfoOptions,
    TokenInfoResult,
    _get_token_info,
)

RESPONSE_CONTRACT_INFO = {
    "accountInfo": {
        "createdAt": util.parse_rfc3339_date("2019-06-14T06:45:50Z"),
        "id": "some_id",
        "name": "Name",
        "type": "paid",
    },
    "contractInfo": {
        "createdAt": util.parse_rfc3339_date("2021-05-21T20:00:53Z"),
        "createdBy": "someone",
        "effectiveTo": util.parse_rfc3339_date("9999-12-31T00:00:00Z"),
        "id": "some_id",
        "name": "Name",
        "products": ["uai-essential-virtual"],
        "resourceEntitlements": [
            {
                "type": "esm-infra",
                "entitled": True,
                "obligations": {"enableByDefault": True},
            },
            {
                "type": "livepatch",
                "entitled": True,
                "obligations": {"enableByDefault": False},
            },
        ],
    },
}

RESPONSE_AVAILABLE_SERVICES = [
    {"name": "livepatch", "available": True},
]


class TestTokenInfo:
    @mock.patch(
        "uaclient.api.u.pro.token_info.v1.get_available_resources",
        return_value=RESPONSE_AVAILABLE_SERVICES,
    )
    @mock.patch(
        "uaclient.api.u.pro.token_info.v1.get_contract_information",
        return_value=RESPONSE_CONTRACT_INFO,
    )
    def test_token_info_output(
        self, m_get_contract_information, m_get_available_resources, FakeConfig
    ):
        cfg = FakeConfig()
        token_info = _get_token_info(
            options=TokenInfoOptions(token="contract_token"), cfg=cfg
        )
        expected_info = TokenInfoResult(
            account=AccountInfo(id="some_id", name="Name"),
            contract=ContractInfo(
                id="some_id",
                name="Name",
                effective=None,
                expires=util.parse_rfc3339_date("9999-12-31T00:00:00Z"),
            ),
            services=[
                ServiceInfo(
                    name="livepatch",
                    description="Canonical Livepatch service",
                    entitled=True,
                    auto_enabled=False,
                    available=True,
                ),
            ],
        )
        assert token_info == expected_info

    @pytest.mark.parametrize(
        "expected_error,expected_err_message,contract_field,date_value",
        (
            (
                exceptions.TokenForbiddenExpired,
                (
                    'Contract "some_id" expired on December 31, 2019\n'
                    "Visit https://ubuntu.com/pro/dashboard to manage "
                    "contract tokens."
                ),
                "effectiveTo",
                util.parse_rfc3339_date("2019-12-31T00:00:00Z"),
            ),
            (
                exceptions.TokenForbiddenNotYet,
                (
                    'Contract "some_id" is not effective until December 31, '
                    "9999\n"
                    "Visit https://ubuntu.com/pro/dashboard to manage "
                    "contract tokens."
                ),
                "effectiveFrom",
                util.parse_rfc3339_date("9999-12-31T00:00:00Z"),
            ),
        ),
    )
    @mock.patch(
        "uaclient.api.u.pro.token_info.v1.get_available_resources",
        return_value=RESPONSE_AVAILABLE_SERVICES,
    )
    @mock.patch("uaclient.api.u.pro.token_info.v1.get_contract_information")
    def test_attach_forbidden_error(
        self,
        m_get_contract_information,
        m_get_available_resources,
        expected_error,
        expected_err_message,
        contract_field,
        date_value,
        capsys,
        FakeConfig,
    ):
        exp_contract = copy.deepcopy(RESPONSE_CONTRACT_INFO)
        exp_contract["contractInfo"][contract_field] = date_value
        m_get_contract_information.return_value = exp_contract
        cfg = FakeConfig()
        try:
            _get_token_info(
                options=TokenInfoOptions(token="contract_token"), cfg=cfg
            )
        except expected_error as e:
            err_message = str(e)
            assert err_message == expected_err_message
