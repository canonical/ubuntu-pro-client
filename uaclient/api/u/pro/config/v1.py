import logging
from typing import Optional

from uaclient import util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UA_CONFIGURABLE_KEYS, UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
)

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class ConfigInfo(DataObject, AdditionalInfo):
    fields = [
        Field("http_proxy", StringDataValue, required=False, doc="HTTP proxy"),
        Field(
            "https_proxy", StringDataValue, required=False, doc="HTTPS proxy"
        ),
        Field(
            "ua_apt_http_proxy",
            StringDataValue,
            required=False,
            doc="Ubuntu Pro APT HTTP proxy",
        ),
        Field(
            "ua_apt_https_proxy",
            StringDataValue,
            required=False,
            doc="Ubuntu Pro APT HTTPS proxy",
        ),
        Field(
            "global_apt_http_proxy",
            StringDataValue,
            required=False,
            doc="Global APT HTTP proxy",
        ),
        Field(
            "global_apt_https_proxy",
            StringDataValue,
            required=False,
            doc="Global APT HTTPS proxy",
        ),
        Field("apt_news", BoolDataValue, required=False, doc="APT news"),
        Field(
            "apt_news_url", StringDataValue, required=False, doc="APT news URL"
        ),
        Field(
            "metering_timer",
            IntDataValue,
            required=False,
            doc="Metering timer",
        ),
        Field(
            "update_messaging_timer",
            IntDataValue,
            required=False,
            doc="Update messaging timer",
        ),
        Field(
            "cli_color",
            BoolDataValue,
            required=False,
            doc="Show colors in the CLI",
        ),
        Field(
            "cli_suggestions",
            BoolDataValue,
            required=False,
            doc="Show suggestions in the CLI",
        ),
    ]

    def __init__(
        self,
        *,
        http_proxy: Optional[str] = None,
        https_proxy: Optional[str] = None,
        ua_apt_http_proxy: Optional[str] = None,
        ua_apt_https_proxy: Optional[str] = None,
        global_apt_http_proxy: Optional[str] = None,
        global_apt_https_proxy: Optional[str] = None,
        update_messaging_timer: Optional[int] = None,
        metering_timer: Optional[int] = None,
        apt_news: Optional[bool] = None,
        apt_news_url: Optional[str] = None,
        cli_color: Optional[bool] = None,
        cli_suggestions: Optional[bool] = None
    ):
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.ua_apt_http_proxy = ua_apt_http_proxy
        self.ua_apt_https_proxy = ua_apt_https_proxy
        self.global_apt_http_proxy = global_apt_http_proxy
        self.global_apt_https_proxy = global_apt_https_proxy
        self.update_messaging_timer = update_messaging_timer
        self.metering_timer = metering_timer
        self.apt_news = apt_news
        self.apt_news_url = apt_news_url
        self.cli_color = cli_color
        self.cli_suggestions = cli_suggestions


def config() -> ConfigInfo:
    return _config(UAConfig())


def _config(cfg: UAConfig) -> ConfigInfo:
    """This endpoint returns the current user configuration"""
    pro_config = {}
    for key in UA_CONFIGURABLE_KEYS:
        if hasattr(cfg, key):
            pro_config[key] = getattr(cfg, key)

    return ConfigInfo.from_dict(pro_config)


endpoint = APIEndpoint(
    version="v1",
    name="Config",
    fn=_config,
    options_cls=None,
)

_doc = {
    "introduced_in": "35",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.config.v1 import config

result = config()
""",  # noqa: E501
    "result_class": ConfigInfo,
    "exceptions": [],
    "example_cli": "pro api u.pro.config.v1",
    "example_json": """
{
    "attributes": {
        "apt_news": true,
        "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
        "global_apt_http_proxy": null,
        "global_apt_https_proxy": null,
        "http_proxy": null,
        "https_proxy": null,
        "metering_timer": 14400,
        "ua_apt_http_proxy": null,
        "ua_apt_https_proxy": null,
        "update_messaging_timer": 21600
    },
    "meta": {
        "environment_vars": []
    },
    "type": "Config"
}
""",
}
