from typing import Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.files.state_files import apt_news_raw_file


class CurrentNewsResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "current_news",
            StringDataValue,
            required=False,
            doc=(
                "The current APT News to be displayed for the system. This"
                " could be a str with up to three lines (i.e. up to two"
                " ``\\n`` characters). If there is no APT News to be"
                " displayed, this will be ``None``."
            ),
        ),
    ]

    def __init__(self, *, current_news: Optional[str]):
        self.current_news = current_news


def current_news() -> CurrentNewsResult:
    return _current_news(UAConfig())


def _current_news(cfg: UAConfig) -> CurrentNewsResult:
    """
    This endpoint returns the current APT News that gets displayed in
    `apt upgrade`.
    """
    return CurrentNewsResult(current_news=apt_news_raw_file.read())


endpoint = APIEndpoint(
    version="v1",
    name="CurrentNews",
    fn=_current_news,
    options_cls=None,
)

_doc = {
    "introduced_in": "29",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.apt_news.current_news.v1 import current_news

result = current_news().current_news
""",
    "result_class": CurrentNewsResult,
    "exceptions": [],
    "example_cli": "pro api u.apt_news.current_news.v1",
    "example_json": """
{
    "current_news":"This is a news message.\\nThis is the second line of the message.\\nAnd this is the third line."
}
""",  # noqa: E501
}
