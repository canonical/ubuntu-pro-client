import contextlib
import copy
import io
import json
import textwrap

import mock
import pytest

from uaclient import event_logger, http, lock, messages, util
from uaclient.cli import (
    _post_cli_attach,
    action_attach,
    attach_parser,
    get_parser,
    main,
    main_error_handler,
)
from uaclient.exceptions import (
    AlreadyAttachedError,
    LockHeldError,
    MagicAttachInvalidParam,
    MagicAttachTokenError,
    NonRootUserError,
    UbuntuProError,
)
from uaclient.testing.fakes import FakeFile, FakeUbuntuProError
from uaclient.yaml import safe_dump

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro attach <token> [flags]

Attach this machine to an Ubuntu Pro subscription with a token obtained from:
https://ubuntu.com/pro/dashboard

When running this command without a token, it will generate a short code
and prompt you to attach the machine to your Ubuntu Pro account using
a web browser.

positional arguments:
  token                 token obtained for Ubuntu Pro authentication

Flags:
  -h, --help            show this help message and exit
  --no-auto-enable      do not enable any recommended services automatically
  --attach-config ATTACH_CONFIG
                        use the provided attach config file instead of passing
                        the token on the cli
  --format {cli,json}   output in the specified format (default: cli)
"""
)

M_PATH = "uaclient.cli."

# Also used in test_cli_auto_attach.py
BASIC_MACHINE_TOKEN = {
    "availableResources": [],
    "machineToken": "non-empty-token",
    "machineTokenInfo": {
        "machineId": "test_machine_id",
        "contractInfo": {
            "name": "mycontract",
            "id": "contract-1",
            "createdAt": util.parse_rfc3339_date("2020-05-08T19:02:26Z"),
            "effectiveTo": util.parse_rfc3339_date("9999-12-31T00:00:00Z"),
            "resourceEntitlements": [],
            "products": ["free"],
        },
        "accountInfo": {"id": "acct-1", "name": "accountName"},
    },
}

ENTITLED_EXAMPLE_ESM_RESOURCE = {
    "obligations": {"enableByDefault": True},
    "type": "esm-infra",
    "directives": {
        "aptKey": "56F7650A24C9E9ECF87C4D8D4067E40313CB4B13",
        "aptURL": "https://esm.ubuntu.com",
    },
    "affordances": {
        "architectures": [
            "arm64",
            "armhf",
            "i386",
            "ppc64le",
            "s390x",
            "x86_64",
        ],
        "series": ["series-example-1", "series-example-2", "series-example-3"],
    },
    "series": {
        "series-example-1": {
            "directives": {
                "suites": ["example-infra-security", "example-infra-updates"]
            }
        }
    },
    "entitled": True,
}

ENTITLED_MACHINE_TOKEN = copy.deepcopy(BASIC_MACHINE_TOKEN)
ENTITLED_MACHINE_TOKEN["machineTokenInfo"]["contractInfo"][
    "resourceEntitlements"
] = [ENTITLED_EXAMPLE_ESM_RESOURCE]


@mock.patch(M_PATH + "util.we_are_currently_root", return_value=False)
def test_non_root_users_are_rejected(
    m_we_are_currently_root, FakeConfig, capsys, event
):
    """Check that a UID != 0 will receive a message and exit non-zero"""

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_attach(mock.MagicMock(), cfg)

    with pytest.raises(SystemExit):
        with mock.patch.object(
            event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
        ):
            main_error_handler(action_attach)(mock.MagicMock(), cfg)

    expected = {
        "_schema_version": event_logger.JSON_SCHEMA_VERSION,
        "result": "failure",
        "errors": [
            {
                "message": messages.E_NONROOT_USER.msg,
                "message_code": messages.E_NONROOT_USER.name,
                "service": None,
                "type": "system",
            }
        ],
        "failed_services": [],
        "needs_reboot": False,
        "processed_services": [],
        "warnings": [],
    }
    assert expected == json.loads(capsys.readouterr()[0])


class TestActionAttach:
    def test_already_attached(self, capsys, FakeConfig, event):
        """Check that an already-attached machine emits message and exits 0"""
        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(
            account_name=account_name,
        )

        with pytest.raises(AlreadyAttachedError):
            action_attach(mock.MagicMock(), cfg=cfg)

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_attach)(mock.MagicMock(), cfg)

        msg = messages.E_ALREADY_ATTACHED.format(account_name=account_name)
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {"account_name": "test_account"},
                    "message": msg.msg,
                    "message_code": msg.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(capsys.readouterr()[0])

    @mock.patch("uaclient.lock.check_lock_info")
    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        m_sleep,
        m_check_lock_info,
        capsys,
        FakeConfig,
        event,
    ):
        cfg = FakeConfig()
        m_check_lock_info.return_value = (123, "pro disable")
        expected_msg = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro attach", lock_holder="pro disable", pid=123
        )
        """Check when an operation holds a lock file, attach cannot run."""
        with pytest.raises(LockHeldError) as exc_info:
            action_attach(mock.MagicMock(), cfg=cfg)
        assert 12 == m_check_lock_info.call_count
        assert expected_msg.msg == exc_info.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_attach)(mock.MagicMock(), cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "lock_holder": "pro disable",
                        "lock_request": "pro attach",
                        "pid": 123,
                    },
                    "message": expected_msg.msg,
                    "message_code": expected_msg.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(capsys.readouterr()[0])

    @mock.patch(
        "uaclient.status.format_tabular", return_value="mock_tabular_status"
    )
    @mock.patch("uaclient.actions.status", return_value=("", 0))
    @mock.patch(M_PATH + "daemon")
    def test_post_cli_attach(
        self, m_daemon, m_status, m_format_tabular, capsys, FakeConfig
    ):
        cfg = FakeConfig.for_attached_machine()
        _post_cli_attach(cfg)

        assert [mock.call()] == m_daemon.stop.call_args_list
        assert [mock.call(cfg)] == m_daemon.cleanup.call_args_list
        assert [mock.call(cfg)] == m_status.call_args_list
        assert [mock.call("")] == m_format_tabular.call_args_list
        out, _ = capsys.readouterr()
        assert "This machine is now attached to 'test_contract'" in out
        assert "mock_tabular_status" in out

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(
        "uaclient.entitlements.check_entitlement_apt_directives_are_unique",
        return_value=True,
    )
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch("uaclient.files.state_files.attachment_data_file.write")
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    @mock.patch(M_PATH + "contract.UAContractClient.add_contract_machine")
    @mock.patch(M_PATH + "_post_cli_attach")
    def test_happy_path_with_token_arg(
        self,
        m_post_cli,
        contract_machine_attach,
        m_update_apt_and_motd_msgs,
        _m_remove_notice,
        _m_should_reboot,
        _m_attachment_data_file_write,
        m_update_activity_token,
        _m_check_ent_apt_directives,
        _m_check_lock_info,
        FakeConfig,
        event,
    ):
        """A mock-heavy test for the happy path with the contract token arg"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = "contract-token"
        args = mock.MagicMock(token=token, attach_config=None)
        cfg = FakeConfig()

        def fake_contract_attach(contract_token, attachment_dt):
            cfg.machine_token_file.write(BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        contract_machine_attach.side_effect = fake_contract_attach

        with mock.patch.object(lock, "lock_data_file"):
            ret = action_attach(args, cfg)

        assert 0 == ret
        expected_calls = [
            mock.call(contract_token=token, attachment_dt=mock.ANY)
        ]
        assert expected_calls == contract_machine_attach.call_args_list
        assert [mock.call(cfg)] == m_update_apt_and_motd_msgs.call_args_list
        assert 1 == m_update_activity_token.call_count
        assert [mock.call(cfg)] == m_post_cli.call_args_list

    @pytest.mark.parametrize("auto_enable", (True, False))
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch("uaclient.files.state_files.attachment_data_file.write")
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "actions.attach_with_token")
    def test_auto_enable_passed_through_to_attach_with_token(
        self,
        m_attach_with_token,
        _m_post_cli_attach,
        m_update_apt_and_motd_msgs,
        _m_get_available_resources,
        _m_remove_notice,
        _m_should_reboot,
        _m_attachment_data_file_write,
        _m_update_activity_token,
        _m_check_lock_info,
        auto_enable,
        FakeConfig,
    ):
        args = mock.MagicMock(
            auto_enable=auto_enable, attach_config=None, token="token"
        )

        cfg = FakeConfig()
        with mock.patch.object(lock, "lock_data_file"):
            action_attach(args, cfg)

        assert [
            mock.call(mock.ANY, token="token", allow_enable=auto_enable)
        ] == m_attach_with_token.call_args_list

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    def test_attach_config_and_token_mutually_exclusive(
        self,
        _m_check_lock_info,
        FakeConfig,
    ):
        args = mock.MagicMock(
            token="something", attach_config=FakeFile("something")
        )
        cfg = FakeConfig()
        with pytest.raises(UbuntuProError) as e:
            with mock.patch.object(lock, "lock_data_file"):
                action_attach(args, cfg=cfg)

        assert e.value.msg == messages.E_ATTACH_TOKEN_ARG_XOR_CONFIG.msg

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "actions.attach_with_token")
    def test_token_from_attach_config(
        self,
        m_attach_with_token,
        _m_post_cli_attach,
        m_update_activity_token,
        _m_check_lock_info,
        FakeConfig,
    ):
        args = mock.MagicMock(
            token=None,
            attach_config=FakeFile(safe_dump({"token": "faketoken"})),
        )
        cfg = FakeConfig()
        with mock.patch.object(lock, "lock_data_file"):
            action_attach(args, cfg=cfg)

        assert [
            mock.call(mock.ANY, token="faketoken", allow_enable=True)
        ] == m_attach_with_token.call_args_list
        assert 1 == m_update_activity_token.call_count

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    def test_attach_config_invalid_config(
        self,
        _m_check_lock_info,
        FakeConfig,
        capsys,
        event,
    ):
        args = mock.MagicMock(
            token=None,
            attach_config=FakeFile(
                safe_dump({"token": "something", "enable_services": "cis"}),
                name="fakename",
            ),
        )
        cfg = FakeConfig()
        with pytest.raises(UbuntuProError) as e:
            with mock.patch.object(lock, "lock_data_file"):
                action_attach(args, cfg=cfg)
        assert "Error while reading fakename:" in e.value.msg

        args.attach_config = FakeFile(
            safe_dump({"token": "something", "enable_services": "cis"}),
            name="fakename",
        )
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
                    main_error_handler(action_attach)(args, cfg)

        expected_message = messages.E_ATTACH_CONFIG_READ_ERROR.format(
            config_name="fakename",
            error=(
                "Got value with "
                'incorrect type for field "enable_services":\n'
                "Expected value with type list but got type: str"
            ),
        )

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "config_name": "fakename",
                        "error": (
                            "Got value with "
                            'incorrect type for field "enable_services":\n'
                            "Expected value with type list but got type: str"
                        ),
                    },
                    "message": expected_message.msg,
                    "message_code": expected_message.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(capsys.readouterr()[0])

    @pytest.mark.parametrize("auto_enable", (True, False))
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
    @mock.patch(
        M_PATH + "actions.enable_entitlement_by_name",
        return_value=(True, None),
    )
    @mock.patch(M_PATH + "actions.attach_with_token")
    @mock.patch("uaclient.util.handle_unicode_characters")
    @mock.patch("uaclient.status.format_tabular")
    @mock.patch(M_PATH + "actions.status")
    @mock.patch("uaclient.daemon.cleanup")
    @mock.patch("uaclient.daemon.stop")
    def test_attach_config_enable_services(
        self,
        _m_daemon_stop,
        _m_daemon_cleanup,
        m_status,
        m_format_tabular,
        m_handle_unicode,
        m_attach_with_token,
        m_enable,
        m_update_activity_token,
        _m_check_lock_info,
        auto_enable,
        FakeConfig,
        event,
    ):
        m_status.return_value = ("status", 0)
        m_format_tabular.return_value = "status"
        m_handle_unicode.return_value = "status"

        cfg = FakeConfig()
        args = mock.MagicMock(
            token=None,
            attach_config=FakeFile(
                safe_dump({"token": "faketoken", "enable_services": ["cis"]})
            ),
            auto_enable=auto_enable,
        )
        with mock.patch.object(lock, "lock_data_file"):
            action_attach(args, cfg=cfg)

        assert [
            mock.call(mock.ANY, token="faketoken", allow_enable=False)
        ] == m_attach_with_token.call_args_list
        if auto_enable:
            assert [
                mock.call(cfg, "cis", assume_yes=True, allow_beta=True)
            ] == m_enable.call_args_list
        else:
            assert [] == m_enable.call_args_list
        assert 1 == m_update_activity_token.call_count

        args.attach_config = FakeFile(
            safe_dump({"token": "faketoken", "enable_services": ["cis"]})
        )

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
                    main_error_handler(action_attach)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "success",
            "errors": [],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": ["cis"] if auto_enable else [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize(
        "expected_exception,expected_msg,expected_outer_msg",
        (
            (
                FakeUbuntuProError(),
                messages.E_ATTACH_FAILURE_DEFAULT_SERVICES,
                messages.E_ATTACH_FAILURE_DEFAULT_SERVICES,
            ),
            (
                Exception("error"),
                messages.UNEXPECTED_ERROR.format(
                    error_msg="error",
                    log_path="/var/log/ubuntu-advantage.log",
                ),
                messages.E_ATTACH_FAILURE_UNEXPECTED,
            ),
        ),
    )
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(
        "uaclient.entitlements.check_entitlement_apt_directives_are_unique",
        return_value=True,
    )
    @mock.patch("uaclient.files.state_files.attachment_data_file.write")
    @mock.patch("uaclient.entitlements.entitlements_enable_order")
    @mock.patch("uaclient.contract.process_entitlement_delta")
    @mock.patch("uaclient.contract.apply_contract_overrides")
    @mock.patch("uaclient.contract.UAContractClient.request_url")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    def test_attach_when_one_service_fails_to_enable(
        self,
        _m_update_messages,
        m_request_url,
        _m_apply_contract_overrides,
        m_process_entitlement_delta,
        m_enable_order,
        _m_attachment_data_file_write,
        _m_check_ent_apt_directives,
        _m_check_lock_info,
        expected_exception,
        expected_msg,
        expected_outer_msg,
        FakeConfig,
        event,
    ):
        args = mock.MagicMock(token="token", attach_config=None)
        cfg = FakeConfig()

        m_enable_order.return_value = ["test1", "test2"]
        m_process_entitlement_delta.side_effect = [
            ({"test": 123}, True),
            expected_exception,
        ]
        m_request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict={
                "machineToken": "not-null",
                "machineTokenInfo": {
                    "machineId": "machine-id",
                    "accountInfo": {
                        "id": "acct-1",
                        "name": "acc-name",
                        "createdAt": util.parse_rfc3339_date(
                            "2019-06-14T06:45:50Z"
                        ),
                        "externalAccountIDs": [
                            {"IDs": ["id1"], "origin": "AWS"}
                        ],
                    },
                    "contractInfo": {
                        "id": "cid",
                        "name": "test_contract",
                        "resourceTokens": [
                            {"token": "token", "type": "test1"},
                            {"token": "token", "type": "test2"},
                        ],
                        "resourceEntitlements": [
                            {"type": "test1", "aptURL": "apt"},
                            {"type": "test2", "aptURL": "apt"},
                        ],
                    },
                },
            },
            json_list=[],
        )

        fake_stdout = io.StringIO()
        with pytest.raises(SystemExit):
            with contextlib.redirect_stdout(fake_stdout):
                with mock.patch.object(
                    event,
                    "_event_logger_mode",
                    event_logger.EventLoggerMode.JSON,
                ):
                    with mock.patch.object(lock, "lock_data_file"):
                        main_error_handler(action_attach)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "services": [
                            {
                                "code": expected_msg.name,
                                "name": "test2",
                                "title": expected_msg.msg,
                            }
                        ]
                    },
                    "message": expected_outer_msg.msg,
                    "message_code": expected_outer_msg.name,
                    "service": None,
                    "type": "system",
                }
            ],
            "failed_services": ["test2"],
            "needs_reboot": False,
            "processed_services": ["test1"],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(M_PATH + "_initiate")
    @mock.patch(M_PATH + "_wait")
    @mock.patch(M_PATH + "_revoke")
    def test_magic_attach_revoke_token_if_wait_fails(
        self,
        m_revoke,
        m_wait,
        m_initiate,
        _m_check_lock_info,
        FakeConfig,
    ):
        m_initiate.return_value = mock.MagicMock(
            token="token", user_code="user_code"
        )
        m_wait.side_effect = MagicAttachTokenError()
        m_args = mock.MagicMock(token=None, attach_config=None)

        with pytest.raises(MagicAttachTokenError):
            with mock.patch.object(lock, "lock_data_file"):
                action_attach(args=m_args, cfg=FakeConfig())

        assert 1 == m_initiate.call_count
        assert 1 == m_wait.call_count
        assert 1 == m_revoke.call_count

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    def test_magic_attach_fails_if_format_json_param_used(
        self, _m_check_lock_info, FakeConfig
    ):
        m_args = mock.MagicMock(token=None, attach_config=None, format="json")

        with pytest.raises(MagicAttachInvalidParam) as exc_info:
            with mock.patch.object(lock, "lock_data_file"):
                action_attach(args=m_args, cfg=FakeConfig())

        assert (
            "This attach flow does not support --format with value: json"
        ) == exc_info.value.msg


@mock.patch(M_PATH + "contract.get_available_resources")
class TestParser:
    @mock.patch("uaclient.cli.setup_logging")
    def test_attach_help(
        self, _m_resources, _m_setup_logging, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/pro", "attach", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT in out

    def test_attach_parser_usage(self, _m_resources):
        parser = attach_parser(mock.Mock())
        assert "pro attach <token> [flags]" == parser.usage

    def test_attach_parser_prog(self, _m_resources):
        parser = attach_parser(mock.Mock())
        assert "attach" == parser.prog

    def test_attach_parser_optionals_title(self, _m_resources):
        parser = attach_parser(mock.Mock())
        assert "Flags" == parser._optionals.title

    def test_attach_parser_stores_token(self, _m_resources, FakeConfig):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "attach", "token"]):
            args = full_parser.parse_args()
        assert "token" == args.token

    def test_attach_parser_allows_empty_required_token(
        self, _m_resources, FakeConfig
    ):
        """Token required but parse_args allows none due to action_attach"""
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "attach"]):
            args = full_parser.parse_args()
        assert None is args.token

    def test_attach_parser_accepts_and_stores_no_auto_enable(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch(
            "sys.argv", ["pro", "attach", "--no-auto-enable", "token"]
        ):
            args = full_parser.parse_args()
        assert not args.auto_enable

    def test_attach_parser_defaults_to_auto_enable(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "attach", "token"]):
            args = full_parser.parse_args()
        assert args.auto_enable

    def test_attach_parser_default_to_cli_format(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "attach", "token"]):
            args = full_parser.parse_args()
        assert "cli" == args.format

    def test_attach_parser_accepts_format_flag(self, _m_resources, FakeConfig):
        full_parser = get_parser(FakeConfig())
        with mock.patch(
            "sys.argv", ["pro", "attach", "token", "--format", "json"]
        ):
            args = full_parser.parse_args()
        assert "json" == args.format
