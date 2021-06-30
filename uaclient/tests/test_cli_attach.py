import copy
import mock

import pytest

from uaclient.cli import (
    UA_AUTH_TOKEN_URL,
    action_attach,
    attach_parser,
    get_parser,
)
from uaclient.exceptions import (
    AlreadyAttachedError,
    LockHeldError,
    NonRootUserError,
    UserFacingError,
)
from uaclient import status
from uaclient.util import UrlError

M_PATH = "uaclient.cli."

# Also used in test_cli_auto_attach.py
BASIC_MACHINE_TOKEN = {
    "availableResources": [],
    "machineToken": "non-empty-token",
    "machineTokenInfo": {
        "contractInfo": {
            "name": "mycontract",
            "id": "contract-1",
            "resourceEntitlements": [],
        },
        "accountInfo": {"id": "acct-1", "name": "accountName"},
    },
}

ENTITLED_TRUSTY_ESM_RESOURCE = {
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
        "series": ["precise", "trusty", "xenial", "bionic"],
    },
    "series": {
        "trusty": {
            "directives": {
                "suites": ["trusty-infra-security", "trusty-infra-updates"]
            }
        }
    },
    "entitled": True,
}

ENTITLED_MACHINE_TOKEN = copy.deepcopy(BASIC_MACHINE_TOKEN)
ENTITLED_MACHINE_TOKEN["machineTokenInfo"]["contractInfo"][
    "resourceEntitlements"
] = [ENTITLED_TRUSTY_ESM_RESOURCE]


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_attach(mock.MagicMock(), cfg)


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAttach:
    def test_already_attached(self, _m_getuid, capsys, FakeConfig):
        """Check that an already-attached machine emits message and exits 0"""
        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)

        with pytest.raises(AlreadyAttachedError):
            action_attach(mock.MagicMock(), cfg)

    @mock.patch(M_PATH + "util.subp")
    def test_lock_file_exists(self, m_subp, _m_getuid, capsys, FakeConfig):
        """Check when an operation holds a lock file, attach cannot run."""
        cfg = FakeConfig()

        cfg.write_cache("lock", "123:ua disable")
        with pytest.raises(LockHeldError) as exc_info:
            action_attach(mock.MagicMock(), cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: ua attach.\n"
            "Operation in progress: ua disable (pid:123)"
        ) == exc_info.value.msg

    def test_token_is_a_required_argument(self, _m_getuid, FakeConfig):
        """When missing the required token argument, raise a UserFacingError"""
        args = mock.MagicMock()
        args.token = None
        with pytest.raises(UserFacingError) as e:
            action_attach(args, FakeConfig())
        assert status.MESSAGE_ATTACH_REQUIRES_TOKEN == str(e.value)

    @pytest.mark.parametrize(
        "error_class, error_str, expected_log",
        (
            (UrlError, "Forbidden", "Forbidden\nTraceback"),
            (
                UserFacingError,
                "Unable to attach default services",
                "WARNING  Unable to attach default services",
            ),
        ),
    )
    @mock.patch("uaclient.util.should_reboot", return_value=False)
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.update_ua_messages")
    @mock.patch(M_PATH + "contract.request_updated_contract")
    def test_status_updated_when_auto_enable_fails(
        self,
        request_updated_contract,
        update_ua_messages,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_get_uid,
        error_class,
        error_str,
        expected_log,
        caplog_text,
        FakeConfig,
    ):
        """If auto-enable of a service fails, attach status is updated."""
        token = "contract-token"
        args = mock.MagicMock(token=token)
        cfg = FakeConfig()
        cfg.status()  # persist unattached status
        # read persisted status cache from disk
        orig_unattached_status = cfg.read_cache("status-cache")

        def fake_request_updated_contract(cfg, contract_token, allow_enable):
            cfg.write_cache("machine-token", ENTITLED_MACHINE_TOKEN)
            raise error_class(error_str)

        request_updated_contract.side_effect = fake_request_updated_contract
        ret = action_attach(args, cfg)
        assert 1 == ret
        assert cfg.is_attached
        # Assert updated status cache is written to disk
        assert orig_unattached_status != cfg.read_cache(
            "status-cache"
        ), "Did not persist on disk status during attach failure"
        logs = caplog_text()
        assert expected_log in logs
        assert [mock.call(cfg)] == update_ua_messages.call_args_list

    @mock.patch("uaclient.util.should_reboot", return_value=False)
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    @mock.patch("uaclient.config.update_ua_messages")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_contract_machine_attach"
    )
    @mock.patch(M_PATH + "action_status")
    def test_happy_path_with_token_arg(
        self,
        action_status,
        contract_machine_attach,
        update_ua_messages,
        _m_should_reboot,
        _m_remove_notice,
        _m_getuid,
        FakeConfig,
    ):
        """A mock-heavy test for the happy path with the contract token arg"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = "contract-token"
        args = mock.MagicMock(token=token)
        cfg = FakeConfig()

        def fake_contract_attach(contract_token):
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        contract_machine_attach.side_effect = fake_contract_attach

        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == action_status.call_count
        expected_calls = [mock.call(contract_token=token)]
        assert expected_calls == contract_machine_attach.call_args_list
        assert [mock.call(cfg)] == update_ua_messages.call_args_list

    @pytest.mark.parametrize("auto_enable", (True, False))
    @mock.patch("uaclient.util.should_reboot", return_value=False)
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.update_ua_messages")
    def test_auto_enable_passed_through_to_request_updated_contract(
        self,
        update_ua_messages,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_get_uid,
        auto_enable,
        FakeConfig,
    ):
        args = mock.MagicMock(auto_enable=auto_enable)

        def fake_contract_updates(cfg, contract_token, allow_enable):
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
            return True

        cfg = FakeConfig()
        with mock.patch(M_PATH + "contract.request_updated_contract") as m_ruc:
            m_ruc.side_effect = fake_contract_updates
            action_attach(args, cfg)

        expected_call = mock.call(mock.ANY, mock.ANY, allow_enable=auto_enable)
        assert [expected_call] == m_ruc.call_args_list
        assert [mock.call(cfg)] == update_ua_messages.call_args_list


class TestParser:
    def test_attach_parser_usage(self):
        parser = attach_parser(mock.Mock())
        assert "ua attach <token> [flags]" == parser.usage

    def test_attach_parser_prog(self):
        parser = attach_parser(mock.Mock())
        assert "attach" == parser.prog

    def test_attach_parser_optionals_title(self):
        parser = attach_parser(mock.Mock())
        assert "Flags" == parser._optionals.title

    def test_attach_parser_stores_token(self):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "attach", "token"]):
            args = full_parser.parse_args()
        assert "token" == args.token

    def test_attach_parser_allows_empty_required_token(self):
        """Token required but parse_args allows none due to action_attach"""
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "attach"]):
            args = full_parser.parse_args()
        assert None is args.token

    def test_attach_parser_help_points_to_ua_contract_dashboard_url(
        self, capsys
    ):
        """Contracts' dashboard URL is referenced by ua attach --help."""
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "attach", "--help"]):
            with pytest.raises(SystemExit):
                full_parser.parse_args()
        assert UA_AUTH_TOKEN_URL in capsys.readouterr()[0]

    def test_attach_parser_accepts_and_stores_no_auto_enable(self):
        full_parser = get_parser()
        with mock.patch(
            "sys.argv", ["ua", "attach", "--no-auto-enable", "token"]
        ):
            args = full_parser.parse_args()
        assert not args.auto_enable

    def test_attach_parser_defaults_to_auto_enable(self):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "attach", "token"]):
            args = full_parser.parse_args()
        assert args.auto_enable
