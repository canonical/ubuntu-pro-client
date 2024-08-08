from uaclient import secret_manager
from uaclient.api import exceptions
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
        Field(
            "user_code",
            StringDataValue,
            doc=(
                "Code the user will see in the UI when confirming the Magic"
                " Attach"
            ),
        ),
        Field(
            "token",
            StringDataValue,
            doc=(
                "Magic Token that can be used in either"
                " `u.pro.attach.magic.revoke.v1`_ or"
                " `u.pro.attach.magic.wait.v1`_"
            ),
        ),
        Field(
            "expires",
            StringDataValue,
            doc="Timestamp of the Magic Attach process expiration",
        ),
        Field(
            "expires_in",
            IntDataValue,
            doc="Seconds before the Magic Attach process expires",
        ),
    ]

    def __init__(
        self,
        user_code: str,
        token: str,
        expires: str,
        expires_in: int,
    ):
        self.user_code = user_code
        self.token = token
        self.expires = expires
        self.expires_in = expires_in


def initiate() -> MagicAttachInitiateResult:
    return _initiate(UAConfig())


def _initiate(cfg: UAConfig) -> MagicAttachInitiateResult:
    """
    This endpoint initiates the Magic Attach flow, retrieving the User Code to
    confirm the operation and the Token used to proceed.
    """
    contract = UAContractClient(cfg)
    initiate_resp = contract.new_magic_attach_token()
    secret_manager.secrets.add_secret(initiate_resp["token"])
    secret_manager.secrets.add_secret(initiate_resp["userCode"])
    return MagicAttachInitiateResult(
        user_code=initiate_resp["userCode"],
        token=initiate_resp["token"],
        expires=initiate_resp["expires"],
        expires_in=int(initiate_resp["expiresIn"]),
    )


endpoint = APIEndpoint(
    version="v1",
    name="MagicAttachInitiate",
    fn=_initiate,
    options_cls=None,
)

_doc = {
    "introduced_in": "27.11",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.attach.magic.initiate.v1 import initiate

result = initiate()
""",
    "result_class": MagicAttachInitiateResult,
    "exceptions": [
        (
            exceptions.ConnectivityError,
            (
                "Raised if it is not possible to connect to the contracts"
                " service."
            ),
        ),
        (
            exceptions.ContractAPIError,
            (
                "Raised if there is an unexpected error in the contracts"
                " service interaction."
            ),
        ),
        (
            exceptions.MagicAttachUnavailable,
            (
                "Raised if the Magic Attach service is busy or unavailable at"
                " the moment."
            ),
        ),
    ],
    "example_cli": "pro api u.pro.attach.magic.initiate.v1",
    "example_json": """
{
    "user_code":"<UI_code>",
    "token":"<magic_token>",
    "expires": "<yyyy-MM-dd>T<HH:mm:ss>.<TZ>",
    "expires_in": 600
}
""",
}
