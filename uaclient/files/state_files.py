from typing import Any, Dict, List, Optional

from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)
from uaclient.defaults import MESSAGES_DIR
from uaclient.files.data_types import DataObjectFile, DataObjectFileFormat
from uaclient.files.files import UAFile

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
    ]

    def __init__(
        self,
        metering: Optional[TimerJobState],
        update_messaging: Optional[TimerJobState],
    ):
        self.metering = metering
        self.update_messaging = update_messaging


timer_jobs_state_file = DataObjectFile(
    AllTimerJobsState,
    UAFile("jobs-status.json"),
    DataObjectFileFormat.JSON,
)


apt_news_contents_file = UAFile("apt-news", directory=MESSAGES_DIR)
