import logging
import mock
import os
import stat
import sys

import pytest

from uaclient.cli import assert_attached_root, main, setup_logging
from uaclient.exceptions import (
    NonRootUserError,
    UserFacingError,
    UnattachedError,
)
from uaclient.testing.fakes import FakeConfig


class TestAssertAttachedRoot:
    def test_assert_attached_root_happy_path(self, capsys):
        @assert_attached_root
        def test_function(args, cfg):
            return mock.sentinel.success

        cfg = FakeConfig.for_attached_machine()

        with mock.patch("uaclient.cli.os.getuid", return_value=0):
            ret = test_function(mock.Mock(), cfg)

        assert mock.sentinel.success == ret

        out, _err = capsys.readouterr()
        assert "" == out.strip()

    @pytest.mark.parametrize(
        "attached,uid,expected_exception",
        [
            (True, 1000, NonRootUserError),
            (False, 1000, NonRootUserError),
            (False, 0, UnattachedError),
        ],
    )
    def test_assert_attached_root_exceptions(
        self, attached, uid, expected_exception
    ):
        @assert_attached_root
        def test_function(args, cfg):
            return mock.sentinel.success

        if attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()

        with pytest.raises(expected_exception):
            with mock.patch("uaclient.cli.os.getuid", return_value=uid):
                test_function(mock.Mock(), cfg)


class TestMain:
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_keyboard_interrupt_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        capsys,
        logging_sandbox,
        caplog_text,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = KeyboardInterrupt

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert "Interrupt received; exiting.\n" == err
        error_log = caplog_text()
        assert "Traceback (most recent call last):" in error_log

    @pytest.mark.parametrize("caplog_text", [logging.ERROR], indirect=True)
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_user_facing_error_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        capsys,
        logging_sandbox,
        caplog_text,
    ):
        msg = "You need to know about this."

        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = UserFacingError(msg)

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert "" == out
        assert "ERROR: {}\n".format(msg) == err
        error_log = caplog_text()
        assert msg in error_log
        assert "Traceback (most recent call last):" in error_log


class TestSetupLogging:
    @pytest.mark.parametrize("level", (logging.INFO, logging.ERROR))
    def test_console_log_configured_if_not_present(
        self, level, capsys, logging_sandbox
    ):
        setup_logging(level, logging.INFO)
        logging.log(level, "after setup")
        logging.log(level - 1, "not present")

        _, err = capsys.readouterr()
        assert "after setup" in err
        assert "not present" not in err

    def test_console_log_configured_if_already_present(
        self, capsys, logging_sandbox
    ):
        logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))

        logging.error("before setup")
        setup_logging(logging.INFO, logging.INFO)
        logging.error("after setup")

        # 'before setup' will be in stderr, so check that setup_logging
        # configures the format
        _, err = capsys.readouterr()
        assert "ERROR: before setup" not in err
        assert "ERROR: after setup" in err

    def test_file_log_not_configured_if_not_root(
        self, tmpdir, logging_sandbox
    ):
        log_file = tmpdir.join("log_file")

        setup_logging(logging.INFO, logging.INFO, log_file=log_file.strpath)
        logging.info("after setup")

        assert not log_file.exists()

    @pytest.mark.parametrize("log_filename", (None, "file.log"))
    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    @mock.patch("uaclient.cli.config")
    def test_file_log_configured_if_root(
        self, m_config, _m_getuid, log_filename, logging_sandbox, tmpdir
    ):
        if log_filename is None:
            log_filename = "default.log"
            log_file = tmpdir.join(log_filename)
            m_config.CONFIG_DEFAULTS = {"log_file": log_file.strpath}
        else:
            log_file = tmpdir.join(log_filename)

        setup_logging(logging.INFO, logging.INFO, log_file=log_file.strpath)
        logging.info("after setup")

        assert "after setup" in log_file.read()

    @pytest.mark.parametrize("pre_existing", (True, False))
    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    @mock.patch("uaclient.cli.config")
    def test_file_log_only_readable_by_root(
        self, m_config, _m_getuid, logging_sandbox, tmpdir, pre_existing
    ):
        log_file = tmpdir.join("root-only.log")
        log_path = log_file.strpath

        if pre_existing:
            log_file.write("existing content\n")
            assert 0o600 != stat.S_IMODE(os.lstat(log_path).st_mode)

        setup_logging(logging.INFO, logging.INFO, log_file=log_path)
        logging.info("after setup")

        assert 0o600 == stat.S_IMODE(os.lstat(log_path).st_mode)
        log_content = log_file.read()
        assert "after setup" in log_content
        if pre_existing:
            assert "existing content" in log_content
