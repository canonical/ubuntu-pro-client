import mock
import pytest

from uaclient import lock
from uaclient.cli.cli_util import (
    assert_attached,
    assert_lock_file,
    assert_not_attached,
    assert_root,
)
from uaclient.exceptions import (
    AlreadyAttachedError,
    NonRootUserError,
    UnattachedError,
)
from uaclient.files.notices import Notice

M_PATH_UACONFIG = "uaclient.config.UAConfig."


class TestAssertLockFile:
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("os.getpid", return_value=123)
    @mock.patch("uaclient.files.notices.NoticesManager.add")
    def test_assert_root_creates_lock_and_notice(
        self,
        m_add_notice,
        _m_getpid,
        _m_check_lock_info,
        FakeConfig,
    ):
        arg, kwarg = mock.sentinel.arg, mock.sentinel.kwarg

        @assert_lock_file("some operation")
        def test_function(args, cfg):
            assert arg == mock.sentinel.arg
            assert kwarg == mock.sentinel.kwarg

            return mock.sentinel.success

        with mock.patch.object(lock, "lock_data_file") as m_lock_file:
            ret = test_function(arg, cfg=mock.MagicMock())

        assert mock.sentinel.success == ret
        lock_msg = "Operation in progress: some operation"
        assert [
            mock.call(Notice.OPERATION_IN_PROGRESS, lock_msg)
        ] == m_add_notice.call_args_list
        assert [
            mock.call(
                lock.LockData(lock_pid="123", lock_holder="some operation")
            )
        ] == m_lock_file.write.call_args_list
        assert 1 == m_lock_file.delete.call_count


class TestAssertRoot:
    def test_assert_root_when_root(self):
        # autouse mock for we_are_currently_root defaults it to True
        arg, kwarg = mock.sentinel.arg, mock.sentinel.kwarg

        @assert_root
        def test_function(arg, *, kwarg):
            assert arg == mock.sentinel.arg
            assert kwarg == mock.sentinel.kwarg

            return mock.sentinel.success

        ret = test_function(arg, kwarg=kwarg)

        assert mock.sentinel.success == ret

    def test_assert_root_when_not_root(self):
        @assert_root
        def test_function():
            pass

        with mock.patch(
            "uaclient.cli.util.we_are_currently_root", return_value=False
        ):
            with pytest.raises(NonRootUserError):
                test_function()


# Test multiple uids, to be sure that the root checking is absent
@pytest.mark.parametrize("root", [True, False])
class TestAssertAttached:
    def test_assert_attached_when_attached(self, capsys, root, FakeConfig):
        @assert_attached()
        def test_function(args, cfg):
            return mock.sentinel.success

        cfg = FakeConfig.for_attached_machine()

        with mock.patch(
            "uaclient.cli.util.we_are_currently_root", return_value=root
        ):
            ret = test_function(mock.Mock(), cfg)

        assert mock.sentinel.success == ret

        out, _err = capsys.readouterr()
        assert "" == out.strip()

    def test_assert_attached_when_unattached(self, root, FakeConfig):
        @assert_attached()
        def test_function(args, cfg):
            pass

        cfg = FakeConfig()

        with mock.patch(
            "uaclient.cli.util.we_are_currently_root", return_value=root
        ):
            with pytest.raises(UnattachedError):
                test_function(mock.Mock(), cfg)


@pytest.mark.parametrize("root", [True, False])
class TestAssertNotAttached:
    def test_when_attached(self, root, FakeConfig):
        @assert_not_attached
        def test_function(args, cfg):
            pass

        cfg = FakeConfig.for_attached_machine()

        with mock.patch(
            "uaclient.cli.util.we_are_currently_root", return_value=root
        ):
            with pytest.raises(AlreadyAttachedError):
                test_function(mock.Mock(), cfg)

    def test_when_not_attached(self, capsys, root, FakeConfig):
        @assert_not_attached
        def test_function(args, cfg):
            return mock.sentinel.success

        cfg = FakeConfig()

        with mock.patch(
            "uaclient.cli.util.we_are_currently_root", return_value=root
        ):
            ret = test_function(mock.Mock(), cfg)

        assert mock.sentinel.success == ret

        out, _err = capsys.readouterr()
        assert "" == out.strip()
