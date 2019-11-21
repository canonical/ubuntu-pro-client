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
    NonRootUserError,
    NonUbuntuProImageError,
)
from uaclient import status
from uaclient.testing.fakes import FakeConfig
from uaclient.tests.test_cli_attach import BASIC_MACHINE_TOKEN
from uaclient import util

M_PATH = "uaclient.cli."


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid):
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

    @pytest.mark.parametrize("cloud_type", ("awslookalike", "azure", "!aws"))
    @mock.patch("uaclient.clouds.identity.get_cloud_type")
    def test_non_aws_cloud_type_raises_error(
        self, m_get_cloud_type, cloud_type
    ):
        """Non-aws clouds will error."""
        m_get_cloud_type.return_value = cloud_type
        with pytest.raises(NonUbuntuProImageError) as excinfo:
            _get_contract_token_from_cloud_identity(FakeConfig())
        assert status.MESSAGE_UNSUPPORTED_UBUNTU_PRO_CLOUD_TYPE.format(
            cloud_type=cloud_type
        ) == str(excinfo.value)

    @mock.patch(
        M_PATH + "contract.UAContractClient.request_pro_aws_contract_token"
    )
    @mock.patch("uaclient.clouds.identity.cloud_instance_factory")
    @mock.patch("uaclient.clouds.identity.get_cloud_type", return_value="aws")
    def test_aws_cloud_type_non_ubuntu_pro_returns_no_token(
        self,
        _get_cloud_type,
        cloud_instance_factory,
        request_pro_aws_contract_token,
    ):
        """AWS clouds on non-Ubuntu Pro images not return a token."""

        cloud_instance_factory.side_effect = self.fake_instance_factory
        request_pro_aws_contract_token.side_effect = ContractAPIError(
            util.UrlError(
                "Server error", code=500, url="http://me", headers={}
            ),
            error_response={"message": "missing instance information"},
        )
        with pytest.raises(NonUbuntuProImageError) as excinfo:
            _get_contract_token_from_cloud_identity(FakeConfig())
        assert status.MESSAGE_UNSUPPORTED_UBUNTU_PRO == str(excinfo.value)

    @mock.patch(
        M_PATH + "contract.UAContractClient.request_pro_aws_contract_token"
    )
    @mock.patch("uaclient.clouds.identity.cloud_instance_factory")
    @mock.patch("uaclient.clouds.identity.get_cloud_type", return_value="aws")
    def test_raise_unexpected_errors(
        self,
        _get_cloud_type,
        cloud_instance_factory,
        request_pro_aws_contract_token,
    ):
        """Any unexpected errors will be raised."""

        cloud_instance_factory.side_effect = self.fake_instance_factory
        unexpected_error = ContractAPIError(
            util.UrlError(
                "Server error", code=500, url="http://me", headers={}
            ),
            error_response={"message": "something unexpected"},
        )
        request_pro_aws_contract_token.side_effect = unexpected_error

        with pytest.raises(ContractAPIError) as excinfo:
            _get_contract_token_from_cloud_identity(FakeConfig())
        assert unexpected_error == excinfo.value

    @mock.patch(
        M_PATH + "contract.UAContractClient.request_pro_aws_contract_token"
    )
    @mock.patch("uaclient.clouds.identity.cloud_instance_factory")
    @mock.patch("uaclient.clouds.identity.get_cloud_type", return_value="aws")
    def test_return_token_from_contract_server_using_identity_doc(
        self,
        _get_cloud_type,
        cloud_instance_factory,
        request_aws_contract_token,
    ):
        """Return token from the contract server using the identity."""

        cloud_instance_factory.side_effect = self.fake_instance_factory

        def fake_aws_contract_token(contract_token):
            return {"contractToken": "myPKCS7-token"}

        request_aws_contract_token.side_effect = fake_aws_contract_token

        cfg = FakeConfig()
        assert "myPKCS7-token" == _get_contract_token_from_cloud_identity(cfg)


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAutoAttach:
    def test_already_attached(self, _m_getuid):
        """Check that an attached machine raises AlreadyAttachedError."""
        account_name = "test_account"
        cfg = FakeConfig.for_attached_machine(account_name=account_name)

        with pytest.raises(AlreadyAttachedError):
            action_auto_attach(mock.MagicMock(), cfg)

    @mock.patch(M_PATH + "contract.request_updated_contract")
    @mock.patch(M_PATH + "_get_contract_token_from_cloud_identity")
    def test_happy_path_on_aws_non_ubuntu_pro(
        self,
        get_contract_token_from_cloud_identity,
        request_updated_contract,
        _m_getuid,
    ):
        """Noop when _get_contract_token_from_cloud_identity finds no token"""
        exc = NonUbuntuProImageError("msg")
        get_contract_token_from_cloud_identity.side_effect = exc

        with pytest.raises(NonUbuntuProImageError):
            action_auto_attach(mock.MagicMock(), FakeConfig())
        assert 0 == request_updated_contract.call_count

    @mock.patch(M_PATH + "contract.request_updated_contract")
    @mock.patch(M_PATH + "_get_contract_token_from_cloud_identity")
    @mock.patch(M_PATH + "action_status")
    def test_happy_path_on_aws_ubuntu_pro(
        self,
        action_status,
        get_contract_token_from_cloud_identity,
        request_updated_contract,
        _m_getuid,
    ):
        """A mock-heavy test for the happy path on Ubuntu Pro AWS"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        cfg = FakeConfig()
        get_contract_token_from_cloud_identity.return_value = "myPKCS7-token"

        def fake_request_updated_contract(cfg, contract_token, allow_enable):
            cfg.write_cache("machine-token", BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        request_updated_contract.side_effect = fake_request_updated_contract

        ret = action_auto_attach(mock.MagicMock(), cfg)
        assert 0 == ret
        expected_calls = [mock.call(cfg, "myPKCS7-token", allow_enable=True)]
        assert expected_calls == request_updated_contract.call_args_list


class TestParser:
    def test_auto_attach_parser_updates_parser_config(self):
        """Update the parser configuration for 'auto-attach'."""
        m_parser = auto_attach_parser(mock.Mock())
        assert "ua auto-attach [flags]" == m_parser.usage
        assert "auto-attach" == m_parser.prog
        assert "Flags" == m_parser._optionals.title

        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "auto-attach"]):
            args = full_parser.parse_args()
        assert "auto-attach" == args.command
        assert "action_auto_attach" == args.action.__name__
