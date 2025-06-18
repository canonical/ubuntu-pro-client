from uaclient import config, contract, system, util
from uaclient.api import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.data_types import (
    DataObject,
    DatetimeDataValue,
    Field,
    StringDataValue,
)
from uaclient.files import machine_token


class GetGuestTokenResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "guest_token",
            StringDataValue,
            doc="The guest token",
        ),
        Field(
            "id",
            StringDataValue,
            doc="The ID of the guest token",
        ),
        Field(
            "expires",
            DatetimeDataValue,
            doc="The expiration time of the guest token",
        ),
    ]

    def __init__(
        self,
        guest_token: str,
        id: str,
        expires: str,
    ):
        self.guest_token = guest_token
        self.id = id
        self.expires = expires


def get_guest_token() -> GetGuestTokenResult:
    return _get_guest_token(config.UAConfig())


def _get_guest_token(
    cfg: config.UAConfig,
) -> GetGuestTokenResult:
    """
    This endpoint fetches a guest token from the backend.
    """
    if not util.we_are_currently_root():
        raise exceptions.NonRootUserError()
    if not _is_attached(cfg).is_attached:
        raise exceptions.UnattachedError()
    machine_token_file = machine_token.get_machine_token_file(cfg)
    machine_token_dict = machine_token_file.machine_token
    contract_id = machine_token_file.contract_id
    if machine_token_dict is None or contract_id is None:
        # mypy doesn't know that these will never be None if we're attached
        # and root
        raise exceptions.UnattachedError()
    machine_token_str = machine_token_dict["machineToken"]
    machine_id = system.get_machine_id(cfg)
    contract_client = contract.UAContractClient(cfg)
    guest_token = contract_client.get_guest_token(
        machine_token=machine_token_str,
        contract_id=contract_id,
        machine_id=machine_id,
    )
    return GetGuestTokenResult(
        guest_token=guest_token["guestToken"],
        id=guest_token["id"],
        expires=guest_token["expires"],
    )


endpoint = APIEndpoint(
    version="v1",
    name="GetGuestToken",
    fn=_get_guest_token,
    options_cls=None,
)

_doc = {
    "introduced_in": "35",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.attach.guest_token.get_guest_token.v1 import get_guest_token
get_guest_token()
""",  # noqa: E501
    "result_class": GetGuestTokenResult,
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
            exceptions.NonRootUserError,
            ("Raised if a non-root user executes this endpoint."),
        ),
        (exceptions.UnattachedError, "Raised if the machine is not attached"),
        (
            exceptions.FeatureNotSupportedOldTokenError,
            ("Raised if the machine needs to be re-attached first."),
        ),
    ],
    "example_cli": "pro api u.pro.attach.guest_token.get_guest_token.v1",
    "example_json": """
{
    "guest_token": "...",
    "id": "...",
    "expires": "..."
}
""",
}
