from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.security_status import get_reboot_status


class RebootRequiredResult(DataObject, AdditionalInfo):
    fields = [
        Field("reboot_required", StringDataValue),
    ]

    def __init__(
        self,
        reboot_required: str,
    ):
        self.reboot_required = reboot_required


def reboot_required() -> RebootRequiredResult:
    return _reboot_required(UAConfig())


def _reboot_required(cfg: UAConfig) -> RebootRequiredResult:
    status = get_reboot_status()
    return RebootRequiredResult(reboot_required=status.value)


endpoint = APIEndpoint(
    version="v1",
    name="RebootRequired",
    fn=_reboot_required,
    options_cls=None,
)
