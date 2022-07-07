import time

from uaclient import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.contract import UAContractClient
from uaclient.data_types import (
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
)

MAXIMUM_ATTEMPTS = 70


class MagicAttachWaitOptions(DataObject):
    fields = [
        Field("magic_token", StringDataValue),
    ]

    def __init__(self, magic_token: str):
        self.magic_token = magic_token


class MagicAttachWaitResult(DataObject, AdditionalInfo):
    fields = [
        Field("_schema", StringDataValue),
        Field("user_code", StringDataValue),
        Field("token", StringDataValue),
        Field("expires", StringDataValue),
        Field("expires_in", IntDataValue),
        Field("contract_id", StringDataValue),
        Field("contract_token", StringDataValue),
    ]

    def __init__(
        self,
        _schema: str,
        user_code: str,
        token: str,
        expires: str,
        expires_in: int,
        contract_id: str,
        contract_token: str,
    ):
        self._schema = _schema
        self.user_code = user_code
        self.token = token
        self.expires = expires
        self.expires_in = expires_in
        self.contract_id = contract_id
        self.contract_token = contract_token


def wait(
    options: MagicAttachWaitOptions,
    cfg: UAConfig,
) -> MagicAttachWaitResult:
    contract = UAContractClient(cfg)

    num_attempts = 0

    while num_attempts < MAXIMUM_ATTEMPTS:
        try:
            wait_resp = contract.get_magic_attach_token_info(
                magic_token=options.magic_token
            )
        except exceptions.MagicAttachTokenError:
            break

        if wait_resp.get("contractToken") is not None:
            return MagicAttachWaitResult(
                _schema="0.1",
                user_code=wait_resp["userCode"],
                token=wait_resp["token"],
                expires=wait_resp["expires"],
                expires_in=int(wait_resp["expiresIn"]),
                contract_id=wait_resp["contractID"],
                contract_token=wait_resp["contractToken"],
            )

        time.sleep(10)
        num_attempts += 1

    raise exceptions.MagicAttachTokenError()


endpoint = APIEndpoint(
    version="v1",
    name="MagicAttachWait",
    fn=wait,
    options_cls=MagicAttachWaitOptions,
)
