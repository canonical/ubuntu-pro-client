from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.contract import UAContractClient
from uaclient.data_types import DataObject, Field, StringDataValue


class MagicAttachRevokeOptions(DataObject):
    fields = [
        Field("magic_token", StringDataValue),
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
    contract = UAContractClient(cfg)
    contract.revoke_magic_attach_token(options.magic_token)

    return MagicAttachRevokeResult()


endpoint = APIEndpoint(
    version="v1",
    name="MagicAttachRevoke",
    fn=_revoke,
    options_cls=MagicAttachRevokeOptions,
)
