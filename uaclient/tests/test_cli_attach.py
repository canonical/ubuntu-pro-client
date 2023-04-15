import contextlib
import copy
import io
import json
import textwrap

import mock
import pytest

from uaclient import event_logger, messages, status, util
from uaclient.cli import (
    UA_AUTH_TOKEN_URL,
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
    UrlError,
    UserFacingError,
)
from uaclient.testing.fakes import FakeFile
from uaclient.yaml import safe_dump

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro attach <token> [flags]

Attach this machine to Ubuntu Pro with a token obtained from:
https://ubuntu.com/pro

When running this command without a token, it will generate a short code
and prompt you to attach the machine to your Ubuntu Pro account using
a web browser.

positional arguments:
  token                 token obtained for Ubuntu Pro authentication:
                        https://auth.contracts.canonical.com

Flags:
  -h, --help            show this help message and exit
  --no-auto-enable      do not enable any recommended services automatically
  --attach-config ATTACH_CONFIG
                        use the provided attach config file instead of passing
                        the token on the cli
  --format {cli,json}   output enable in the specified format (default: cli)
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
                "message": messages.NONROOT_USER.msg,
                "message_code": messages.NONROOT_USER.name,
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

        msg = messages.ALREADY_ATTACHED.format(account_name=account_name)
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
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

    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        capsys,
        FakeConfig,
        event,
    ):
        """Check when an operation holds a lock file, attach cannot run."""
        cfg = FakeConfig()
        cfg.write_cache("lock", "123:pro disable")
        with pytest.raises(LockHeldError) as exc_info:
            action_attach(mock.MagicMock(), cfg=cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: pro attach.\n"
            "Operation in progress: pro disable (pid:123)"
        ) == exc_info.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(
                    cfg, "check_lock_info"
                ) as m_check_lock_info:
                    m_check_lock_info.return_value = (1, "lock_holder")
                    main_error_handler(action_attach)(mock.MagicMock(), cfg)

        expected_msg = messages.LOCK_HELD_ERROR.format(
            lock_request="pro attach", lock_holder="lock_holder", pid=1
        )
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
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

    @pytest.mark.parametrize(
        "error_class, error_str",
        (
            (UrlError, "Forbidden"),
            (UserFacingError, "Unable to attach default services"),
        ),
    )
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    @mock.patch(M_PATH + "contract.request_updated_contract")
    def test_status_updated_when_auto_enable_fails(
        self,
        request_updated_contract,
        m_update_apt_and_motd_msgs,
        _m_get_available_resources,
        _m_remove_notice,
        _m_should_reboot,
        error_class,
        error_str,
        FakeConfig,
        event,
    ):
        """If auto-enable of a service fails, attach status is updated."""
        token = "contract-token"
        args = mock.MagicMock(token=token, attach_config=None)
        cfg = FakeConfig()
        status.status(cfg=cfg)  # persist unattached status
        # read persisted status cache from disk
        orig_unattached_status = cfg.read_cache("status-cache")

        def fake_request_updated_contract(cfg, contract_token, allow_enable):
            cfg.machine_token_file.write(ENTITLED_MACHINE_TOKEN)
            raise error_class(error_str)

        request_updated_contract.side_effect = fake_request_updated_contract
        with pytest.raises(SystemExit) as excinfo:
            main_error_handler(action_attach)(args, cfg)

        assert 1 == excinfo.value.code
        assert cfg.is_attached
        # Assert updated status cache is written to disk
        assert orig_unattached_status != cfg.read_cache(
            "status-cache"
        ), "Did not persist on disk status during attach failure"
        assert [mock.call(cfg)] == m_update_apt_and_motd_msgs.call_args_list

    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_contract_machine_attach"
    )
    @mock.patch("uaclient.actions.status", return_value=("", 0))
    @mock.patch("uaclient.status.format_tabular")
    def test_happy_path_with_token_arg(
        self,
        m_format_tabular,
        m_status,
        contract_machine_attach,
        m_update_apt_and_motd_msgs,
        _m_remove_notice,
        _m_should_reboot,
        FakeConfig,
        event,
    ):
        """A mock-heavy test for the happy path with the contract token arg"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = "contract-token"
        args = mock.MagicMock(token=token, attach_config=None)
        cfg = FakeConfig()

        def fake_contract_attach(contract_token):
            cfg.machine_token_file.write(BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        contract_machine_attach.side_effect = fake_contract_attach

        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == m_status.call_count
        assert 1 == m_format_tabular.call_count
        expected_calls = [mock.call(contract_token=token)]
        assert expected_calls == contract_machine_attach.call_args_list
        assert [mock.call(cfg)] == m_update_apt_and_motd_msgs.call_args_list

        # We need to do that since all config objects in this
        # test will share the same data dir. Since this will
        # test a successful attach, in the end we write a machine token
        # file, which will make all other cfg objects here to report
        # as attached
        cfg.delete_cache()
        cfg.machine_token_file.delete()

        cfg = FakeConfig()
        args = mock.MagicMock(token=token, attach_config=None)
        with mock.patch.object(
            event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
        ):
            with mock.patch.object(
                cfg, "check_lock_info"
            ) as m_check_lock_info:
                m_check_lock_info.return_value = (0, "lock_holder")
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    main_error_handler(action_attach)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "success",
            "errors": [],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": [],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @pytest.mark.parametrize("auto_enable", (True, False))
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    def test_auto_enable_passed_through_to_request_updated_contract(
        self,
        m_update_apt_and_motd_msgs,
        _m_get_available_resources,
        _m_remove_notice,
        _m_should_reboot,
        auto_enable,
        FakeConfig,
    ):
        args = mock.MagicMock(auto_enable=auto_enable, attach_config=None)

        def fake_contract_updates(cfg, contract_token, allow_enable):
            cfg.machine_token_file.write(BASIC_MACHINE_TOKEN)
            return True

        cfg = FakeConfig()
        with mock.patch(M_PATH + "contract.request_updated_contract") as m_ruc:
            m_ruc.side_effect = fake_contract_updates
            action_attach(args, cfg)

        expected_call = mock.call(mock.ANY, mock.ANY, allow_enable=auto_enable)
        assert [expected_call] == m_ruc.call_args_list
        assert [mock.call(cfg)] == m_update_apt_and_motd_msgs.call_args_list

    def test_attach_config_and_token_mutually_exclusive(
        self,
        FakeConfig,
    ):
        args = mock.MagicMock(
            token="something", attach_config=FakeFile("something")
        )
        cfg = FakeConfig()
        with pytest.raises(UserFacingError) as e:
            action_attach(args, cfg=cfg)
        assert e.value.msg == messages.ATTACH_TOKEN_ARG_XOR_CONFIG.msg

    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "actions.attach_with_token")
    def test_token_from_attach_config(
        self,
        m_attach_with_token,
        _m_post_cli_attach,
        FakeConfig,
    ):
        args = mock.MagicMock(
            token=None,
            attach_config=FakeFile(safe_dump({"token": "faketoken"})),
        )
        cfg = FakeConfig()
        action_attach(args, cfg=cfg)
        assert [
            mock.call(mock.ANY, token="faketoken", allow_enable=True)
        ] == m_attach_with_token.call_args_list

    def test_attach_config_invalid_config(
        self,
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
        with pytest.raises(UserFacingError) as e:
            action_attach(args, cfg=cfg)
        assert "Error while reading fakename: " in e.value.msg

        args.attach_config = FakeFile(
            safe_dump({"token": "something", "enable_services": "cis"}),
            name="fakename",
        )
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_attach)(args, cfg)

        expected_message = messages.ATTACH_CONFIG_READ_ERROR.format(
            config_name="fakename",
            error=(
                "Got value with "
                'incorrect type for field\n"enable_services": '
                "Expected value with type list but got type: str"
            ),
        )

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
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

        args.attach_config = FakeFile(
            safe_dump({"token": "faketoken", "enable_services": ["cis"]})
        )

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
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
        FakeConfig,
        event,
    ):
        args = mock.MagicMock(token="token", attach_config=None)
        cfg = FakeConfig()

        m_enable_order.return_value = ["test1", "test2"]
        m_process_entitlement_delta.side_effect = [
            ({"test": 123}, True),
            UserFacingError("error"),
        ]
        m_request_url.return_value = (
            {
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
            None,
        )

        fake_stdout = io.StringIO()
        with pytest.raises(SystemExit):
            with contextlib.redirect_stdout(fake_stdout):
                with mock.patch.object(
                    event,
                    "_event_logger_mode",
                    event_logger.EventLoggerMode.JSON,
                ):
                    main_error_handler(action_attach)(args, cfg)

        expected_msg = messages.ATTACH_FAILURE_DEFAULT_SERVICES
        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": expected_msg.msg,
                    "message_code": expected_msg.name,
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

    @mock.patch(M_PATH + "_initiate")
    @mock.patch(M_PATH + "_wait")
    @mock.patch(M_PATH + "_revoke")
    def test_magic_attach_revoke_token_if_wait_fails(
        self,
        m_revoke,
        m_wait,
        m_initiate,
        FakeConfig,
    ):
        m_initiate.return_value = mock.MagicMock(
            token="token", user_code="user_code"
        )
        m_wait.side_effect = MagicAttachTokenError()
        m_args = mock.MagicMock(token=None, attach_config=None)

        with pytest.raises(MagicAttachTokenError):
            action_attach(args=m_args, cfg=FakeConfig())

        assert 1 == m_initiate.call_count
        assert 1 == m_wait.call_count
        assert 1 == m_revoke.call_count

    def test_magic_attach_fails_if_format_json_param_used(self, FakeConfig):
        m_args = mock.MagicMock(token=None, attach_config=None, format="json")

        with pytest.raises(MagicAttachInvalidParam) as exc_info:
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

    def test_attach_parser_help_points_to_ua_contract_dashboard_url(
        self, _m_resources, capsys, FakeConfig
    ):
        """Contracts' dashboard URL is referenced by pro attach --help."""
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "attach", "--help"]):
            with pytest.raises(SystemExit):
                full_parser.parse_args()
        assert UA_AUTH_TOKEN_URL in capsys.readouterr()[0]

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
