"""
Schema v.1: consolidate account and contract keys.

This schema version is incompatible with previous status.json schema because:
 - account key is now a dict instead of string to collect related id,
   external_account_ids and name under a single object
 - subscription-id and subscription keys are dropped

General notes:

   We will increment a schema version for incompatible changes:
    - changing the value type for existing keys
    - dropping deprecated keys

   Each schema patch file will:
    - be named status_<schema_version>.py  # schema_version is a float
    - contain up() and down() functions to adapt existing status values to the
      desired incremental or decremental schema version.
    - the functions up and down will return the updated schema dict
"""
import copy
import re

from uaclient.config import UAConfig
from uaclient import version

from typing import Any, Dict

NEW_KEYS = (
    "contract",
    "config",
    "config_path",
    "effective",
    "execution_details",
    "execution_status",
    "machine_id",
    "version",
)
DROPPED_KEYS = (
    "account-id",
    "configStatus",
    "configStatusDetails",
    "subscription",
    "subscription-id",
    "techSupportLevel",
)
CHANGED_KEYS = ("account",)  # keys where the value type has changed

PATCH_VERSION = float(re.sub(r".*status_([.\d]+).py", r"\1", __file__))


def up(cfg: UAConfig, current_status: Dict) -> Dict:
    """Patch current_status upgrading from previous schema version status dict.

    :return: Dict of updated config
    """
    new_status = copy.deepcopy(current_status)
    # Asserts to make sure we are looking at the expected current_status
    for key in DROPPED_KEYS + CHANGED_KEYS:
        assert (
            key in current_status
        ), "Missing expected key: {}. Cannot patch status.json".format(key)
        new_status.pop(key, None)
    new_status["_schema_version"] = PATCH_VERSION
    new_status["version"] = version.get_version(features=self.features)

    # Migrated key names
    new_status["execution_status"] = current_status["configStatus"]
    new_status["execution_details"] = current_status["configStatusDetails"]

    if current_status["attached"]:
        token = cfg.machine_token["machineTokenInfo"]
        new_status["machine_id"] = token["machineId"]
        account_info = token["accountInfo"]
        contract_info = token["contractInfo"]
        external_account_ids = []
        for external_account in account_info.get("externalAccountIds", []):
            external_account_ids.append(
                {
                    "ids": external_account.get("IDS", []),
                    "origin": external_account.get("Origin", ""),
                }
            )

        new_status["account"] = {
            "created_at": account_info.get("createdAt", ""),
            "external_account_ids": external_account_ids,
            "name": current_status["account"],
            "id": current_status["account-id"],
        }
        new_status["contract"] = {
            "created_at": contract_info.get("createdAt", ""),
            "products": contract_info.get("products", []),
            "tech_support_level": current_status["techSupportLevel"],
            "name": current_status["subscription"],
            "id": current_status["subscription-id"],
        }
    else:
        new_status.update(
            {
                "contract": {
                    "id": "",
                    "name": "",
                    "created_at": "",
                    "products": [],
                    "tech_support_level": "n/a",
                },
                "account": {
                    "name": "",
                    "id": "",
                    "created_at": "",
                    "external_account_ids": [],
                },
            }
        )
    return new_status


def down(_cfg: UAConfig, current_status: Dict[str, Any]) -> Dict[str, Any]:
    """Downgrade to previous status schema version.

    :return: Dict of downgraded status schema version.
    """
    new_status = copy.deepcopy(current_status)
    schema_ver = float(current_status["_schema_version"])
    assert (
        PATCH_VERSION == schema_ver
    ), "Found unexpected schema version {} cannot downgrade to {}".format(
        schema_ver, PATCH_VERSION
    )
    # Asserts to make sure we are looking at the expected current_status
    for key in NEW_KEYS + CHANGED_KEYS:
        assert (
            key in current_status
        ), "Missing expected key: {} cannot patch status.json.".format(key)

    contract_info = new_status.pop("contract")
    account_info = new_status.pop("account")

    for drop_key in NEW_KEYS:
        if drop_key != "contract":  # Since we already pop'd contract above
            new_status.pop(drop_key, None)
    new_status["techsupportLevel"] = contract_info["tech_support_level"]
    new_status["account"] = account_info["name"]
    new_status["account-id"] = account_info["id"]
    new_status["subscription"] = contract_info["name"]
    new_status["subscription-id"] = contract_info["id"]
    new_status["_schema_version"] = "0.1"
    return new_status
