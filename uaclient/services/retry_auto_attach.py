import datetime
import logging
import time
from subprocess import TimeoutExpired
from typing import Optional

from uaclient import defaults, exceptions, files, messages, system
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    full_auto_attach,
)
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    IntDataValue,
    StringDataValue,
)
from uaclient.services import AUTO_ATTACH_STATUS_MOTD_FILE

RETRY_INTERVALS = [
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
FLAG_FILE_PATH = "/run/ubuntu-advantage/flags/retry-auto-attach-running"

RetryOptions = FullAutoAttachOptions


class RetryState(DataObject):
    fields = [
        Field("interval_index", IntDataValue),
        Field("next_attempt", DatetimeDataValue),
        Field("failure_reason", StringDataValue, required=False),
    ]

    def __init__(
        self,
        interval_index: int,
        next_attempt: datetime.datetime,
        failure_reason: Optional[str],
    ):
        self.interval_index = interval_index
        self.next_attempt = next_attempt
        self.failure_reason = failure_reason


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


def retry_auto_attach(cfg: UAConfig) -> None:
    # in case we got started while already attached somehow
    if cfg.is_attached:
        return

    # pick up where we left off
    persisted_state = STATE_FILE.try_read()
    if persisted_state is not None:
        # skip intervals we've already waited
        intervals = RETRY_INTERVALS[persisted_state.interval_index :]
        failure_reason = persisted_state.failure_reason
    else:
        intervals = RETRY_INTERVALS
        failure_reason = None

    for index, interval in enumerate(intervals):
        last_attempt = datetime.datetime.now(datetime.timezone.utc)
        next_attempt = last_attempt + datetime.timedelta(seconds=interval)
        STATE_FILE.write(
            RetryState(
                interval_index=index,
                next_attempt=next_attempt,
                failure_reason=failure_reason,
            )
        )
        msg_reason = failure_reason
        if msg_reason is None:
            msg_reason = "an unknown error"
        try:
            next_attempt = next_attempt.astimezone()
        except Exception:
            pass
        auto_attach_status_msg = messages.AUTO_ATTACH_RETRY_NOTICE.format(
            num_attempts=index + 1,
            reason=msg_reason,
            next_run_datestring=next_attempt.isoformat(),
        )
        system.write_file(
            AUTO_ATTACH_STATUS_MOTD_FILE, auto_attach_status_msg + "\n"
        )
        cfg.notice_file.remove("", messages.AUTO_ATTACH_RETRY_NOTICE_PREFIX)
        cfg.notice_file.add("", auto_attach_status_msg)

        time.sleep(interval)

        if cfg.is_attached:
            # We attached while sleeping - hooray!
            break

        persisted_options = OPTIONS_FILE.try_read()

        try:
            options = FullAutoAttachOptions()
            if persisted_options is not None:
                options.enable = persisted_options.enable
                options.enable_beta = persisted_options.enable_beta
            full_auto_attach(options)
            break
        except Exception as e:
            # TODO catch specific exceptions
            if isinstance(e, exceptions.UserFacingError):
                failure_reason = e.msg
            else:
                failure_reason = str(e)
            logging.error(e)
            continue

    STATE_FILE.delete()
    OPTIONS_FILE.delete()
    system.remove_file(AUTO_ATTACH_STATUS_MOTD_FILE)
    cfg.notice_file.remove("", messages.AUTO_ATTACH_RETRY_NOTICE_PREFIX)

    if not cfg.is_attached():
        # Total failure!!
        msg_reason = failure_reason
        if msg_reason is None:
            msg_reason = "an unknown error"
        auto_attach_status_msg = (
            messages.AUTO_ATTACH_RETRY_TOTAL_FAILURE_NOTICE.format(
                num_attempts=len(RETRY_INTERVALS) + 1, reason=msg_reason
            )
        )
        system.write_file(
            AUTO_ATTACH_STATUS_MOTD_FILE, auto_attach_status_msg + "\n"
        )
        cfg.notice_file.remove("", messages.AUTO_ATTACH_RETRY_NOTICE_PREFIX)
        cfg.notice_file.add("", auto_attach_status_msg)
