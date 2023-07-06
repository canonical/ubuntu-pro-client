from typing import Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.files.state_files import apt_news_raw_file


class CurrentNewsResult(DataObject, AdditionalInfo):
    fields = [
        Field("current_news", StringDataValue, required=False),
    ]

    def __init__(self, *, current_news: Optional[str]):
        self.current_news = current_news


def current_news() -> CurrentNewsResult:
    return _current_news(UAConfig())


def _current_news(cfg: UAConfig) -> CurrentNewsResult:
    return CurrentNewsResult(current_news=apt_news_raw_file.read())


endpoint = APIEndpoint(
    version="v1",
    name="CurrentNews",
    fn=_current_news,
    options_cls=None,
)
