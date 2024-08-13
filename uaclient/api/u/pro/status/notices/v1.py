import logging
from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.files.notices import NoticesManager

LOG = logging.getLogger("ubuntupro.lib.auto_attach")


class NoticeInfo(DataObject):
    fields = [
        Field("order_id", StringDataValue, doc="Notice order id"),
        Field(
            "message",
            StringDataValue,
            doc="Message displayed by the notice",
        ),
        Field("label", StringDataValue, doc="Notice label"),
    ]

    def __init__(self, order_id: str, message: str, label: str):
        self.order_id = order_id
        self.message = message
        self.label = label


class NoticeListResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "notices",
            data_list(NoticeInfo),
            doc="A list of currently saved notices",
        ),
    ]

    def __init__(self, notices: List[NoticeInfo]):
        self.notices = notices


def notices() -> NoticeListResult:
    return _notices(cfg=UAConfig())


def _notices(cfg: UAConfig) -> NoticeListResult:
    return NoticeListResult(
        notices=[
            NoticeInfo(
                order_id=n.order_id,
                label=n.label,
                message=n.message,
            )
            for n in NoticesManager().get_active_notices()
        ]
    )


endpoint = APIEndpoint(
    version="v1",
    name="NoticeList",
    fn=_notices,
    options_cls=None,
)

_doc = {
    "introduced_in": "35",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.status.notices.v1 import notice_list

result = notices()
""",  # noqa: E501
    "result_class": NoticeListResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.status.notices.v1",
    "example_json": """
{
    "attributes": {
      "notices": [
        {
          "label": "contract_expired",
          "message": "Your Ubuntu Pro subscription has EXPIRED*\nRenew your subscription at https://ubuntu.com/pro/dashboard", # noqa: E501
          "order_id": "5"
        },
        {
          "label": "limited_to_release",
          "message": "Limited to release: Ubuntu 22.04 LTS (Jammy Jellyfish).",
          "order_id": "80"
        }
      ]
    },
    "meta": {
      "environment_vars": []
    },
    "type": "NoticesList"
}
""",
}
