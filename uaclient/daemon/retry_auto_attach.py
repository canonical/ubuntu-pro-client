import datetime
import logging
import time

from uaclient import exceptions, lock, messages, system, util
from uaclient.api import exceptions as api_exceptions
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    full_auto_attach,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.daemon import AUTO_ATTACH_STATUS_MOTD_FILE
from uaclient.files import notices, state_files

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

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
FLAG_FILE_PATH = "/run/ubuntu-advantage/flags/auto-attach-failed"


def full_auto_attach_exception_to_failure_reason(e: Exception) -> str:
    if isinstance(e, api_exceptions.InvalidProImage):
        return messages.RETRY_ERROR_DETAIL_INVALID_PRO_IMAGE.format(
            detail=e.error_msg
        )
    elif isinstance(e, api_exceptions.NonAutoAttachImageError):
        return messages.RETRY_ERROR_DETAIL_NON_AUTO_ATTACH_IMAGE
    elif isinstance(e, api_exceptions.LockHeldError):
        return messages.RETRY_ERROR_DETAIL_LOCK_HELD.format(pid=e.pid)
    elif isinstance(e, api_exceptions.ContractAPIError):
        return messages.RETRY_ERROR_DETAIL_CONTRACT_API_ERROR.format(
            error_msg=e.body
        )
    elif isinstance(e, api_exceptions.ConnectivityError):
        return messages.RETRY_ERROR_DETAIL_URL_ERROR_URL.format(
            url=e.url
        ) + ': "{}"'.format(str(e.cause_error))
    elif isinstance(e, api_exceptions.UbuntuProError):
        return '"{}"'.format(e.msg)
    else:
        LOG.error("Unexpected exception", exc_info=e)
        return str(e) or messages.UNKNOWN_ERROR


def cleanup(cfg: UAConfig):
    state_files.retry_auto_attach_state_file.delete()
    state_files.retry_auto_attach_options_file.delete()
    system.ensure_file_absent(AUTO_ATTACH_STATUS_MOTD_FILE)
    notices.remove(
        notices.Notice.AUTO_ATTACH_RETRY_FULL_NOTICE,
    )
    notices.remove(
        notices.Notice.AUTO_ATTACH_RETRY_TOTAL_FAILURE,
    )


def retry_auto_attach(cfg: UAConfig) -> None:
    # in case we got started while already attached somehow
    if _is_attached(cfg).is_attached:
        return

    # pick up where we left off
    persisted_state = state_files.retry_auto_attach_state_file.read()
    if persisted_state is not None:
        # skip intervals we've already waited
        offset = persisted_state.interval_index
        intervals = RETRY_INTERVALS[offset:]
        failure_reason = persisted_state.failure_reason
    else:
        offset = 0
        intervals = RETRY_INTERVALS
        failure_reason = None

    for index, interval in enumerate(intervals):
        last_attempt = datetime.datetime.now(datetime.timezone.utc)
        next_attempt = last_attempt + datetime.timedelta(seconds=interval)
        next_attempt = next_attempt.replace(second=0, microsecond=0)
        state_files.retry_auto_attach_state_file.write(
            state_files.RetryAutoAttachState(
                interval_index=offset + index,
                failure_reason=failure_reason,
            )
        )
        msg_reason = failure_reason
        if msg_reason is None:
            msg_reason = messages.UNKNOWN_ERROR
        try:
            next_attempt = next_attempt.astimezone()
        except Exception:
            pass
        auto_attach_status_msg = messages.AUTO_ATTACH_RETRY_NOTICE.format(
            num_attempts=offset + index + 1,
            reason=msg_reason,
            next_run_datestring=next_attempt.isoformat(),
        )
        system.write_file(
            AUTO_ATTACH_STATUS_MOTD_FILE,
            "\n" + auto_attach_status_msg + "\n\n",
        )
        try:
            with lock.RetryLock(
                lock_holder="pro.daemon.retry_auto_attach.notice_updates",
            ):
                notices.add(
                    notices.Notice.AUTO_ATTACH_RETRY_FULL_NOTICE,
                    num_attempts=offset + index + 1,
                    reason=msg_reason,
                    next_run_datestring=next_attempt.isoformat(),
                )
        except exceptions.LockHeldError:
            pass

        time.sleep(interval)

        if _is_attached(cfg).is_attached:
            # We attached while sleeping - hooray!
            break

        try:
            persisted_options = (
                state_files.retry_auto_attach_options_file.read()
            )
            options = FullAutoAttachOptions()
            if persisted_options is not None:
                options.enable = persisted_options.enable
                options.enable_beta = persisted_options.enable_beta
            full_auto_attach(options)
            break
        except api_exceptions.AlreadyAttachedError:
            LOG.info("already attached, ending retry service")
            break
        except api_exceptions.EntitlementsNotEnabledError as e:
            LOG.warning(e.msg)
            break
        except Exception as e:
            failure_reason = full_auto_attach_exception_to_failure_reason(e)
            LOG.error(e)

    cleanup(cfg)

    if not _is_attached(cfg).is_attached:
        # Total failure!!
        state_files.retry_auto_attach_state_file.write(
            state_files.RetryAutoAttachState(
                interval_index=len(RETRY_INTERVALS),
                failure_reason=failure_reason,
            )
        )
        msg_reason = failure_reason
        if msg_reason is None:
            msg_reason = messages.UNKNOWN_ERROR
        auto_attach_status_msg = (
            messages.AUTO_ATTACH_RETRY_TOTAL_FAILURE_NOTICE.format(
                num_attempts=len(RETRY_INTERVALS) + 1, reason=msg_reason
            )
        )
        system.write_file(
            AUTO_ATTACH_STATUS_MOTD_FILE,
            "\n" + auto_attach_status_msg + "\n\n",
        )
        notices.add(
            notices.Notice.AUTO_ATTACH_RETRY_TOTAL_FAILURE,
            num_attempts=len(RETRY_INTERVALS) + 1,
            reason=msg_reason,
        )
