import time

from uaclient import exceptions, secret_manager
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
        Field(
            "magic_token",
            StringDataValue,
            doc="The Token provided by the initiate endpoint.",
        ),
    ]

    def __init__(self, magic_token: str):
        self.magic_token = magic_token


class MagicAttachWaitResult(DataObject, AdditionalInfo):
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
            doc="The same Magic Token that was sent as an argument",
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
        Field(
            "contract_id",
            StringDataValue,
            doc="ID of the contract the machine will be attached to",
        ),
        Field(
            "contract_token",
            StringDataValue,
            doc="The contract Token to attach the machine",
        ),
    ]

    def __init__(
        self,
        user_code: str,
        token: str,
        expires: str,
        expires_in: int,
        contract_id: str,
        contract_token: str,
    ):
        self.user_code = user_code
        self.token = token
        self.expires = expires
        self.expires_in = expires_in
        self.contract_id = contract_id
        self.contract_token = contract_token


def wait(
    options: MagicAttachWaitOptions,
) -> MagicAttachWaitResult:
    return _wait(options, UAConfig())


def _wait(
    options: MagicAttachWaitOptions, cfg: UAConfig
) -> MagicAttachWaitResult:
    """
    This endpoint polls the contracts service waiting for the user to confirm
    the Magic Attach.
    """
    contract = UAContractClient(cfg)

    num_attempts = 0
    num_connection_errors = 0
    wait_time = 10

    secret_manager.secrets.add_secret(options.magic_token)
    while num_attempts < MAXIMUM_ATTEMPTS:
        wait_resp = None

        try:
            wait_resp = contract.get_magic_attach_token_info(
                magic_token=options.magic_token
            )
            num_connection_errors = 0
        except exceptions.MagicAttachTokenError:
            break
        # If the server is unavailable we will bump the wait
        # time. We will return to the normal amount if we can
        # successfully reach the server and we verify that
        # the contractToken information is still not being
        # returned
        except exceptions.MagicAttachUnavailable:
            wait_time = 30
        # If we have a flaky connectivity error, this part of the code
        # will make sure that we try at least three more times before
        # raising a ConnectivityError.
        except exceptions.ConnectivityError as e:
            if num_connection_errors < 3:
                num_connection_errors += 1
            else:
                raise e

        if wait_resp and wait_resp.get("contractToken") is not None:
            return MagicAttachWaitResult(
                user_code=wait_resp["userCode"],
                token=wait_resp["token"],
                expires=wait_resp["expires"],
                expires_in=int(wait_resp["expiresIn"]),
                contract_id=wait_resp["contractID"],
                contract_token=wait_resp["contractToken"],
            )
        elif wait_resp:
            wait_time = 10

        time.sleep(wait_time)
        num_attempts += 1

    raise exceptions.MagicAttachTokenError()


endpoint = APIEndpoint(
    version="v1",
    name="MagicAttachWait",
    fn=_wait,
    options_cls=MagicAttachWaitOptions,
)

_doc = {
    "introduced_in": "27.11",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.attach.magic.wait.v1 import MagicAttachWaitOptions, wait

options = MagicAttachWaitOptions(magic_token="<magic_token>")
result = wait(options)
""",  # noqa: E501
    "result_class": MagicAttachWaitResult,
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
            exceptions.MagicAttachTokenError,
            "Raised when an invalid/expired Token is sent.",
        ),
        (
            exceptions.MagicAttachUnavailable,
            (
                "Raised if the Magic Attach service is busy or unavailable at"
                " the moment."
            ),
        ),
    ],
    "example_cli": "pro api u.pro.attach.magic.wait.v1 --args magic_token=<magic_token>",  # noqa: E501
    "example_json": """
{
    "user_code":"<UI_code>",
    "token":"<magic_token>",
    "expires": "<yyyy-MM-dd>T<HH:mm:ss>.<TZ>",
    "expires_in": 500,
    "contract_id": "<Contract-ID>",
    "contract_token": "<attach_token>",
}
""",
}
