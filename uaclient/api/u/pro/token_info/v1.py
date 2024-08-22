import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uaclient import exceptions, util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.contract import get_available_resources, get_contract_information
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.defaults import ATTACH_FAIL_DATE_FORMAT
from uaclient.entitlements import entitlement_factory

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class TokenInfoOptions(DataObject):
    fields = [
        Field(
            "token", StringDataValue, doc="Token to be used for the request"
        ),
    ]

    def __init__(self, token: str):
        self.token = token


class AccountInfo(DataObject):
    fields = [
        Field("id", StringDataValue),
        Field("name", StringDataValue),
    ]

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class ContractInfo(DataObject):
    fields = [
        Field("id", StringDataValue),
        Field("name", StringDataValue),
        Field("effective", DatetimeDataValue),
        Field("expires", DatetimeDataValue),
    ]

    def __init__(
        self,
        id: str,
        name: str,
        effective: Optional[datetime],
        expires: Optional[datetime],
    ):
        self.id = id
        self.name = name
        self.effective = effective
        self.expires = expires


class ServiceInfo(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("description", StringDataValue),
        Field("entitled", BoolDataValue),
        Field("auto_enabled", BoolDataValue),
        Field("available", BoolDataValue),
    ]

    def __init__(
        self,
        available: bool,
        description: str,
        entitled: bool,
        name: str,
        auto_enabled: bool,
    ):
        self.available = available
        self.description = description
        self.entitled = entitled
        self.name = name
        self.auto_enabled = auto_enabled


class TokenInfoResult(DataObject, AdditionalInfo):
    fields = [
        Field("account", AccountInfo),
        Field("contract", ContractInfo),
        Field("services", data_list(ServiceInfo)),
    ]

    def __init__(
        self,
        account: AccountInfo,
        contract: ContractInfo,
        services: List[ServiceInfo],
    ):
        self.account = account
        self.contract = contract
        self.services = services


def _get_application_entitlement_information(
    entitlements: List[Dict[str, Any]], entitlement_name: str
) -> Dict[str, Any]:
    """Extract information from the entitlements array."""
    for entitlement in entitlements:
        if entitlement.get("type") == entitlement_name:
            return {
                "entitled": entitlement.get("entitled"),
                "auto_enabled": (
                    entitlement.get("obligations", {}).get("enableByDefault")
                ),
            }
    return {"entitled": False, "auto_enabled": False}


def get_token_info(options: TokenInfoOptions) -> TokenInfoResult:
    return _get_token_info(options=options, cfg=UAConfig())


def _get_token_info(
    options: TokenInfoOptions, cfg: UAConfig
) -> TokenInfoResult:
    token = options.token
    try:
        contract_information = get_contract_information(cfg, token)
    except exceptions.ContractAPIError as e:
        if e.code == 401:
            raise exceptions.AttachInvalidTokenError()
        raise e

    contract_info = contract_information.get("contractInfo", {})

    account_info = contract_information.get("accountInfo", {})
    account = AccountInfo(
        id=account_info.get("id", ""), name=account_info.get("name", "")
    )

    # Check contract expiration
    now = datetime.now(timezone.utc)
    if contract_info.get("effectiveTo"):
        expiration_datetime = contract_info.get("effectiveTo")
        delta = expiration_datetime - now
        if delta.total_seconds() <= 0:
            raise exceptions.TokenForbiddenExpired(
                contract_id=contract_info.get("id", ""),
                date=expiration_datetime.strftime(ATTACH_FAIL_DATE_FORMAT),
                contract_expiry_date=expiration_datetime.strftime("%m-%d-%Y"),
            )
    if contract_info.get("effectiveFrom"):
        effective_datetime = contract_info.get("effectiveFrom")
        delta = now - effective_datetime
        if delta.total_seconds() <= 0:
            raise exceptions.TokenForbiddenNotYet(
                contract_id=contract_info.get("id", ""),
                date=effective_datetime.strftime(ATTACH_FAIL_DATE_FORMAT),
                contract_effective_date=effective_datetime.strftime(
                    "%m-%d-%Y"
                ),
            )

    contract = ContractInfo(
        id=contract_info.get("id", ""),
        name=contract_info.get("name", ""),
        effective=contract_info.get("effectiveFrom", None),
        expires=contract_info.get("effectiveTo", None),
    )

    services = []
    resources = get_available_resources(cfg)
    inapplicable_resources = {
        resource["name"]: resource.get("description")
        for resource in sorted(resources, key=lambda x: x.get("name", ""))
        if not resource.get("available")
    }
    entitlements = contract_info.get("resourceEntitlements", [])
    for resource in resources:
        entitlement_name = resource.get("name", "")
        try:
            ent = entitlement_factory(cfg=cfg, name=entitlement_name)
        except exceptions.EntitlementNotFoundError:
            continue
        entitlement_information = _get_application_entitlement_information(
            entitlements, entitlement_name
        )
        services.append(
            ServiceInfo(
                name=resource.get("presentedAs", ent.name),
                description=ent.description,
                entitled=entitlement_information["entitled"],
                auto_enabled=entitlement_information["auto_enabled"],
                available=(
                    True if ent.name not in inapplicable_resources else False
                ),
            )
        )
    services.sort(key=lambda x: x.name)

    return TokenInfoResult(
        account=account,
        contract=contract,
        services=services,
    )


endpoint = APIEndpoint(
    version="v1",
    name="TokenInfo",
    fn=_get_token_info,
    options_cls=TokenInfoOptions,
)

_doc = {
    "introduced_in": "35",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.token_info.v1 import get_token_info, TokenInfoOptions
result = get_token_info(TokenInfoOptions(token="contract_token"))
""",
    "result_class": TokenInfoResult,
    "exceptions": [
        (
            exceptions.AttachInvalidTokenError,
            "When an invalid token is passed as an argument",
        ),
        (
            exceptions.TokenForbiddenExpired,
            "When the contract has expired",
        ),
        (
            exceptions.TokenForbiddenNotYet,
            "When the contract is not yet effective",
        ),
    ],
    "example_cli": "pro api u.pro.token_info.v1 --args token=CONTRACT_TOKEN",
    "example_json": """
    {
      "attributes": {
        "account": {
          "id": "accountID",
          "name": "accountName"
        },
        "contract": {
          "id": "contractID",
          "name": "contractName"
        },
        "services": {
          "services": [
            {
              "auto_enabled": true,
              "available": false,
              "description": "Scalable Android in the cloud",
              "entitled": true,
              "name": "anbox-cloud"
            },
            {
              "auto_enabled": false,
              "available": true,
              "description": "Common Criteria EAL2 Provisioning Packages",
              "entitled": true,
              "name": "cc-eal"
            },
            {
              "auto_enabled": false,
              "available": true,
              "description": "Security compliance and audit tools",
              "entitled": true,
              "name": "cis"
            },
            ...
            {
              "auto_enabled": false,
              "available": true,
              "description": "All Updates for the Robot Operating System",
              "entitled": true,
              "name": "ros-updates"
            }
          ]
        },
      },
      "meta": {
        "environment_vars": []
      },
      "type": "TokenInfo"
    }
""",
}
