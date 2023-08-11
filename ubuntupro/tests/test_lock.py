import mock
import pytest

from ubuntupro.exceptions import LockHeldError
from ubuntupro.files.notices import Notice
from ubuntupro.lock import SingleAttemptLock, SpinLock
from ubuntupro.messages import LOCK_HELD

M_PATH = "ubuntupro.lock."
M_PATH_UACONFIG = "ubuntupro.config.UAConfig."


@pytest.mark.parametrize("lock_cls", (SingleAttemptLock, SpinLock))
@mock.patch("os.getpid", return_value=123)
@mock.patch(M_PATH_UACONFIG + "delete_cache_key")
@mock.patch("ubuntupro.files.notices.NoticesManager.add")
@mock.patch(M_PATH_UACONFIG + "write_cache")
class TestLockCommon:
    def test_creates_and_releases_lock(
        self,
        m_write_cache,
        m_add_notice,
        m_delete_cache_key,
        _m_getpid,
        lock_cls,
        FakeConfig,
    ):
        cfg = FakeConfig()
        arg = mock.sentinel.arg

        def test_function(arg):
            assert arg == mock.sentinel.arg
            return mock.sentinel.success

        with lock_cls(cfg=cfg, lock_holder="some operation"):
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

    def test_creates_and_releases_lock_when_error_occurs(
        self,
        m_write_cache,
        m_add_notice,
        m_delete_cache_key,
        _m_getpid,
        lock_cls,
        FakeConfig,
    ):
        cfg = FakeConfig()

        def test_function():
            raise RuntimeError("test")

        with pytest.raises(RuntimeError) as exc:
            with lock_cls(cfg=cfg, lock_holder="some operation"):
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


@mock.patch("os.getpid", return_value=123)
@mock.patch(M_PATH_UACONFIG + "delete_cache_key")
@mock.patch("ubuntupro.files.notices.NoticesManager.add")
@mock.patch(M_PATH_UACONFIG + "write_cache")
class TestSingleAttemptLock:
    @mock.patch(M_PATH_UACONFIG + "check_lock_info", return_value=(10, "held"))
    def test_raises_lock_held_when_held(
        self,
        _m_check_lock_info,
        m_write_cache,
        m_add_notice,
        m_delete_cache_key,
        _m_getpid,
        FakeConfig,
    ):
        cfg = FakeConfig()
        arg = mock.sentinel.arg

        def test_function(args, cfg):
            assert arg == mock.sentinel.arg
            return mock.sentinel.success

        with pytest.raises(LockHeldError) as exc:
            with SingleAttemptLock(cfg=cfg, lock_holder="some operation"):
                test_function(arg, cfg=cfg)

        assert (
            "Unable to perform: some operation.\n"
            + LOCK_HELD.format(lock_holder="held", pid=10).msg
            == exc.value.msg
        )

        assert [] == m_write_cache.call_args_list
        assert [] == m_add_notice.call_args_list
        assert [] == m_delete_cache_key.call_args_list


class TestSpinLock:
    @mock.patch(M_PATH + "time.sleep")
    @mock.patch(
        M_PATH + "SingleAttemptLock.__enter__",
        side_effect=[
            LockHeldError("request", "holder", 10),
            LockHeldError("request", "holder", 10),
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
        M_PATH + "SingleAttemptLock.__enter__",
        side_effect=[
            LockHeldError("request", "holder", 10),
            LockHeldError("request", "holder", 10),
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
            + LOCK_HELD.format(lock_holder="holder", pid=10).msg
            == exc.value.msg
        )

        assert [
            mock.call(),
            mock.call(),
        ] == m_single_attempt_lock_enter.call_args_list
        assert [mock.call(1)] == m_sleep.call_args_list
