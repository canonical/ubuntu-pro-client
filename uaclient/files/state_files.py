import datetime
from typing import Any, Dict, List, Optional

from uaclient import defaults
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)
from uaclient.files.data_types import DataObjectFile, DataObjectFileFormat
from uaclient.files.files import UAFile, UserCacheFile

SERVICES_ONCE_ENABLED = "services-once-enabled"


class ServicesOnceEnabledData(DataObject):
    fields = [
        Field("fips_updates", BoolDataValue, False),
    ]

    def __init__(self, fips_updates: bool):
        self.fips_updates = fips_updates


def _services_once_enable_preprocess_data(
    data: Dict[str, Any]
) -> Dict[str, Any]:
    # Since we are using now returning DataObject instances from read, we
    # cannot have variables with "-" in them. We need to explictly convert
    # them before creating the object
    updated_data = {}
    for key in data.keys():
        if "-" in key:
            updated_data[key.replace("-", "_")] = True
        else:
            updated_data[key] = True

    return updated_data


services_once_enabled_file = DataObjectFile(
    data_object_cls=ServicesOnceEnabledData,
    ua_file=UAFile(
        name=SERVICES_ONCE_ENABLED,
        private=False,
    ),
    preprocess_data=_services_once_enable_preprocess_data,
)


class RetryAutoAttachOptions(DataObject):
    fields = [
        Field("enable", data_list(StringDataValue), False),
        Field("enable_beta", data_list(StringDataValue), False),
    ]

    def __init__(
        self,
        enable: Optional[List[str]] = None,
        enable_beta: Optional[List[str]] = None,
    ):
        self.enable = enable
        self.enable_beta = enable_beta


retry_auto_attach_options_file = DataObjectFile(
    RetryAutoAttachOptions,
    UAFile(
        "retry-auto-attach-options.json",
        private=True,
    ),
    DataObjectFileFormat.JSON,
)


class RetryAutoAttachState(DataObject):
    fields = [
        Field("interval_index", IntDataValue),
        Field("failure_reason", StringDataValue, required=False),
    ]

    def __init__(
        self,
        interval_index: int,
        failure_reason: Optional[str],
    ):
        self.interval_index = interval_index
        self.failure_reason = failure_reason


retry_auto_attach_state_file = DataObjectFile(
    RetryAutoAttachState,
    UAFile("retry-auto-attach-state.json", private=True),
    DataObjectFileFormat.JSON,
)


class TimerJobState(DataObject):
    fields = [
        Field("next_run", DatetimeDataValue),
        Field("last_run", DatetimeDataValue),
    ]

    def __init__(self, next_run, last_run):
        self.next_run = next_run
        self.last_run = last_run


class AllTimerJobsState(DataObject):
    fields = [
        Field("metering", TimerJobState, required=False),
        Field("update_messaging", TimerJobState, required=False),
        Field("update_contract_info", TimerJobState, required=False),
    ]

    def __init__(
        self,
        metering: Optional[TimerJobState],
        update_messaging: Optional[TimerJobState],
        update_contract_info: Optional[TimerJobState],
    ):
        self.metering = metering
        self.update_messaging = update_messaging
        self.update_contract_info = update_contract_info


timer_jobs_state_file = DataObjectFile(
    AllTimerJobsState,
    UAFile("jobs-status.json", private=False),
    DataObjectFileFormat.JSON,
)


apt_news_contents_file = UAFile("apt-news", directory=defaults.MESSAGES_DIR)
apt_news_raw_file = UAFile(
    "apt-news-raw", private=False, directory=defaults.MESSAGES_DIR
)


class LivepatchSupportCacheData(DataObject):
    fields = [
        Field("version", StringDataValue),
        Field("flavor", StringDataValue),
        Field("arch", StringDataValue),
        Field("codename", StringDataValue),
        Field("supported", BoolDataValue, required=False),
        Field("cached_at", DatetimeDataValue),
    ]

    def __init__(
        self,
        version: str,
        flavor: str,
        arch: str,
        codename: str,
        supported: Optional[bool],
        cached_at: datetime.datetime,
    ):
        self.version = version
        self.flavor = flavor
        self.arch = arch
        self.codename = codename
        self.supported = supported
        self.cached_at = cached_at


livepatch_support_cache = DataObjectFile(
    LivepatchSupportCacheData,
    UserCacheFile("livepatch-kernel-support-cache.json"),
    file_format=DataObjectFileFormat.JSON,
)


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


user_config_file = DataObjectFile(
    UserConfigData,
    UAFile("user-config.json", private=True),
    DataObjectFileFormat.JSON,
    optional_type_errors_become_null=True,
)


reboot_cmd_marker_file = UAFile("marker-reboot-cmds-required")


class AnboxCloudData(DataObject):
    fields = [
        Field("anbox_images_url", StringDataValue),
        Field("anbox_images_resource_token", StringDataValue),
        Field("anbox_cloud_apt_token", StringDataValue),
        Field("anbox_cloud_apt_url", StringDataValue),
    ]

    def __init__(
        self,
        anbox_images_url: str,
        anbox_images_resource_token: str,
        anbox_cloud_apt_token: str,
        anbox_cloud_apt_url: str,
    ):
        self.anbox_images_url = anbox_images_url
        self.anbox_images_resource_token = anbox_images_resource_token
        self.anbox_cloud_apt_token = anbox_cloud_apt_token
        self.anbox_cloud_apt_url = anbox_cloud_apt_url


anbox_cloud_credentials_file = DataObjectFile(
    AnboxCloudData,
    UAFile(
        "anbox-cloud-credentials",
        defaults.DEFAULT_PRIVATE_DATA_DIR,
        private=True,
    ),
    DataObjectFileFormat.JSON,
)


class AttachmentData(DataObject):
    fields = [
        Field("attached_at", DatetimeDataValue),
    ]

    def __init__(self, attached_at: datetime.datetime):
        self.attached_at = attached_at


attachment_data_file = DataObjectFile(
    AttachmentData,
    UAFile("attachment.json", private=False),
    DataObjectFileFormat.JSON,
)
