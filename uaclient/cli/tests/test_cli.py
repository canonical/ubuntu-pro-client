import contextlib
import logging
import socket

import mock
import pytest

from uaclient import defaults, exceptions, messages
from uaclient.cli import _warn_about_output_redirection, main
from uaclient.exceptions import (
    AlreadyAttachedError,
    LockHeldError,
    UnattachedError,
)


class TestMain:
    @pytest.mark.parametrize(
        "exception,expected_error_msg,expected_log",
        (
            (
                TypeError("'NoneType' object is not subscriptable"),
                messages.UNEXPECTED_ERROR.format(
                    error_msg="'NoneType' object is not subscriptable",
                    log_path="/var/log/ubuntu-advantage.log",
                ),
                "Unhandled exception, please file a bug",
            ),
        ),
    )
    @mock.patch("uaclient.cli.event.info")
    @mock.patch("uaclient.cli.LOG.exception")
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_errors_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        m_log_exception,
        m_event_info,
        event,
        exception,
        expected_error_msg,
        expected_log,
        FakeConfig,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = exception

        with pytest.raises(SystemExit) as excinfo:
            with mock.patch("sys.argv", ["/usr/bin/ua", "subcmd"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()

        exc = excinfo.value
        assert 1 == exc.code
        assert [
            mock.call(info_msg=expected_error_msg.msg, file_type=mock.ANY)
        ] == m_event_info.call_args_list
        assert [mock.call(expected_log)] == m_log_exception.call_args_list

    @pytest.mark.parametrize(
        "exception,expected_log",
        (
            (
                KeyboardInterrupt,
                "KeyboardInterrupt",
            ),
        ),
    )
    @mock.patch("uaclient.cli.LOG.error")
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_interrupt_errors_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        m_log_error,
        exception,
        expected_log,
        FakeConfig,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = exception

        with pytest.raises(SystemExit) as excinfo:
            with mock.patch("sys.argv", ["/usr/bin/ua", "subcmd"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()

        exc = excinfo.value
        assert 1 == exc.code

        assert [mock.call(expected_log)] == m_log_error.call_args_list

    @pytest.mark.parametrize(
        "exception,expected_exit_code",
        [
            (UnattachedError(), 1),
            (AlreadyAttachedError(account_name=mock.MagicMock()), 2),
            (
                LockHeldError(
                    pid="123",
                    lock_request="pro reboot-cmds",
                    lock_holder="pro auto-attach",
                ),
                1,
            ),
        ],
    )
    @mock.patch("uaclient.cli.event.info")
    @mock.patch("uaclient.cli.LOG.error")
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_user_facing_error_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        m_log_error,
        m_event_info,
        event,
        exception,
        expected_exit_code,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = exception
        expected_msg = exception.msg

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert expected_exit_code == exc.code

        assert [
            mock.call(info_msg=expected_msg, file_type=mock.ANY)
        ] == m_event_info.call_args_list
        assert [mock.call(expected_msg)] == m_log_error.call_args_list

    @pytest.mark.parametrize(
        ["error_url", "expected_log_call"],
        (
            (
                "http://nowhere.com",
                mock.call(
                    "Failed to access URL: %s",
                    "http://nowhere.com",
                    exc_info=mock.ANY,
                ),
            ),
        ),
    )
    @mock.patch("uaclient.cli.event.info")
    @mock.patch("uaclient.cli.LOG.exception")
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_url_error_handled_gracefully(
        self,
        m_get_parser,
        _m_setup_logging,
        m_log_exception,
        m_event_info,
        error_url,
        expected_log_call,
    ):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = exceptions.ConnectivityError(
            cause=socket.gaierror(-2, "Name or service not known"),
            url=error_url,
        )

        with pytest.raises(SystemExit) as excinfo:
            main(["some", "args"])

        exc = excinfo.value
        assert 1 == exc.code

        assert [
            mock.call(
                info_msg=messages.E_CONNECTIVITY_ERROR.format(
                    url=error_url,
                    cause_error="[Errno -2] Name or service not known",
                ).msg,
                file_type=mock.ANY,
            )
        ] == m_event_info.call_args_list
        assert [expected_log_call] == m_log_exception.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    def test_command_line_is_logged(
        self, _m_get_parser, _m_setup_logging, caplog_text
    ):
        main(["some", "args"])

        log = caplog_text()

        assert "['some', 'args']" in log

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    @mock.patch(
        "uaclient.cli.util.get_pro_environment",
        return_value={"UA_ENV": "YES", "UA_FEATURES_WOW": "XYZ"},
    )
    def test_environment_is_logged(
        self,
        _m_pro_environment,
        _m_get_parser,
        _m_setup_logging,
        caplog_text,
    ):
        main(["some", "args"])

        log = caplog_text()

        assert "UA_ENV=YES" in log
        assert "UA_FEATURES_WOW=XYZ" in log

    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("uaclient.cli.get_parser")
    @mock.patch("uaclient.cli.UAConfig")
    @pytest.mark.parametrize("config_error", [True, False])
    def test_setup_logging_with_defaults(
        self,
        m_config,
        _m_get_parser,
        m_setup_logging,
        config_error,
        tmpdir,
        FakeConfig,
    ):
        log_file = tmpdir.join("file.log")
        cfg = FakeConfig({"log_file": log_file.strpath})
        if not config_error:
            m_config.return_value = cfg
        else:
            m_config.side_effect = OSError("Error reading UAConfig")

        with contextlib.suppress(SystemExit):
            main(["some", "args"])

        expected_setup_logging_calls = [
            mock.call(
                defaults.CONFIG_DEFAULTS["log_level"],
                defaults.CONFIG_DEFAULTS["log_file"],
            ),
        ]

        if not config_error:
            expected_setup_logging_calls.append(
                mock.call(mock.ANY, cfg.log_file),
            )

        assert expected_setup_logging_calls == m_setup_logging.call_args_list

    @pytest.mark.parametrize(
        "command,out_format,is_tty,should_warn",
        (
            ("status", None, True, False),
            ("status", None, False, True),
            ("status", "tabular", True, False),
            ("status", "tabular", False, True),
            ("status", "json", True, False),
            ("status", "json", False, False),
            ("security-status", None, True, False),
            ("security-status", None, False, True),
            ("security-status", "json", True, False),
            ("security-status", "json", False, False),
        ),
    )
    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @mock.patch("uaclient.cli.event.info")
    @mock.patch("sys.stdout.isatty")
    def test_status_human_readable_warning(
        self,
        m_tty,
        m_event_info,
        command,
        out_format,
        is_tty,
        should_warn,
        caplog_text,
    ):
        m_tty.return_value = is_tty

        m_args = mock.MagicMock()
        m_args.command = command
        m_args.format = out_format

        _warn_about_output_redirection(m_args)

        if should_warn:
            assert [
                mock.call(
                    messages.WARNING_HUMAN_READABLE_OUTPUT.format(
                        command=command
                    ),
                    file_type=mock.ANY,
                )
            ] == m_event_info.call_args_list
            assert (
                "Not in a tty and human-readable command called"
                in caplog_text()
            )
        else:
            assert [] == m_event_info.call_args_list
            assert (
                "Not in a tty and human-readable command called"
                not in caplog_text()
            )


# There is a fixture for this function to avoid leaking, as it is called in
# the main CLI function. So, instead of importing it directly, we are using
# the reference for the fixture to test it.
class TestWarnAboutNewVersion:
    @pytest.mark.parametrize("new_version", (None, "1.2.3"))
    @mock.patch("uaclient.cli.event.info")
    @mock.patch("uaclient.cli.version.check_for_new_version")
    def test_warn_about_new_version(
        self,
        m_check_version,
        m_event_info,
        new_version,
        _warn_about_new_version,
    ):
        m_check_version.return_value = new_version

        _warn_about_new_version()

        if new_version:
            assert [
                mock.call(
                    messages.WARN_NEW_VERSION_AVAILABLE_CLI.format(
                        version=new_version
                    ),
                    file_type=mock.ANY,
                )
            ] == m_event_info.call_args_list
        else:
            assert [] == m_event_info.call_args_list

    @pytest.mark.parametrize("command", ("api", "status"))
    @pytest.mark.parametrize("out_format", (None, "tabular", "json"))
    @mock.patch("uaclient.cli.event.info")
    @mock.patch(
        "uaclient.cli.version.check_for_new_version", return_value="1.2.3"
    )
    def test_dont_show_for_api_calls(
        self,
        m_check_version,
        m_event_info,
        command,
        out_format,
        _warn_about_new_version,
    ):
        m_check_version.return_value = "1"

        args = mock.MagicMock()
        args.command = command
        args.format = out_format

        if not out_format:
            del args.format

        _warn_about_new_version(args)

        if command != "api" and out_format != "json":
            assert [
                mock.call(
                    messages.WARN_NEW_VERSION_AVAILABLE_CLI.format(
                        version="1"
                    ),
                    file_type=mock.ANY,
                )
            ] == m_event_info.call_args_list
        else:
            assert [] == m_event_info.call_args_list
