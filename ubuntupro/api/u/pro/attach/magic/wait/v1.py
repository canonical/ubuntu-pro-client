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
        Field("user_code", StringDataValue),
        Field("token", StringDataValue),
        Field("expires", StringDataValue),
        Field("expires_in", IntDataValue),
        Field("contract_id", StringDataValue),
        Field("contract_token", StringDataValue),
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
    contract = UAContractClient(cfg)

    num_attempts = 0
    num_connection_errors = 0
    wait_time = 10

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
