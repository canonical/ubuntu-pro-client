import datetime
import logging
import pathlib
import time
from subprocess import TimeoutExpired
from typing import Optional

from uaclient import defaults, exceptions, files, system
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    full_auto_attach,
)
from uaclient.config import UAConfig
from uaclient.data_types import (
    DataObject,
    DatetimeDataValue,
    Field,
    StringDataValue,
)

FLAG_FILE_PATH = "/run/ubuntu-advantage/flags/retry-auto-attach-running"

OPTIONS_FILE = files.DataObjectFile(
    RetryOptions,
    files.UAFile(
        "retry-auto-attach-options.json",
        defaults.DEFAULT_DATA_DIR,
        private=True,
    ),
    files.DataObjectFileFormat.JSON,
)
STATE_FILE = files.DataObjectFile(
    RetryState,
    files.UAFile(
        "retry-auto-attach-state.json", defaults.DEFAULT_DATA_DIR, private=True
    ),
    files.DataObjectFileFormat.JSON,
)

RetryOptions = FullAutoAttachOptions


class RetryState(DataObject):
    fields = [
        Field("last_attempt", DatetimeDataValue),
        Field("next_attempt", DatetimeDataValue),
        Field("failure_reason", StringDataValue, required=False),
    ]

    def __init__(
        self,
        last_attempt: datetime.datetime,
        next_attempt: datetime.datetime,
        failure_reason: Optional[str],
    ):
        self.last_attempt = last_attempt
        self.next_attempt = next_attempt
        self.failure_reason = failure_reason


def start():
    try:
        system.subp(
            ["systemctl", "start", "pro-auto-attach-retry.service"],
            timeout=2.0,
        )
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        logging.warning(e)


def stop():
    try:
        system.subp(
            ["systemctl", "stop", "pro-auto-attach-retry.service"], timeout=2.0
        )
    except (exceptions.ProcessExecutionError, TimeoutExpired) as e:
        logging.warning(e)


def _should_stop_retrying(cfg: UAConfig) -> bool:
    if cfg.is_attached():
        return True

    # TODO more checks

    return False


def retry_auto_attach(cfg: UAConfig) -> None:
    intervals = [
        900,  # 15m (T+15m)
        900,  # 15m (T+30m)
        1800,  # 30m (T+1h)
        3600,  # 1h  (T+2h)
        7200,  # 2h  (T+4h)
        14400,  # 4h  (T+8h)
        28800,  # 8h  (T+16h)
        28800,  # 8h  (T+1d)
        86400,  # 1d  (T+2d)
        86400,  # 1d  (T+3d)
        172800,  # 2d  (T+5d)
        172800,  # 2d  (T+7d)
        259200,  # 3d  (T+10d)
        259200,  # 3d  (T+13d)
        345600,  # 4d  (T+17d)
        345600,  # 4d  (T+21d)
        432000,  # 5d  (T+26d)
        432000,  # 5d  (T+31d)
    ]
    failure_reason = None
    for interval in intervals:
        last_attempt = datetime.datetime.now(datetime.timezone.utc)
        next_attempt = last_attempt + datetime.timedelta(seconds=interval)
        STATE_FILE.write(
            RetryState(
                last_attempt=last_attempt,
                next_attempt=next_attempt,
                failure_reason=failure_reason,
            )
        )
        # TODO update messaging: motd and status

        time.sleep(interval)

        if cfg.is_attached():
            # We attached while sleeping - hooray!
            break

        try:
            full_auto_attach(FullAutoAttachOptions())
        except Exception as e:
            # TODO catch specific exceptions
            failure_reason = str(e)
            logging.error(e)
            continue
        break

    STATE_FILE.delete()
    OPTIONS_FILE.delete()
    if not cfg.is_attached():
        # Total failure!!
        # TODO message
        pass
