import mock
import os
from textwrap import dedent

import pytest

from uaclient.cli import action_clean, clean_parser, get_parser
from uaclient import exceptions


@mock.patch("uaclient.cli.os.getuid", return_value=0)
class TestActionClean:
    def test_non_root_users_are_rejected(self, m_getuid, FakeConfig):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        m_getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_clean(mock.MagicMock(), cfg)

    @mock.patch("uaclient.cli.util.subp")
    def test_lock_file_exists(self, m_subp, _m_getuid, FakeConfig):
        """Check when an operation holds a lock file, clean cannot run."""
        cfg = FakeConfig.for_attached_machine()
        with open(cfg.data_path("lock"), "w") as stream:
            stream.write("123:ua enable")
        with pytest.raises(exceptions.LockHeldError) as err:
            action_clean(mock.MagicMock(), cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: ua clean.\n"
            "Operation in progress: ua enable (pid:123)"
        ) == err.value.msg

    @pytest.mark.parametrize("logs", (True, False))
    @mock.patch("uaclient.config.UAConfig.delete_cache")
    def test_clear_cache_and_optional_logfile(
        self, _m_getuid, m_delete_cache, logs, FakeConfig
    ):
        cfg = FakeConfig.for_attached_machine()
        
        with open(cfg.log_file, "w") as stream:
          stream.write("something")
        args = mock.MagicMock()
        args.logs = logs
        action_clean(args, cfg)
        assert [mock.call()] == m_delete_cache.call_args_list
        if logs:
            assert not os.path.exists(cfg.log_file), "Unexpected logfile found"
        else:
            assert os.path.exists(cfg.log_file), "Expected logfile missing"


class TestParser:
    def test_clean_parser_usage(self):
        parser = clean_parser(mock.Mock())
        assert "ua clean [flags]" == parser.usage

    def test_clean_parser_prog(self):
        parser = clean_parser(mock.Mock())
        assert "clean" == parser.prog

    def test_clean_parser_optionals_title(self):
        parser = clean_parser(mock.Mock())
        assert "Flags" == parser._optionals.title

    def test_clean_parser_accepts_and_stores_logs(self):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "clean", "--logs"]):
            args = full_parser.parse_args()

        assert args.logs

    def test_clean_parser_defaults_to_no_logs(self):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "clean"]):
            args = full_parser.parse_args()

        assert not args.logs
