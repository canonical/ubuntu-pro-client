from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.security_status import get_livepatch_fixed_cves


class LivepatchCVEObject(DataObject):
    fields = [Field("name", StringDataValue), Field("patched", BoolDataValue)]

    def __init__(self, name: str, patched: bool):
        self.name = name
        self.patched = patched


class LivepatchCVEsResult(DataObject, AdditionalInfo):
    fields = [
        Field("fixed_cves", data_list(LivepatchCVEObject)),
    ]

    def __init__(
        self,
        fixed_cves: List[LivepatchCVEObject],
    ):
        self.fixed_cves = fixed_cves


def livepatch_cves() -> LivepatchCVEsResult:
    return _livepatch_cves(UAConfig())


def _livepatch_cves(cfg: UAConfig) -> LivepatchCVEsResult:
    return LivepatchCVEsResult(
        fixed_cves=[
            LivepatchCVEObject(name=cve["name"], patched=cve["patched"])
            for cve in get_livepatch_fixed_cves()
        ]
    )


endpoint = APIEndpoint(
    version="v1",
    name="LivepatchCVEs",
    fn=_livepatch_cves,
    options_cls=None,
)
