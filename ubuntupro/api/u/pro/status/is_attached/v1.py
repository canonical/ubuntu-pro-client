from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import BoolDataValue, DataObject, Field


class IsAttachedResult(DataObject, AdditionalInfo):
    fields = [
        Field("is_attached", BoolDataValue),
    ]

    def __init__(self, *, is_attached: bool):
        self.is_attached = is_attached


def is_attached() -> IsAttachedResult:
    return _is_attached(UAConfig())


def _is_attached(cfg: UAConfig) -> IsAttachedResult:
    return IsAttachedResult(is_attached=bool(cfg.machine_token))


endpoint = APIEndpoint(
    version="v1",
    name="IsAttached",
    fn=_is_attached,
    options_cls=None,
)
