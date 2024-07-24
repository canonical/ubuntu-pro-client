from uaclient.api import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.contract import UAContractClient
from uaclient.data_types import DataObject, Field, StringDataValue


class MagicAttachRevokeOptions(DataObject):
    fields = [
        Field(
            "magic_token",
            StringDataValue,
            doc="The Token provided by the initiate endpoint.",
        ),
    ]

    def __init__(self, magic_token):
        self.magic_token = magic_token


class MagicAttachRevokeResult(DataObject, AdditionalInfo):
    pass


def revoke(options: MagicAttachRevokeOptions) -> MagicAttachRevokeResult:
    return _revoke(options, UAConfig())


def _revoke(
    options: MagicAttachRevokeOptions, cfg: UAConfig
) -> MagicAttachRevokeResult:
    """
    This endpoint revokes a Magic Attach Token.
    """
    contract = UAContractClient(cfg)
    contract.revoke_magic_attach_token(options.magic_token)

    return MagicAttachRevokeResult()


endpoint = APIEndpoint(
    version="v1",
    name="MagicAttachRevoke",
    fn=_revoke,
    options_cls=MagicAttachRevokeOptions,
)

_doc = {
    "introduced_in": "27.11",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.attach.magic.revoke.v1 import MagicAttachRevokeOptions, revoke

options = MagicAttachWaitOptions(magic_token="<magic_token>")
result = revoke(options)
""",  # noqa: E501
    "result_class": MagicAttachRevokeResult,
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
            exceptions.MagicAttachTokenAlreadyActivated,
            (
                "Raised when trying to revoke a Token which was already"
                " activated through the UI."
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
    "example_cli": "pro api u.pro.attach.magic.revoke.v1 --args magic_token=<token>",  # noqa: E501
    "example_json": """
{}
""",
}
