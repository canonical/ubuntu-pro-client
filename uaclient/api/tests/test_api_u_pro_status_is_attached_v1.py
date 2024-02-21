import datetime

import pytest

from uaclient.api.u.pro.status.is_attached.v1 import (
    ContractExpiryStatus,
    _is_attached,
)


class TestGetContractExpiryStatus:
    @pytest.mark.parametrize(
        "contract_remaining_days,expected_status",
        (
            (21, ContractExpiryStatus.ACTIVE),
            (20, ContractExpiryStatus.ACTIVE_EXPIRED_SOON),
            (-1, ContractExpiryStatus.EXPIRED_GRACE_PERIOD),
            (-20, ContractExpiryStatus.EXPIRED),
        ),
    )
    def test_contract_expiry_status_based_on_remaining_days(
        self, contract_remaining_days, expected_status, FakeConfig
    ):
        """Return a tuple of ContractExpiryStatus and remaining_days"""
        now = datetime.datetime.utcnow()
        expire_date = now + datetime.timedelta(days=contract_remaining_days)
        cfg = FakeConfig.for_attached_machine()
        m_token = cfg.machine_token
        m_token["machineTokenInfo"]["contractInfo"][
            "effectiveTo"
        ] = expire_date

        is_attached_info = _is_attached(cfg)
        assert is_attached_info.is_attached
        assert expected_status.value == is_attached_info.contract_status
        assert (
            contract_remaining_days == is_attached_info.contract_remaining_days
        )
