import mock
import pytest

from uaclient import exceptions, status, util
from uaclient.actions import attach_with_token, auto_attach
from uaclient.contract import ContractAPIError
from uaclient.exceptions import NonAutoAttachImageError
from uaclient.tests.test_cli_auto_attach import fake_instance_factory

M_PATH = "uaclient.actions."


class TestAttachWithToken:
    @pytest.mark.parametrize(
        "request_updated_contract_side_effect, expected_error_class,"
        " expect_status_call",
        [
            (None, None, False),
            (util.UrlError("cause"), util.UrlError, True),
            (
                exceptions.UserFacingError("test"),
                exceptions.UserFacingError,
                True,
            ),
        ],
    )
    @mock.patch(M_PATH + "config.update_ua_messages")
    @mock.patch(M_PATH + "config.UAConfig.status")
    @mock.patch(M_PATH + "contract.request_updated_contract")
    def test_attach_with_token(
        self,
        m_request_updated_contract,
        m_status,
        m_update_ua_messages,
        request_updated_contract_side_effect,
        expected_error_class,
        expect_status_call,
        FakeConfig,
    ):
        cfg = FakeConfig()
        m_request_updated_contract.side_effect = (
            request_updated_contract_side_effect
        )
        if expected_error_class:
            with pytest.raises(expected_error_class):
                attach_with_token(cfg, "token", False)
        else:
            attach_with_token(cfg, "token", False)
        if expect_status_call:
            assert [mock.call()] == m_status.call_args_list
        assert [mock.call(cfg)] == m_update_ua_messages.call_args_list


class TestAutoAttach:
    @mock.patch(M_PATH + "attach_with_token")
    @mock.patch(M_PATH + "identity.get_instance_id", return_value="my-iid")
    @mock.patch(
        M_PATH
        + "contract.UAContractClient.request_auto_attach_contract_token",
        return_value={"contractToken": "token"},
    )
    @mock.patch(M_PATH + "config.update_ua_messages")
    @mock.patch(M_PATH + "config.UAConfig.write_cache")
    def test_happy_path_on_auto_attach(
        self,
        m_write_cache,
        m_update_ua_messages,
        m_request_auto_attach_contract_token,
        m_get_instance_id,
        m_attach_with_token,
        FakeConfig,
    ):
        cfg = FakeConfig()

        auto_attach(cfg, fake_instance_factory(cfg))

        assert [
            mock.call(cfg, token="token", allow_enable=True)
        ] == m_attach_with_token.call_args_list

        assert [
            mock.call("instance-id", "my-iid")
        ] == m_write_cache.call_args_list

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
    @mock.patch(M_PATH + "identity.get_instance_id", return_value="old-iid")
    def test_handles_4XX_contract_errors(
        self,
        _m_get_instance_id,
        m_request_auto_attach_contract_token,
        http_msg,
        http_code,
        http_response,
        FakeConfig,
    ):
        """VMs running on non-auto-attach images do not return a token."""
        cfg = FakeConfig()
        m_request_auto_attach_contract_token.side_effect = ContractAPIError(
            util.UrlError(
                http_msg, code=http_code, url="http://me", headers={}
            ),
            error_response=http_response,
        )
        with pytest.raises(NonAutoAttachImageError) as excinfo:
            auto_attach(cfg, fake_instance_factory(cfg))
        assert status.MESSAGE_UNSUPPORTED_AUTO_ATTACH == str(excinfo.value)

    @mock.patch(
        M_PATH + "contract.UAContractClient.request_auto_attach_contract_token"
    )
    @mock.patch(M_PATH + "identity.get_instance_id", return_value="my-iid")
    def test_raise_unexpected_errors(
        self,
        _m_get_instance_id,
        m_request_auto_attach_contract_token,
        FakeConfig,
    ):
        """Any unexpected errors will be raised."""
        cfg = FakeConfig()

        unexpected_error = ContractAPIError(
            util.UrlError(
                "Server error", code=500, url="http://me", headers={}
            ),
            error_response={"message": "something unexpected"},
        )
        m_request_auto_attach_contract_token.side_effect = unexpected_error

        with pytest.raises(ContractAPIError) as excinfo:
            auto_attach(cfg, fake_instance_factory(cfg))

        assert unexpected_error == excinfo.value
