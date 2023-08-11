from typing import Optional

from ubuntupro.api.api import APIEndpoint
from ubuntupro.api.data_types import AdditionalInfo
from ubuntupro.config import UAConfig
from ubuntupro.data_types import DataObject, Field, StringDataValue
from ubuntupro.files.state_files import apt_news_raw_file


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
