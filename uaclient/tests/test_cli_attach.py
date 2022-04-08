import contextlib
import copy
import io
import json

import mock
import pytest
import yaml

from uaclient import event_logger, messages, status
from uaclient.cli import (
    UA_AUTH_TOKEN_URL,
    action_attach,
    attach_parser,
    get_parser,
    main_error_handler,
)
from uaclient.exceptions import (
    AlreadyAttachedError,
    LockHeldError,
    NonRootUserError,
    UrlError,
    UserFacingError,
)
from uaclient.testing.fakes import FakeFile

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
            "createdAt": "2020-05-08T19:02:26Z",
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


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig, capsys, event):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

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


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAttach:
    def test_already_attached(self, _m_getuid, capsys, FakeConfig, event):
        """Check that an already-attached machine emits message and exits 0"""
        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)

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

    @mock.patch(M_PATH + "util.subp")
    def test_lock_file_exists(
        self, m_subp, _m_getuid, capsys, FakeConfig, event
    ):
        """Check when an operation holds a lock file, attach cannot run."""
        cfg = FakeConfig()
        cfg.write_cache("lock", "123:ua disable")
        with pytest.raises(LockHeldError) as exc_info:
            action_attach(mock.MagicMock(), cfg=cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: ua attach.\n"
            "Operation in progress: ua disable (pid:123)"
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
            lock_request="ua attach", lock_holder="lock_holder", pid=1
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

    def test_token_is_a_required_argument(
        self, _m_getuid, FakeConfig, capsys, event
    ):
        """When missing the required token argument, raise a UserFacingError"""
        args = mock.MagicMock(token=None, attach_config=None)
        cfg = FakeConfig()
        with pytest.raises(UserFacingError) as e:
            action_attach(args, cfg=cfg)
        assert messages.ATTACH_REQUIRES_TOKEN.msg == str(e.value.msg)

        args = mock.MagicMock()
        args.token = None
        args.attach_config = None
        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(
                    cfg, "check_lock_info"
                ) as m_check_lock_info:
                    m_check_lock_info.return_value = (0, "lock_holder")
                    main_error_handler(action_attach)(args, cfg)

        expected_msg = messages.ATTACH_REQUIRES_TOKEN
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
    @mock.patch("uaclient.util.should_reboot", return_value=False)
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.jobs.update_messaging.update_apt_and_motd_messages")
    @mock.patch(M_PATH + "contract.request_updated_contract")
    def test_status_updated_when_auto_enable_fails(
        self,
        request_updated_contract,
        m_update_apt_and_motd_msgs,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_get_uid,
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
            cfg.write_cache("machine-token", ENTITLED_MACHINE_TOKEN)
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

    @mock.patch("uaclient.util.should_reboot", return_value=False)
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    @mock.patch("uaclient.jobs.update_messaging.update_apt_and_motd_messages")
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
        _m_should_reboot,
        _m_remove_notice,
        _m_getuid,
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
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
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
    @mock.patch("uaclient.util.should_reboot", return_value=False)
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.jobs.update_messaging.update_apt_and_motd_messages")
    def test_auto_enable_passed_through_to_request_updated_contract(
        self,
        m_update_apt_and_motd_msgs,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_get_uid,
        auto_enable,
        FakeConfig,
    ):
        args = mock.MagicMock(auto_enable=auto_enable, attach_config=None)

        def fake_contract_updates(cfg, contract_token, allow_enable):
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
            return True

        cfg = FakeConfig()
        with mock.patch(M_PATH + "contract.request_updated_contract") as m_ruc:
            m_ruc.side_effect = fake_contract_updates
            action_attach(args, cfg)

        expected_call = mock.call(mock.ANY, mock.ANY, allow_enable=auto_enable)
        assert [expected_call] == m_ruc.call_args_list
        assert [mock.call(cfg)] == m_update_apt_and_motd_msgs.call_args_list

    def test_attach_config_and_token_mutually_exclusive(
        self, _m_getuid, FakeConfig
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
        self, m_attach_with_token, _m_post_cli_attach, _m_getuid, FakeConfig
    ):
        args = mock.MagicMock(
            token=None,
            attach_config=FakeFile(yaml.dump({"token": "faketoken"})),
        )
        cfg = FakeConfig()
        action_attach(args, cfg=cfg)
        assert [
            mock.call(mock.ANY, token="faketoken", allow_enable=True)
        ] == m_attach_with_token.call_args_list

    def test_attach_config_invalid_config(
        self, _m_getuid, FakeConfig, capsys, event
    ):
        args = mock.MagicMock(
            token=None,
            attach_config=FakeFile(
                yaml.dump({"token": "something", "enable_services": "cis"}),
                name="fakename",
            ),
        )
        cfg = FakeConfig()
        with pytest.raises(UserFacingError) as e:
            action_attach(args, cfg=cfg)
        assert "Error while reading fakename: " in e.value.msg

        args.attach_config = FakeFile(
            yaml.dump({"token": "something", "enable_services": "cis"}),
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
                "Expected value with type list but got value: 'cis'"
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
    @mock.patch("uaclient.daemon.stop")
    def test_attach_config_enable_services(
        self,
        _m_daemon_stop,
        m_status,
        m_format_tabular,
        m_handle_unicode,
        m_attach_with_token,
        m_enable,
        _m_getuid,
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
                yaml.dump({"token": "faketoken", "enable_services": ["cis"]})
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
            yaml.dump({"token": "faketoken", "enable_services": ["cis"]})
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

    @mock.patch("uaclient.contract.process_entitlement_delta")
    @mock.patch("uaclient.util.apply_contract_overrides")
    @mock.patch("uaclient.contract.UAContractClient.request_url")
    @mock.patch("uaclient.jobs.update_messaging.update_apt_and_motd_messages")
    def test_attach_when_one_service_fails_to_enable(
        self,
        _m_update_messages,
        m_request_url,
        _m_apply_contract_overrides,
        m_process_entitlement_delta,
        _m_getuid,
        FakeConfig,
        event,
    ):
        args = mock.MagicMock(token="token", attach_config=None)
        cfg = FakeConfig()

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
                        "createdAt": "2019-06-14T06:45:50Z",
                        "externalAccountIDs": [
                            {"IDs": ["id1"], "Origin": "AWS"}
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


@mock.patch(M_PATH + "contract.get_available_resources")
class TestParser:
    def test_attach_parser_usage(self, _m_resources):
        parser = attach_parser(mock.Mock())
        assert "ua attach <token> [flags]" == parser.usage

    def test_attach_parser_prog(self, _m_resources):
        parser = attach_parser(mock.Mock())
        assert "attach" == parser.prog

    def test_attach_parser_optionals_title(self, _m_resources):
        parser = attach_parser(mock.Mock())
        assert "Flags" == parser._optionals.title

    def test_attach_parser_stores_token(self, _m_resources, FakeConfig):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["ua", "attach", "token"]):
            args = full_parser.parse_args()
        assert "token" == args.token

    def test_attach_parser_allows_empty_required_token(
        self, _m_resources, FakeConfig
    ):
        """Token required but parse_args allows none due to action_attach"""
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["ua", "attach"]):
            args = full_parser.parse_args()
        assert None is args.token

    def test_attach_parser_help_points_to_ua_contract_dashboard_url(
        self, _m_resources, capsys, FakeConfig
    ):
        """Contracts' dashboard URL is referenced by ua attach --help."""
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["ua", "attach", "--help"]):
            with pytest.raises(SystemExit):
                full_parser.parse_args()
        assert UA_AUTH_TOKEN_URL in capsys.readouterr()[0]

    def test_attach_parser_accepts_and_stores_no_auto_enable(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch(
            "sys.argv", ["ua", "attach", "--no-auto-enable", "token"]
        ):
            args = full_parser.parse_args()
        assert not args.auto_enable

    def test_attach_parser_defaults_to_auto_enable(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["ua", "attach", "token"]):
            args = full_parser.parse_args()
        assert args.auto_enable

    def test_attach_parser_default_to_cli_format(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["ua", "attach", "token"]):
            args = full_parser.parse_args()
        assert "cli" == args.format

    def test_attach_parser_accepts_format_flag(self, _m_resources, FakeConfig):
        full_parser = get_parser(FakeConfig())
        with mock.patch(
            "sys.argv", ["ua", "attach", "token", "--format", "json"]
        ):
            args = full_parser.parse_args()
        assert "json" == args.format
