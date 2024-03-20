import logging
import os
import time
from typing import Tuple

from uaclient import exceptions, system, util
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.files import notices
from uaclient.files.data_types import DataObjectFile, DataObjectFileFormat
from uaclient.files.files import UAFile
from uaclient.files.notices import Notice

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class LockData(DataObject):
    fields = [
        Field("lock_pid", StringDataValue),
        Field("lock_holder", StringDataValue),
    ]

    def __init__(self, lock_pid: str, lock_holder: str):
        self.lock_pid = lock_pid
        self.lock_holder = lock_holder


lock_data_file = DataObjectFile(
    LockData,
    UAFile("lock", private=False),
    DataObjectFileFormat.JSON,
)


def check_lock_info() -> Tuple[int, str]:
    """Return lock info if lock file is present the lock is active.

    If process claiming the lock is no longer present, remove the lock file
    and log a warning.

    :return: A tuple (pid, string describing lock holder)
        If no active lock, pid will be -1.
    """

    try:
        lock_data_obj = lock_data_file.read()
    except exceptions.InvalidFileFormatError:
        raise exceptions.InvalidLockFile(lock_file_path=lock_data_file.path)

    no_lock = (-1, "")
    if not lock_data_obj:
        return no_lock

    lock_pid = lock_data_obj.lock_pid
    lock_holder = lock_data_obj.lock_holder

    try:
        system.subp(["ps", lock_pid])
        return (int(lock_pid), lock_holder)
    except exceptions.ProcessExecutionError:
        if not util.we_are_currently_root():
            LOG.debug(
                "Found stale lock file previously held by %s:%s",
                lock_pid,
                lock_holder,
            )
            return (int(lock_pid), lock_holder)
        LOG.warning(
            "Removing stale lock file previously held by %s:%s",
            lock_pid,
            lock_holder,
        )
        system.ensure_file_absent(lock_data_file.path)
        return no_lock


def clear_lock_file_if_present():
    lock_data_file.delete()


class RetryLock:
    """
    Context manager for gaining exclusive access to the lock file.

    Create a lock file if absent. The lock file will contain a pid of the
    running process, and a customer-visible description of the lock holder.

    The RetryLock will try several times to acquire the lock before giving up.
    The number of times to try and how long to sleep in between tries is
    configurable.

    :param lock_holder: String with the service name or command which is
        holding the lock. This lock_holder string will be customer visible in
        status.json.
    :param sleep_time: Number of seconds to sleep before retrying if the lock
        is already held.
    :param max_retries: Maximum number of times to try to grab the lock before
        giving up and raising a LockHeldError.
    :raises: LockHeldError if lock is held after (sleep_time * max_retries)
    """

    def __init__(
        self,
        *_args,
        lock_holder: str,
        sleep_time: int = 10,
        max_retries: int = 12
    ):
        self.lock_holder = lock_holder
        self.sleep_time = sleep_time
        self.max_retries = max_retries

    def grab_lock(self):
        (lock_pid, cur_lock_holder) = check_lock_info()
        if lock_pid > 0:
            raise exceptions.LockHeldError(
                lock_request=self.lock_holder,
                lock_holder=cur_lock_holder,
                pid=lock_pid,
            )
        lock_data_file.write(
            LockData(lock_pid=str(os.getpid()), lock_holder=self.lock_holder)
        )
        notices.add(
            Notice.OPERATION_IN_PROGRESS,
            operation=self.lock_holder,
        )

    def __enter__(self):
        LOG.debug("spin lock starting for %s", self.lock_holder)
        tries = 0
        while True:
            try:
                self.grab_lock()
                break
            except exceptions.LockHeldError as e:
                LOG.debug(
                    "RetryLock Attempt %d. %s. Spinning...", tries + 1, e.msg
                )
                tries += 1
                if tries >= self.max_retries:
                    raise e
                else:
                    time.sleep(self.sleep_time)

    def __exit__(self, _exc_type, _exc_value, _traceback):
        lock_data_file.delete()
        notices.remove(Notice.OPERATION_IN_PROGRESS)
