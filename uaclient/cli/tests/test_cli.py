import contextlib
import io
import json
import logging
import socket

import mock
import pytest

from uaclient import defaults, exceptions, messages, status
from uaclient.cli import action_help, main
from uaclient.entitlements import get_valid_entitlement_names
from uaclient.exceptions import (
    AlreadyAttachedError,
    LockHeldError,
    UbuntuProError,
    UnattachedError,
)


class TestCLIParser:
    @pytest.mark.parametrize(
        "out_format, expected_return",
        (
            (
                "tabular",
                "\n\n".join(
                    ["Name:\ntest", "Available:\nyes", "Help:\nTest\n\n"]
                ),
            ),
            ("json", {"name": "test", "available": "yes", "help": "Test"}),
        ),
    )
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.status._is_attached")
    def test_help_command_when_unnatached(
        self, m_attached, m_available_resources, out_format, expected_return
    ):
        """
        Test help command for a valid service in an unattached pro client.
        """
        m_args = mock.MagicMock()
        m_service_name = mock.PropertyMock(return_value="test")
        type(m_args).service = m_service_name
        m_format = mock.PropertyMock(return_value=out_format)
        type(m_args).format = m_format

        m_ent_help_info = mock.PropertyMock(return_value="Test")
        m_entitlement_obj = mock.MagicMock()
        type(m_entitlement_obj).help_info = m_ent_help_info

        m_attached.return_value = mock.MagicMock(is_attached=False)

        m_available_resources.return_value = [
            {"name": "test", "available": True}
        ]

        fake_stdout = io.StringIO()
        with mock.patch(
            "uaclient.status.entitlement_factory",
            return_value=m_entitlement_obj,
        ):
            with contextlib.redirect_stdout(fake_stdout):
                action_help(m_args, cfg=None)

        if out_format == "tabular":
            assert expected_return.strip() == fake_stdout.getvalue().strip()
        else:
            assert expected_return == json.loads(fake_stdout.getvalue())

        assert 1 == m_service_name.call_count
        assert 1 == m_ent_help_info.call_count
        assert 1 == m_available_resources.call_count
        assert 1 == m_attached.call_count
        assert 1 == m_format.call_count

    @pytest.mark.parametrize(
        "ent_status, ent_msg",
        (
            (status.ContractStatus.ENTITLED, "yes"),
            (status.ContractStatus.UNENTITLED, "no"),
        ),
    )
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.status._is_attached")
    def test_help_command_when_attached(
        self, m_attached, m_available_resources, ent_status, ent_msg
    ):
        """Test help command for a valid service in an attached pro client."""
        m_args = mock.MagicMock()
        m_service_name = mock.PropertyMock(return_value="test")
        type(m_args).service = m_service_name

        m_ent_help_info = mock.PropertyMock(
            return_value="Test service\nService is being tested"
        )
        m_entitlement_obj = mock.MagicMock()
        type(m_entitlement_obj).help_info = m_ent_help_info

        m_entitlement_obj.contract_status.return_value = ent_status
        m_entitlement_obj.user_facing_status.return_value = (
            status.UserFacingStatus.ACTIVE,
            messages.NamedMessage("test-code", "active"),
        )
        m_ent_name = mock.PropertyMock(return_value="test")
        type(m_entitlement_obj).name = m_ent_name
        m_ent_desc = mock.PropertyMock(return_value="description")
        type(m_entitlement_obj).description = m_ent_desc

        m_attached.return_value = mock.MagicMock(is_attached=True)
        m_available_resources.return_value = [
            {"name": "test", "available": True}
        ]

        status_msg = "enabled" if ent_msg == "yes" else "—"
        ufs_call_count = 1 if ent_msg == "yes" else 0
        ent_name_call_count = 2 if ent_msg == "yes" else 1

        expected_msgs = [
            "Name:\ntest",
            "Entitled:\n{}".format(ent_msg),
            "Status:\n{}".format(status_msg),
        ]

        expected_msgs.append(
            "Help:\nTest service\nService is being tested\n\n"
        )

        expected_msg = "\n\n".join(expected_msgs)

        fake_stdout = io.StringIO()
        with mock.patch(
            "uaclient.status.entitlement_factory",
            return_value=m_entitlement_obj,
        ):
            with contextlib.redirect_stdout(fake_stdout):
                action_help(m_args, cfg=None)

        assert expected_msg.strip() == fake_stdout.getvalue().strip()
        assert 1 == m_service_name.call_count
        assert 1 == m_ent_help_info.call_count
        assert 1 == m_available_resources.call_count
        assert 1 == m_attached.call_count
        assert 1 == m_ent_desc.call_count
        assert ent_name_call_count == m_ent_name.call_count
        assert 1 == m_entitlement_obj.contract_status.call_count
        assert (
            ufs_call_count == m_entitlement_obj.user_facing_status.call_count
        )

    @mock.patch("uaclient.status.get_available_resources")
    def test_help_command_for_invalid_service(self, m_available_resources):
        """Test help command when an invalid service is provided."""
        m_args = mock.MagicMock()
        m_service_name = mock.PropertyMock(return_value="test")
        type(m_args).service = m_service_name

        m_available_resources.return_value = [
            {"name": "ent1", "available": True}
        ]

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            with pytest.raises(UbuntuProError) as excinfo:
                action_help(m_args, cfg=None)

        assert "No help available for 'test'" == str(excinfo.value)
        assert 1 == m_service_name.call_count
        assert 1 == m_available_resources.call_count


M_PATH_UACONFIG = "uaclient.config.UAConfig."


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
    @mock.patch("uaclient.cli.config.UAConfig")
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
        "cli_args,is_tty,should_warn",
        (
            (["pro", "status"], True, False),
            (["pro", "status"], False, True),
            (["pro", "status", "--format", "tabular"], True, False),
            (["pro", "status", "--format", "tabular"], False, True),
            (["pro", "status", "--format", "json"], True, False),
            (["pro", "status", "--format", "json"], False, False),
            (["pro", "security-status"], True, False),
            (["pro", "security-status"], False, True),
            (["pro", "security-status", "--format", "json"], True, False),
            (["pro", "security-status", "--format", "json"], False, False),
        ),
    )
    @mock.patch("uaclient.cli.event.info")
    @mock.patch("uaclient.cli.action_status")
    @mock.patch("uaclient.cli.action_security_status")
    @mock.patch("uaclient.log.setup_cli_logging")
    @mock.patch("sys.stdout.isatty")
    def test_status_human_readable_warning(
        self,
        m_tty,
        _m_setup_logging,
        _m_action_security_status,
        _m_action_status,
        m_event_info,
        cli_args,
        is_tty,
        should_warn,
        FakeConfig,
    ):
        m_tty.return_value = is_tty
        with mock.patch("sys.argv", cli_args):
            with mock.patch(
                "uaclient.config.UAConfig",
                return_value=FakeConfig(),
            ):
                main()

        if should_warn:
            assert [
                mock.call(
                    messages.WARNING_HUMAN_READABLE_OUTPUT.format(
                        command=cli_args[1]
                    ),
                    file_type=mock.ANY,
                )
            ] == m_event_info.call_args_list
        else:
            assert [] == m_event_info.call_args_list


class TestGetValidEntitlementNames:
    @mock.patch(
        "uaclient.cli.entitlements.valid_services",
        return_value=["ent1", "ent2", "ent3"],
    )
    def test_get_valid_entitlements(self, _m_valid_services, FakeConfig):
        service = ["ent1", "ent3", "ent4"]
        expected_ents_found = ["ent1", "ent3"]
        expected_ents_not_found = ["ent4"]

        actual_ents_found, actual_ents_not_found = get_valid_entitlement_names(
            service, cfg=FakeConfig()
        )

        assert expected_ents_found == actual_ents_found
        assert expected_ents_not_found == actual_ents_not_found


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
