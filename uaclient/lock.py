import functools
import logging
import os
import time

from uaclient import config, exceptions

LOG = logging.getLogger("pro.lock")

# Set a module-level callable here so we don't have to reinstantiate
# UAConfig in order to determine dynamic data_path exception handling of
# main_error_handler
clear_lock_file = None


def clear_lock_file_if_present():
    global clear_lock_file
    if clear_lock_file:
        clear_lock_file()


class SingleAttemptLock:
    """
    Context manager for gaining exclusive access to the lock file.
    Create a lock file if absent. The lock file will contain a pid of the
    running process, and a customer-visible description of the lock holder.

    :param lock_holder: String with the service name or command which is
        holding the lock. This lock_holder string will be customer visible in
        status.json.
    :raises: LockHeldError if lock is held.
    """

    def __init__(self, *_args, cfg: config.UAConfig, lock_holder: str):
        self.cfg = cfg
        self.lock_holder = lock_holder

    def __enter__(self):
        global clear_lock_file
        (lock_pid, cur_lock_holder) = self.cfg.check_lock_info()
        if lock_pid > 0:
            raise exceptions.LockHeldError(
                lock_request=self.lock_holder,
                lock_holder=cur_lock_holder,
                pid=lock_pid,
            )
        self.cfg.write_cache(
            "lock", "{}:{}".format(os.getpid(), self.lock_holder)
        )
        notice_msg = "Operation in progress: {}".format(self.lock_holder)
        self.cfg.notice_file.add("", notice_msg)
        clear_lock_file = functools.partial(self.cfg.delete_cache_key, "lock")

    def __exit__(self, _exc_type, _exc_value, _traceback):
        global clear_lock_file
        self.cfg.delete_cache_key("lock")
        clear_lock_file = None  # Unset due to successful lock delete


class SpinLock(SingleAttemptLock):
    """
    Context manager for gaining exclusive access to the lock file. In contrast
    to the SingleAttemptLock, the SpinLock will try several times to acquire
    the lock before giving up. The number of times to try and how long to sleep
    in between tries is configurable.

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
        cfg: config.UAConfig,
        lock_holder: str,
        sleep_time: int = 10,
        max_retries: int = 12
    ):
        super().__init__(cfg=cfg, lock_holder=lock_holder)
        self.sleep_time = sleep_time
        self.max_retries = max_retries

    def __enter__(self):
        LOG.debug("spin lock starting for {}".format(self.lock_holder))
        tries = 0
        while True:
            try:
                super().__enter__()
                break
            except exceptions.LockHeldError as e:
                LOG.debug(
                    "SpinLock Attempt {}. {}. Spinning...".format(
                        tries + 1, e.msg
                    )
                )
                tries += 1
                if tries >= self.max_retries:
                    raise e
                else:
                    time.sleep(self.sleep_time)
