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
    fields = [
        Field("name", StringDataValue, doc="Name (ID) of the CVE"),
        Field("patched", BoolDataValue, doc="Livepatch has patched the CVE"),
    ]

    def __init__(self, name: str, patched: bool):
        self.name = name
        self.patched = patched


class LivepatchCVEsResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "fixed_cves",
            data_list(LivepatchCVEObject),
            doc="List of Livepatch patches for the given system",
        ),
    ]

    def __init__(
        self,
        fixed_cves: List[LivepatchCVEObject],
    ):
        self.fixed_cves = fixed_cves


def livepatch_cves() -> LivepatchCVEsResult:
    return _livepatch_cves(UAConfig())


def _livepatch_cves(cfg: UAConfig) -> LivepatchCVEsResult:
    """
    This endpoint lists Livepatch patches for the currently-running kernel.
    """
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

_doc = {
    "introduced_in": "27.12",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.security.status.livepatch_cves.v1 import livepatch_cves

result = livepatch_cves()
""",  # noqa: E501
    "result_class": LivepatchCVEsResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.security.status.livepatch_cves.v1",
    "example_json": """
{
    "fixed_cves":[
        {
            "name": "<CVE Name>",
            "patched": true
        },
        {
            "name": "<Other CVE Name>",
            "patched": false
        },
    ]
}
""",
}
