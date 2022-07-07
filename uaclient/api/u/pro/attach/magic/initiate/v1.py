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


class MagicAttachInitiateResult(DataObject, AdditionalInfo):
    fields = [
        Field("_schema", StringDataValue),
        Field("user_code", StringDataValue),
        Field("token", StringDataValue),
        Field("expires", StringDataValue),
        Field("expires_in", IntDataValue),
    ]

    def __init__(
        self,
        _schema: str,
        user_code: str,
        token: str,
        expires: str,
        expires_in: int,
    ):
        self._schema = _schema
        self.user_code = user_code
        self.token = token
        self.expires = expires
        self.expires_in = expires_in


def initiate(cfg: UAConfig) -> MagicAttachInitiateResult:
    contract = UAContractClient(cfg)
    initiate_resp = contract.new_magic_attach_token()

    return MagicAttachInitiateResult(
        _schema="0.1",
        user_code=initiate_resp["userCode"],
        token=initiate_resp["token"],
        expires=initiate_resp["expires"],
        expires_in=int(initiate_resp["expiresIn"]),
    )


endpoint = APIEndpoint(
    version="v1",
    name="MagicAttachInitiate",
    fn=initiate,
    options_cls=None,
)
