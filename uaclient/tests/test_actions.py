import logging

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.actions import (
    attach_with_token,
    auto_attach,
    collect_logs,
    get_cloud_instance,
)
from uaclient.exceptions import (
    CloudFactoryError,
    CloudFactoryNoCloudError,
    CloudFactoryNonViableCloudError,
    CloudFactoryUnsupportedCloudError,
    ContractAPIError,
    NonAutoAttachImageError,
    UserFacingError,
)

M_PATH = "uaclient.actions."


def fake_instance_factory():
    m_instance = mock.Mock()
    m_instance.identity_doc = "pkcs7-validated-by-backend"
    return m_instance


class TestAttachWithToken:
    @pytest.mark.parametrize(
        "request_updated_contract_side_effect, expected_error_class,"
        " expect_status_call",
        [
            (None, None, False),
            (exceptions.UrlError("cause"), exceptions.UrlError, True),
            (
                exceptions.UserFacingError("test"),
                exceptions.UserFacingError,
                True,
            ),
        ],
    )
    @mock.patch(M_PATH + "identity.get_instance_id", return_value="my-iid")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    @mock.patch("uaclient.status.status")
    @mock.patch(M_PATH + "contract.request_updated_contract")
    @mock.patch(M_PATH + "config.UAConfig.write_cache")
    def test_attach_with_token(
        self,
        m_write_cache,
        m_request_updated_contract,
        m_status,
        m_update_apt_and_motd_msgs,
        _m_get_instance_id,
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
            assert [mock.call(cfg=cfg)] == m_status.call_args_list
        if not expect_status_call:
            assert [
                mock.call("instance-id", "my-iid")
            ] == m_write_cache.call_args_list

        assert [mock.call(cfg)] == m_update_apt_and_motd_msgs.call_args_list


class TestAutoAttach:
    @mock.patch(M_PATH + "attach_with_token")
    @mock.patch(
        M_PATH
        + "contract.UAContractClient.request_auto_attach_contract_token",
        return_value={"contractToken": "token"},
    )
    def test_happy_path_on_auto_attach(
        self,
        m_request_auto_attach_contract_token,
        m_attach_with_token,
        FakeConfig,
    ):
        cfg = FakeConfig()

        auto_attach(cfg, fake_instance_factory())

        assert [
            mock.call(cfg, token="token", allow_enable=True)
        ] == m_attach_with_token.call_args_list

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
            exceptions.UrlError(
                "Server error", code=500, url="http://me", headers={}
            ),
            error_response={"message": "something unexpected"},
        )
        m_request_auto_attach_contract_token.side_effect = unexpected_error

        with pytest.raises(ContractAPIError) as excinfo:
            auto_attach(cfg, fake_instance_factory())

        assert unexpected_error == excinfo.value


@mock.patch("uaclient.actions._write_command_output_to_file")
class TestCollectLogs:
    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    @mock.patch("uaclient.system.write_file")
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.actions._get_state_files")
    @mock.patch("glob.glob")
    def test_collect_logs_invalid_file(
        self,
        m_glob,
        m_get_state_files,
        m_load_file,
        m_write_file,
        m_we_are_currently_root,
        m_write_cmd,
        caplog_text,
    ):
        m_get_state_files.return_value = ["a", "b"]
        m_load_file.side_effect = [UnicodeError("test"), "test"]
        m_glob.return_value = []

        with mock.patch("os.path.isfile", return_value=True):
            collect_logs(cfg=mock.MagicMock(), output_dir="test")

        assert 2 == m_load_file.call_count
        assert [mock.call("a"), mock.call("b")] == m_load_file.call_args_list
        assert 1 == m_write_file.call_count
        assert [mock.call("test/b", "test")] == m_write_file.call_args_list
        assert "Failed to load file: a\n" in caplog_text()


class TestGetCloudInstance:
    @pytest.mark.parametrize(
        "cloud_factory_error, expected_error_cls, expected_error_msg",
        [
            (
                CloudFactoryNoCloudError("test"),
                UserFacingError,
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
            ),
            (
                CloudFactoryNonViableCloudError("test"),
                UserFacingError,
                messages.UNSUPPORTED_AUTO_ATTACH,
            ),
            (
                CloudFactoryUnsupportedCloudError("test"),
                NonAutoAttachImageError,
                messages.UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
                    cloud_type="test"
                ),
            ),
            (
                CloudFactoryNoCloudError("test"),
                UserFacingError,
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
            ),
            (
                CloudFactoryError("test"),
                UserFacingError,
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
            ),
        ],
    )
    @mock.patch(M_PATH + "identity.cloud_instance_factory")
    def test_handle_cloud_factory_errors(
        self,
        m_cloud_instance_factory,
        cloud_factory_error,
        expected_error_cls,
        expected_error_msg,
        FakeConfig,
    ):
        """Non-supported clouds will error."""
        m_cloud_instance_factory.side_effect = cloud_factory_error
        cfg = FakeConfig()

        with pytest.raises(expected_error_cls) as excinfo:
            get_cloud_instance(cfg=cfg)

        if expected_error_msg:
            assert expected_error_msg == str(excinfo.value)
