import os

import mock
import pytest

from uaclient import lock
from uaclient.defaults import DEFAULT_DATA_DIR
from uaclient.exceptions import InvalidLockFile, LockHeldError
from uaclient.files.notices import Notice
from uaclient.messages import E_INVALID_LOCK_FILE, LOCK_HELD

M_PATH = "uaclient.lock."
M_PATH_UACONFIG = "uaclient.config.UAConfig."


class TestSpinLock:
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("os.getpid", return_value=123)
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    def test_creates_and_releases_lock(
        self,
        m_add_notice,
        _m_getpid,
        _m_check_lock_info,
    ):
        def test_function():
            return mock.sentinel.success

        with mock.patch.object(lock, "lock_data_file") as m_lock_file:
            with lock.SpinLock(lock_holder="some operation"):
                ret = test_function()

        assert mock.sentinel.success == ret
        assert [
            mock.call(
                lock.LockData(lock_pid="123", lock_holder="some operation")
            )
        ] == m_lock_file.write.call_args_list
        lock_msg = "Operation in progress: some operation"
        assert [
            mock.call(Notice.OPERATION_IN_PROGRESS, lock_msg)
        ] == m_add_notice.call_args_list
        assert 1 == m_lock_file.delete.call_count

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("os.getpid", return_value=123)
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    def test_creates_and_releases_lock_when_error_occurs(
        self,
        m_add_notice,
        _m_getpid,
        _m_check_lock_info,
    ):
        def test_function():
            raise RuntimeError("test")

        with pytest.raises(RuntimeError) as exc:
            with mock.patch.object(lock, "lock_data_file") as m_lock_file:
                with lock.SpinLock(lock_holder="some operation"):
                    test_function()

        assert "test" == str(exc.value)
        assert [
            mock.call(
                lock.LockData(lock_pid="123", lock_holder="some operation")
            )
        ] == m_lock_file.write.call_args_list
        lock_msg = "Operation in progress: some operation"
        assert [
            mock.call(Notice.OPERATION_IN_PROGRESS, lock_msg)
        ] == m_add_notice.call_args_list
        assert 1 == m_lock_file.delete.call_count

    @mock.patch(M_PATH + "time.sleep")
    @mock.patch(
        M_PATH + "SpinLock.grab_lock",
        side_effect=[
            LockHeldError(
                lock_request="request", lock_holder="holder", pid=10
            ),
            LockHeldError(
                lock_request="request", lock_holder="holder", pid=10
            ),
            None,
        ],
    )
    def test_spins_when_lock_held(self, m_single_attempt_lock_enter, m_sleep):
        with lock.SpinLock(lock_holder="request", sleep_time=1, max_retries=3):
            pass

        assert [
            mock.call(),
            mock.call(),
            mock.call(),
        ] == m_single_attempt_lock_enter.call_args_list
        assert [mock.call(1), mock.call(1)] == m_sleep.call_args_list

    @mock.patch(M_PATH + "time.sleep")
    @mock.patch(
        M_PATH + "SpinLock.grab_lock",
        side_effect=[
            LockHeldError(
                lock_request="request", lock_holder="holder", pid=10
            ),
            LockHeldError(
                lock_request="request", lock_holder="holder", pid=10
            ),
            None,
        ],
    )
    def test_raises_lock_held_after_max_retries(
        self, m_single_attempt_lock_enter, m_sleep
    ):
        with pytest.raises(LockHeldError) as exc:
            with lock.SpinLock(
                lock_holder="request", sleep_time=1, max_retries=2
            ):
                pass

        assert (
            "Unable to perform: request.\n"
            + LOCK_HELD.format(lock_holder="holder", pid=10)
            == exc.value.msg
        )

        assert [
            mock.call(),
            mock.call(),
        ] == m_single_attempt_lock_enter.call_args_list
        assert [mock.call(1)] == m_sleep.call_args_list


class TestCheckLockInfo:
    @pytest.mark.parametrize("lock_content", ((""), ("corrupted")))
    @mock.patch("uaclient.system.load_file")
    def test_raise_exception_for_corrupted_lock(
        self,
        m_load_file,
        lock_content,
    ):
        m_load_file.return_value = lock_content

        expected_msg = E_INVALID_LOCK_FILE.format(
            lock_file_path=os.path.join(DEFAULT_DATA_DIR, "lock")
        )

        with pytest.raises(InvalidLockFile) as exc_info:
            lock.check_lock_info()

        assert expected_msg.msg == exc_info.value.msg
        assert m_load_file.call_count == 1
