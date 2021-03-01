import mock

import pytest

from uaclient.cli import (
    action_auto_attach,
    auto_attach_parser,
    get_parser,
    _get_contract_token_from_cloud_identity,
)
from uaclient.contract import ContractAPIError
from uaclient.exceptions import (
    AlreadyAttachedError,
    LockHeldError,
    NonRootUserError,
    NonAutoAttachImageError,
    UserFacingError,
)
from uaclient import status
from uaclient.tests.test_cli_attach import BASIC_MACHINE_TOKEN
from uaclient import util

M_PATH = "uaclient.cli."
M_ID_PATH = "uaclient.clouds.identity."


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_auto_attach(mock.MagicMock(), cfg)


class TestGetContractTokenFromCloudIdentity:
    def fake_instance_factory(self):
        m_instance = mock.Mock()
        m_instance.identity_doc = "pkcs7-validated-by-backend"
        return m_instance

    @pytest.mark.parametrize(
        "cloud_type", ("awslookalike", "unsupported-cloud", "azure2", "!aws")
    )
    @mock.patch(M_ID_PATH + "get_cloud_type")
    def test_non_aws_cloud_type_raises_error(
        self, m_get_cloud_type, cloud_type, FakeConfig
    ):
        """Non-aws clouds will error."""
        m_get_cloud_type.return_value = cloud_type
        with pytest.raises(NonAutoAttachImageError) as excinfo:
            _get_contract_token_from_cloud_identity(FakeConfig())
        assert status.MESSAGE_UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
            cloud_type=cloud_type
        ) == str(excinfo.value)

    @pytest.mark.parametrize(
        "http_msg,http_code,http_response",
        (
            ("Not found", 404, {"message": "missing instance information"}),
            (
                "Forbidden",
                403,
                {"message": "forbidden: cannot verify signing certificate"},
            ),
        ),
    )
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_ID_PATH + "get_instance_id", return_value="old-iid")
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_aws_cloud_type_non_auto_attach_returns_no_token(
        self,
        cloud_instance_factory,
        get_instance_id,
        request_auto_attach_contract_token,
        http_msg,
        http_code,
        http_response,
        FakeConfig,
    ):
        """VMs running on non-auto-attach images do not return a token."""
        cloud_instance_factory.side_effect = self.fake_instance_factory
        request_auto_attach_contract_token.side_effect = ContractAPIError(
            util.UrlError(
                http_msg, code=http_code, url="http://me", headers={}
            ),
            error_response=http_response,
        )
        with pytest.raises(NonAutoAttachImageError) as excinfo:
            _get_contract_token_from_cloud_identity(FakeConfig())
        assert status.MESSAGE_UNSUPPORTED_AUTO_ATTACH == str(excinfo.value)

    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_ID_PATH + "get_instance_id", return_value="my-iid")
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_raise_unexpected_errors(
        self,
        cloud_instance_factory,
        _get_instance_id,
        request_auto_attach_contract_token,
        FakeConfig,
    ):
        """Any unexpected errors will be raised."""

        cloud_instance_factory.side_effect = self.fake_instance_factory
        unexpected_error = ContractAPIError(
            util.UrlError(
                "Server error", code=500, url="http://me", headers={}
            ),
            error_response={"message": "something unexpected"},
        )
        request_auto_attach_contract_token.side_effect = unexpected_error

        with pytest.raises(ContractAPIError) as excinfo:
            _get_contract_token_from_cloud_identity(FakeConfig())
        assert unexpected_error == excinfo.value

    @mock.patch(M_ID_PATH + "get_instance_id", return_value="my-iid")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_return_token_from_contract_server_using_identity_doc(
        self,
        cloud_instance_factory,
        request_auto_attach_contract_token,
        get_instance_id,
        FakeConfig,
    ):
        """Return token from the contract server using the identity."""

        cloud_instance_factory.side_effect = self.fake_instance_factory

        def fake_contract_token(instance):
            return {"contractToken": "myPKCS7-token"}

        request_auto_attach_contract_token.side_effect = fake_contract_token

        cfg = FakeConfig()
        assert "myPKCS7-token" == _get_contract_token_from_cloud_identity(cfg)
        # instance-id is persisted for next auto-attach call
        assert 1 == get_instance_id.call_count
        assert "my-iid" == cfg.read_cache("instance-id")

    @pytest.mark.parametrize(
        "iid_response,calls_detach", (("old-iid", False), ("new-iid", True))
    )
    @mock.patch(M_ID_PATH + "get_instance_id")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_delta_in_instance_id_forces_detach(
        self,
        cloud_instance_factory,
        request_auto_attach_contract_token,
        get_instance_id,
        iid_response,
        calls_detach,
        FakeConfig,
    ):
        """When instance-id changes since last attach, call detach."""

        get_instance_id.return_value = iid_response
        cloud_instance_factory.side_effect = self.fake_instance_factory

        def fake_contract_token(instance):
            return {"contractToken": "myPKCS7-token"}

        request_auto_attach_contract_token.side_effect = fake_contract_token

        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)
        # persist old instance-id value
        cfg.write_cache("instance-id", "old-iid")

        if calls_detach:
            with mock.patch(M_PATH + "_detach") as m_detach:
                m_detach.return_value = 0
                assert (
                    "myPKCS7-token"
                    == _get_contract_token_from_cloud_identity(cfg)
                )
            assert [mock.call(cfg, assume_yes=True)] == m_detach.call_args_list
        else:
            with pytest.raises(AlreadyAttachedError):
                _get_contract_token_from_cloud_identity(cfg)
        # current instance-id is persisted for next auto-attach call
        assert iid_response == cfg.read_cache("instance-id")

    @mock.patch(M_PATH + "_detach")
    @mock.patch(M_ID_PATH + "get_instance_id")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_failed_detach_on_changed_instance_id_raises_errors(
        self,
        cloud_instance_factory,
        request_auto_attach_contract_token,
        get_instance_id,
        m_detach,
        FakeConfig,
    ):
        """When instance-id changes since last attach, call detach."""

        get_instance_id.return_value = "new-iid"
        cloud_instance_factory.side_effect = self.fake_instance_factory

        def fake_contract_token(instance):
            return {"contractToken": "myPKCS7-token"}

        request_auto_attach_contract_token.side_effect = fake_contract_token
        m_detach.return_value = 1  # Failure to auto-detach

        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)
        # persist old instance-id value
        cfg.write_cache("instance-id", "old-iid")

        with pytest.raises(UserFacingError) as err:
            assert "myPKCS7-token" == _get_contract_token_from_cloud_identity(
                cfg
            )
        assert status.MESSAGE_DETACH_AUTOMATION_FAILURE == str(err.value)

    @pytest.mark.parametrize("iid_curr, iid_old", (("123", 123), (123, "123")))
    @mock.patch(M_ID_PATH + "get_instance_id")
    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_numeric_iid_does_not_trigger_auto_attach(
        self,
        cloud_instance_factory,
        request_auto_attach_contract_token,
        get_instance_id,
        iid_curr,
        iid_old,
        FakeConfig,
    ):
        """When instance-id changes since last attach, call detach."""

        get_instance_id.return_value = iid_curr
        cloud_instance_factory.side_effect = self.fake_instance_factory

        def fake_contract_token(instance):
            return {"contractToken": "myPKCS7-token"}

        request_auto_attach_contract_token.side_effect = fake_contract_token

        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)
        # persist old instance-id value
        cfg.write_cache("instance-id", iid_old)

        with pytest.raises(AlreadyAttachedError):
            _get_contract_token_from_cloud_identity(cfg)
        assert str(iid_curr) == str(cfg.read_cache("instance-id"))


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAutoAttach:
    @mock.patch(M_ID_PATH + "cloud_instance_factory")
    def test_already_attached_on_non_ubuntu_pro(
        self, m_cloud_instance_factory, _m_getuid, FakeConfig
    ):
        """An attached machine raises AlreadyAttachedError on non-PRO."""
        # Non-PRO raises UserFacingError on non-PRO image
        m_cloud_instance_factory.side_effect = UserFacingError("Not-a-PRO")
        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)
        with pytest.raises(AlreadyAttachedError):
            action_auto_attach(mock.MagicMock(), cfg)

    @mock.patch("uaclient.cli.util.subp")
    def test_lock_file_exists(self, m_subp, _getuid, FakeConfig):
        """Check inability to auto-attach if operation holds lock file."""
        cfg = FakeConfig()
        cfg.write_cache("lock", "123:ua disable")
        with pytest.raises(LockHeldError) as err:
            action_auto_attach(mock.MagicMock(), cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: ua auto-attach.\n"
            "Operation in progress: ua disable (pid:123)"
        ) == err.value.msg

    @mock.patch(M_PATH + "contract.request_updated_contract")
    @mock.patch(M_PATH + "_get_contract_token_from_cloud_identity")
    def test_happy_path_on_aws_non_auto_attach(
        self,
        get_contract_token_from_cloud_identity,
        request_updated_contract,
        _m_getuid,
        FakeConfig,
    ):
        """Noop when _get_contract_token_from_cloud_identity finds no token"""
        exc = NonAutoAttachImageError("msg")
        get_contract_token_from_cloud_identity.side_effect = exc

        with pytest.raises(NonAutoAttachImageError):
            action_auto_attach(mock.MagicMock(), FakeConfig())
        assert 0 == request_updated_contract.call_count

    @pytest.mark.parametrize(
        "features_override", ((None), ({"disable_auto_attach": True}))
    )
    @mock.patch(M_PATH + "contract.request_updated_contract")
    @mock.patch(M_PATH + "_get_contract_token_from_cloud_identity")
    @mock.patch(M_PATH + "action_status")
    def test_happy_path_on_aws_auto_attach(
        self,
        action_status,
        get_contract_token_from_cloud_identity,
        request_updated_contract,
        _m_getuid,
        features_override,
        FakeConfig,
    ):
        """A mock-heavy test for the happy path on auto attach AWS"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        cfg = FakeConfig()
        if features_override:
            cfg.override_features(features_override)
            expected_calls = []
        else:
            expected_calls = [
                mock.call(cfg, "myPKCS7-token", allow_enable=True)
            ]
        get_contract_token_from_cloud_identity.return_value = "myPKCS7-token"

        def fake_request_updated_contract(cfg, contract_token, allow_enable):
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        request_updated_contract.side_effect = fake_request_updated_contract

        ret = action_auto_attach(mock.MagicMock(), cfg)
        assert 0 == ret
        assert expected_calls == request_updated_contract.call_args_list


class TestParser:
    def test_auto_attach_parser_updates_parser_config(self):
        """Update the parser configuration for 'auto-attach'."""
        m_parser = auto_attach_parser(mock.Mock())
        assert "ua auto-attach [flags]" == m_parser.usage
        assert "auto-attach" == m_parser.prog
        assert "Flags" == m_parser._optionals.title

        full_parser = get_parser(mock.Mock())
        with mock.patch("sys.argv", ["ua", "auto-attach"]):
            args = full_parser.parse_args()
        assert "auto-attach" == args.command
        assert "action_auto_attach" == args.action.__name__
