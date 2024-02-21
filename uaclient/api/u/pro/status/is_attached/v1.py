import enum
from typing import Optional, Tuple

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
)
from uaclient.defaults import (
    CONTRACT_EXPIRY_GRACE_PERIOD_DAYS,
    CONTRACT_EXPIRY_PENDING_DAYS,
)


class IsAttachedResult(DataObject, AdditionalInfo):
    fields = [
        Field("is_attached", BoolDataValue),
        Field("contract_status", StringDataValue, False),
        Field("contract_remaining_days", IntDataValue),
        Field("is_attached_and_contract_valid", BoolDataValue),
    ]

    def __init__(
        self,
        *,
        is_attached: bool,
        contract_status: Optional[str],
        contract_remaining_days: int,
        is_attached_and_contract_valid: bool
    ):
        self.is_attached = is_attached
        self.contract_status = contract_status
        self.contract_remaining_days = contract_remaining_days
        self.is_attached_and_contract_valid = is_attached_and_contract_valid


@enum.unique
class ContractExpiryStatus(enum.Enum):
    NONE = None
    ACTIVE = "active"
    ACTIVE_EXPIRED_SOON = "active-soon-to-expire"
    EXPIRED_GRACE_PERIOD = "grace-period"
    EXPIRED = "expired"


def _get_contract_expiry_status(
    cfg: UAConfig,
    is_machine_attached: bool,
) -> Tuple[ContractExpiryStatus, int]:
    """Return a tuple [ContractExpiryStatus, num_days]"""
    if not is_machine_attached:
        return ContractExpiryStatus.NONE, 0

    grace_period = CONTRACT_EXPIRY_GRACE_PERIOD_DAYS
    pending_expiry = CONTRACT_EXPIRY_PENDING_DAYS
    remaining_days = cfg.machine_token_file.contract_remaining_days

    # if unknown assume the worst
    if remaining_days is None:
        return ContractExpiryStatus.EXPIRED, -grace_period

    if 0 <= remaining_days <= pending_expiry:
        return ContractExpiryStatus.ACTIVE_EXPIRED_SOON, remaining_days
    elif -grace_period <= remaining_days < 0:
        return ContractExpiryStatus.EXPIRED_GRACE_PERIOD, remaining_days
    elif remaining_days < -grace_period:
        return ContractExpiryStatus.EXPIRED, remaining_days
    return ContractExpiryStatus.ACTIVE, remaining_days


def is_attached() -> IsAttachedResult:
    return _is_attached(UAConfig())


def _is_attached(cfg: UAConfig) -> IsAttachedResult:
    is_machine_attached = bool(cfg.machine_token)
    contract_status, remaining_days = _get_contract_expiry_status(
        cfg, is_machine_attached
    )
    is_attached_and_contract_valid = True
    if (
        not is_machine_attached
        or contract_status == ContractExpiryStatus.EXPIRED
    ):
        is_attached_and_contract_valid = False

    return IsAttachedResult(
        is_attached=is_machine_attached,
        contract_status=contract_status.value,
        contract_remaining_days=remaining_days,
        is_attached_and_contract_valid=is_attached_and_contract_valid,
    )


endpoint = APIEndpoint(
    version="v1",
    name="IsAttached",
    fn=_is_attached,
    options_cls=None,
)
