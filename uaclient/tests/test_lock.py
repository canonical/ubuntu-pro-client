import mock
import pytest

from uaclient.exceptions import LockHeldError
from uaclient.files.notices import Notice
from uaclient.lock import SpinLock
from uaclient.messages import LOCK_HELD

M_PATH = "uaclient.lock."
M_PATH_UACONFIG = "uaclient.config.UAConfig."


class TestSpinLock:
    @mock.patch("os.getpid", return_value=123)
    @mock.patch(M_PATH_UACONFIG + "delete_cache_key")
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    @mock.patch(M_PATH_UACONFIG + "write_cache")
    def test_creates_and_releases_lock(
        self,
        m_write_cache,
        m_add_notice,
        m_delete_cache_key,
        _m_getpid,
        FakeConfig,
    ):
        cfg = FakeConfig()
        arg = mock.sentinel.arg

        def test_function(arg):
            assert arg == mock.sentinel.arg
            return mock.sentinel.success

        with SpinLock(cfg=cfg, lock_holder="some operation"):
            ret = test_function(arg)

        assert mock.sentinel.success == ret
        assert [
            mock.call("lock", "123:some operation")
        ] == m_write_cache.call_args_list
        lock_msg = "Operation in progress: some operation"
        assert [
            mock.call(Notice.OPERATION_IN_PROGRESS, lock_msg)
        ] == m_add_notice.call_args_list
        assert [mock.call("lock")] == m_delete_cache_key.call_args_list

    @mock.patch("os.getpid", return_value=123)
    @mock.patch(M_PATH_UACONFIG + "delete_cache_key")
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    @mock.patch(M_PATH_UACONFIG + "write_cache")
    def test_creates_and_releases_lock_when_error_occurs(
        self,
        m_write_cache,
        m_add_notice,
        m_delete_cache_key,
        _m_getpid,
        FakeConfig,
    ):
        cfg = FakeConfig()

        def test_function():
            raise RuntimeError("test")

        with pytest.raises(RuntimeError) as exc:
            with SpinLock(cfg=cfg, lock_holder="some operation"):
                test_function()

        assert "test" == str(exc.value)
        assert [
            mock.call("lock", "123:some operation")
        ] == m_write_cache.call_args_list
        lock_msg = "Operation in progress: some operation"
        assert [
            mock.call(Notice.OPERATION_IN_PROGRESS, lock_msg)
        ] == m_add_notice.call_args_list
        assert [mock.call("lock")] == m_delete_cache_key.call_args_list

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
    def test_spins_when_lock_held(
        self, m_single_attempt_lock_enter, m_sleep, FakeConfig
    ):
        cfg = FakeConfig()

        with SpinLock(
            cfg=cfg, lock_holder="request", sleep_time=1, max_retries=3
        ):
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
        self, m_single_attempt_lock_enter, m_sleep, FakeConfig
    ):
        cfg = FakeConfig()

        with pytest.raises(LockHeldError) as exc:
            with SpinLock(
                cfg=cfg, lock_holder="request", sleep_time=1, max_retries=2
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
