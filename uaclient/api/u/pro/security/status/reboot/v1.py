from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.security_status import get_reboot_status


class RebootStatusResult(DataObject, AdditionalInfo):
    fields = [
        Field("reboot_required", StringDataValue),
    ]

    def __init__(
        self,
        reboot_required: str,
    ):
        self.reboot_required = reboot_required


def reboot_status(cfg: UAConfig) -> RebootStatusResult:
    status = get_reboot_status()
    return RebootStatusResult(reboot_required=status.value)


endpoint = APIEndpoint(
    version="v1",
    name="RebootStatus",
    fn=reboot_status,
    options_cls=None,
)
