import copy
import logging
import os
from typing import Optional
from urllib.parse import urlparse

from uaclient import defaults, event_logger, util
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
)
from uaclient.files.data_types import DataObjectFile, DataObjectFileFormat
from uaclient.files.files import UAFile

# Config proxy fields that are visible and configurable
PROXY_FIELDS = [
    "apt_http_proxy",
    "apt_https_proxy",
    "global_apt_http_proxy",
    "global_apt_https_proxy",
    "ua_apt_http_proxy",
    "ua_apt_https_proxy",
    "http_proxy",
    "https_proxy",
]


class UserConfigData(DataObject):
    fields = [
        Field("apt_http_proxy", StringDataValue, required=False),
        Field("apt_https_proxy", StringDataValue, required=False),
        Field("global_apt_http_proxy", StringDataValue, required=False),
        Field("global_apt_https_proxy", StringDataValue, required=False),
        Field("ua_apt_http_proxy", StringDataValue, required=False),
        Field("ua_apt_https_proxy", StringDataValue, required=False),
        Field("http_proxy", StringDataValue, required=False),
        Field("https_proxy", StringDataValue, required=False),
        Field("apt_news", BoolDataValue, required=False),
        Field("apt_news_url", StringDataValue, required=False),
        Field("poll_for_pro_license", BoolDataValue, required=False),
        Field("polling_error_retry_delay", IntDataValue, required=False),
        Field("metering_timer", IntDataValue, required=False),
        Field("update_messaging_timer", IntDataValue, required=False),
    ]

    def __init__(
        self,
        apt_http_proxy: Optional[str] = None,
        apt_https_proxy: Optional[str] = None,
        global_apt_http_proxy: Optional[str] = None,
        global_apt_https_proxy: Optional[str] = None,
        ua_apt_http_proxy: Optional[str] = None,
        ua_apt_https_proxy: Optional[str] = None,
        http_proxy: Optional[str] = None,
        https_proxy: Optional[str] = None,
        apt_news: Optional[bool] = None,
        apt_news_url: Optional[str] = None,
        poll_for_pro_license: Optional[bool] = None,
        polling_error_retry_delay: Optional[int] = None,
        metering_timer: Optional[int] = None,
        update_messaging_timer: Optional[int] = None,
    ):
        self.apt_http_proxy = apt_http_proxy
        self.apt_https_proxy = apt_https_proxy
        self.global_apt_http_proxy = global_apt_http_proxy
        self.global_apt_https_proxy = global_apt_https_proxy
        self.ua_apt_http_proxy = ua_apt_http_proxy
        self.ua_apt_https_proxy = ua_apt_https_proxy
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.apt_news = apt_news
        self.apt_news_url = apt_news_url
        self.poll_for_pro_license = poll_for_pro_license
        self.polling_error_retry_delay = polling_error_retry_delay
        self.metering_timer = metering_timer
        self.update_messaging_timer = update_messaging_timer


event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class UserConfigFileObject:
    def __init__(self, directory: str = defaults.DEFAULT_DATA_DIR):
        file_name = defaults.USER_CONFIG_FILE
        self._private = DataObjectFile(
            UserConfigData,
            UAFile(
                file_name,
                os.path.join(directory, defaults.PRIVATE_SUBDIR),
                private=True,
            ),
            DataObjectFileFormat.JSON,
            optional_type_errors_become_null=True,
        )
        self._public = DataObjectFile(
            UserConfigData,
            UAFile(file_name, directory, private=False),
            DataObjectFileFormat.JSON,
            optional_type_errors_become_null=True,
        )

    @property
    def public_config(self) -> UserConfigData:
        public_config = self._public.read()
        if public_config is None:
            public_config = UserConfigData()
        return public_config

    def redact_config_data(
        self, user_config: UserConfigData
    ) -> UserConfigData:
        redacted_data = copy.deepcopy(user_config)
        for field in PROXY_FIELDS:
            value = getattr(redacted_data, field)
            if value:
                parsed_url = urlparse(value)
                if parsed_url.username or parsed_url.password:
                    setattr(
                        redacted_data,
                        field,
                        "<REDACTED>",
                    )
        return redacted_data

    def read(self) -> UserConfigData:
        if util.we_are_currently_root():
            private_config = self._private.read()
            if private_config is not None:
                return private_config
        public_config = self._public.read()
        if public_config is not None:
            return public_config
        return UserConfigData()

    def write(self, content: UserConfigData):
        self._private.write(content)
        redacted_content = self.redact_config_data(content)
        self._public.write(redacted_content)


user_config = UserConfigFileObject(defaults.DEFAULT_DATA_DIR)
