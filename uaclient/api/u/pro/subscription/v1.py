import logging
from datetime import datetime
from typing import List, Optional

from uaclient import util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.files import machine_token

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class ContractInfo(DataObject, AdditionalInfo):
    fields = [
        Field(
            "created_at",
            DatetimeDataValue,
            doc="Creation date of the contract",
        ),
        Field("id", StringDataValue, doc="Contract id"),
        Field("name", StringDataValue, doc="Contract name"),
        Field(
            "products",
            data_list(StringDataValue),
            doc="List of products included in the contract",
        ),
        Field(
            "tech_support_level",
            StringDataValue,
            doc="Technical support level of the contract",
        ),
        Field(
            "origin",
            StringDataValue,
            required=False,
            doc="Origin of the contract",
        ),
        Field(
            "effective",
            DatetimeDataValue,
            required=False,
            doc="Effective start date of the contract",
        ),
        Field(
            "expires",
            DatetimeDataValue,
            required=False,
            doc="Expiration date of the contract",
        ),
    ]

    def __init__(
        self,
        *,
        created_at: str,
        id: str,
        name: str,
        products: List[str],
        tech_support_level: Optional[str],
        origin: Optional[str],
        effective: Optional[datetime],
        expires: Optional[datetime],
    ):
        self.created_at = created_at
        self.id = id
        self.name = name
        self.products = products
        self.tech_support_level = tech_support_level
        self.origin = origin
        self.effective = effective
        self.expires = expires


class AccountInfo(DataObject, AdditionalInfo):
    fields = [
        Field(
            "created_at", DatetimeDataValue, doc="Creation date of the account"
        ),
        Field(
            "external_account_ids",
            data_list(StringDataValue),
            doc="External account identifiers",
        ),
        Field("id", StringDataValue, doc="Account id"),
        Field("name", StringDataValue, doc="Account name"),
    ]

    def __init__(
        self,
        *,
        created_at: str,
        external_account_ids: List[str],
        id: str,
        name: str,
    ):
        self.created_at = created_at
        self.external_account_ids = external_account_ids
        self.id = id
        self.name = name


class SubscriptionResult(DataObject, AdditionalInfo):
    fields = [
        Field("contract", ContractInfo, doc="Contract Information"),
        Field("account", AccountInfo, doc="Account information"),
        Field("machine_id", StringDataValue, doc="Machine id"),
        Field("activity_id", StringDataValue, doc="Activity id"),
        Field(
            "machine_is_attached",
            BoolDataValue,
            doc="Check if machine is attached to a contract",
        ),
    ]

    def __init__(
        self,
        *,
        contract: ContractInfo,
        account: AccountInfo,
        machine_id: str,
        activity_id: str,
        machine_is_attached: bool
    ):
        self.contract = contract
        self.account = account
        self.machine_id = machine_id
        self.activity_id = activity_id
        self.machine_is_attached = machine_is_attached


def subscription() -> SubscriptionResult:
    return _subscription(UAConfig())


def _subscription(cfg: UAConfig) -> SubscriptionResult:
    """
    Returns the Ubuntu Pro subscription information for the machine.
    """
    if not _is_attached(cfg).is_attached:
        return SubscriptionResult(
            contract=ContractInfo(
                created_at="",
                id="",
                name="",
                products=[],
                tech_support_level=None,
                origin=None,
                effective=None,
                expires=None,
            ),
            account=AccountInfo(
                created_at="",
                external_account_ids=[],
                id="",
                name="",
            ),
            machine_id="",
            activity_id="",
            machine_is_attached=False,
        )

    machine_token_file = machine_token.get_machine_token_file(cfg)
    machineTokenInfo = machine_token_file.machine_token["machineTokenInfo"]

    # Contract Info
    contractInfo = machineTokenInfo["contractInfo"]
    expires = machine_token_file.contract_expiry_datetime
    effective = contractInfo.get("effectiveFrom", None)

    contract = ContractInfo(
        created_at=contractInfo.get("createdAt", ""),
        id=contractInfo["id"],
        name=contractInfo["name"],
        products=contractInfo.get("products", []),
        tech_support_level=machine_token_file.support_level,
        origin=contractInfo.get("origin", None),
        effective=effective,
        expires=expires,
    )

    # Account Info
    account = AccountInfo(
        created_at=machine_token_file.account.get("createdAt", ""),
        external_account_ids=machine_token_file.account.get(
            "externalAccountIDs", []
        ),
        id=machine_token_file.account["id"],
        name=machine_token_file.account["name"],
    )

    # Subscription Result
    activity_id = machine_token_file.activity_id or ""
    machine_is_attached = True
    return SubscriptionResult(
        contract=contract,
        account=account,
        machine_id=machineTokenInfo["machineId"],
        activity_id=activity_id,
        machine_is_attached=machine_is_attached,
    )


endpoint = APIEndpoint(
    version="v1",
    name="Subscription",
    fn=_subscription,
    options_cls=None,
)

_doc = {
    "introduced_in": "35",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.subscription.v1 import subscription
result = subscription()
""",  # noqa: E501
    "result_class": SubscriptionResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.subscription.v1",
    "example_json": """
{
    "attributes": {
        "account": {
            "created_at": "2022-01-01",
            "external_account_ids": [],
            "id": "TestAccountId",
            "name": "TestAccountName"
        },
        "activity_id": "123456789",
        "contract": {
            "created_at": "2022-01-01",
            "effective": None,
            "expires": "2023-01-01",
            "id": "TestContractId",
            "name": "TestContractName",
            "origin": None,
            "products": [],
            "tech_support_level": "n/a"
        },
        "machine_id": "TestMId"
    },
    "meta": {
        "environment_vars": []
    },
    "type": "Subscription"
}
""",
}
