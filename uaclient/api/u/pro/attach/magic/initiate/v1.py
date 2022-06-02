from uaclient.config import UAConfig
from uaclient.contract import UAContractClient
from uaclient.data_types import DataObject, Field, StringDataValue


class MagicAttachInitiateResult(DataObject):
    fields = [
        Field("_schema", StringDataValue),
        Field("confirmation_code", StringDataValue),
        Field("token", StringDataValue),
        Field("expires", StringDataValue),
        Field("user_email", StringDataValue),
    ]

    def __init__(
        self,
        _schema: str,
        confirmation_code: str,
        token: str,
        expires: str,
        user_email: str,
    ):
        self._schema = _schema
        self.confirmation_code = confirmation_code
        self.token = token
        self.expires = expires
        self.user_email = user_email


def initiate(email: str, cfg: UAConfig = None) -> MagicAttachInitiateResult:
    if cfg is None:
        cfg = UAConfig()

    contract = UAContractClient(cfg)
    initiate_resp = contract.new_magic_attach_token(email)

    return MagicAttachInitiateResult(
        _schema="0.1",
        confirmation_code=initiate_resp["confirmationCode"],
        token=initiate_resp["token"],
        expires=initiate_resp["expires"],
        user_email=initiate_resp["userEmail"],
    )
