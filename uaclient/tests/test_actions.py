import json

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
from uaclient.testing import helpers

M_PATH = "uaclient.actions."


def fake_instance_factory():
    m_instance = mock.Mock()
    m_instance.identity_doc = "pkcs7-validated-by-backend"
    return m_instance


class TestAttachWithToken:
    @pytest.mark.parametrize(
        [
            "token",
            "allow_enable",
            "add_contract_machine_side_effect",
            "machine_id",
            "entitlements",
            "process_entitlements_delta_side_effect",
            "instance_id",
            "expected_add_contract_machine_call_args",
            "expected_machine_token_file_write_call_args",
            "expected_get_machine_id_call_args",
            "expected_config_write_cache_call_args",
            "expected_process_entitlements_delta_call_args",
            "expected_attachment_data_file_write_call_args",
            "expected_status_call_args",
            "expected_update_motd_messages_call_args",
            "expected_get_instance_id_call_args",
            "expected_timer_start_call_args",
            "expected_raises",
        ],
        [
            (
                "token",
                True,
                exceptions.UrlError(Exception(), "url"),
                None,
                None,
                None,
                None,
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                pytest.raises(exceptions.ConnectivityError),
            ),
            (
                "token",
                True,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                exceptions.UrlError(Exception(), "url"),
                None,
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [mock.call("machine-id", "machine-id")],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [mock.call(cfg=mock.ANY)],
                [mock.call(mock.ANY)],
                [],
                [],
                pytest.raises(exceptions.UrlError),
            ),
            (
                "token",
                True,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                exceptions.UserFacingError("message"),
                None,
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [mock.call("machine-id", "machine-id")],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [mock.call(cfg=mock.ANY)],
                [mock.call(mock.ANY)],
                [],
                [],
                pytest.raises(exceptions.UserFacingError),
            ),
            (
                "token",
                True,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                None,
                None,
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [mock.call("machine-id", "machine-id")],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY)],
                [mock.call()],
                [mock.call()],
                helpers.does_not_raise(),
            ),
            (
                "token",
                True,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                None,
                "id",
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [
                    mock.call("machine-id", "machine-id"),
                    mock.call("instance-id", "id"),
                ],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY)],
                [mock.call()],
                [mock.call()],
                helpers.does_not_raise(),
            ),
            (
                "token2",
                False,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                None,
                "id",
                [mock.call(contract_token="token2", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [
                    mock.call("machine-id", "machine-id"),
                    mock.call("instance-id", "id"),
                ],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, False)],
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY)],
                [mock.call()],
                [mock.call()],
                helpers.does_not_raise(),
            ),
        ],
    )
    @mock.patch(M_PATH + "timer.start")
    @mock.patch(M_PATH + "identity.get_instance_id", return_value="my-iid")
    @mock.patch("uaclient.timer.update_messaging.update_motd_messages")
    @mock.patch(M_PATH + "ua_status.status")
    @mock.patch("uaclient.files.state_files.attachment_data_file.write")
    @mock.patch(M_PATH + "contract.process_entitlements_delta")
    @mock.patch(
        "uaclient.files.MachineTokenFile.entitlements",
        new_callable=mock.PropertyMock,
    )
    @mock.patch(M_PATH + "config.UAConfig.write_cache")
    @mock.patch(M_PATH + "system.get_machine_id")
    @mock.patch("uaclient.files.MachineTokenFile.write")
    @mock.patch(M_PATH + "contract.UAContractClient.add_contract_machine")
    def test_attach_with_token(
        self,
        m_add_contract_machine,
        m_machine_token_file_write,
        m_get_machine_id,
        m_config_write_cache,
        m_entitlements,
        m_process_entitlements_delta,
        m_attachment_data_file_write,
        m_status,
        m_update_motd_messages,
        m_get_instance_id,
        m_timer_start,
        token,
        allow_enable,
        add_contract_machine_side_effect,
        machine_id,
        entitlements,
        process_entitlements_delta_side_effect,
        instance_id,
        expected_add_contract_machine_call_args,
        expected_machine_token_file_write_call_args,
        expected_get_machine_id_call_args,
        expected_config_write_cache_call_args,
        expected_process_entitlements_delta_call_args,
        expected_attachment_data_file_write_call_args,
        expected_status_call_args,
        expected_update_motd_messages_call_args,
        expected_get_instance_id_call_args,
        expected_timer_start_call_args,
        expected_raises,
        FakeConfig,
    ):
        cfg = FakeConfig()
        m_add_contract_machine.side_effect = add_contract_machine_side_effect
        m_get_machine_id.return_value = machine_id
        m_entitlements.return_value = entitlements
        m_process_entitlements_delta.side_effect = (
            process_entitlements_delta_side_effect
        )
        m_get_instance_id.return_value = instance_id

        with expected_raises:
            attach_with_token(cfg, token, allow_enable)

        assert (
            expected_add_contract_machine_call_args
            == m_add_contract_machine.call_args_list
        )
        assert (
            expected_machine_token_file_write_call_args
            == m_machine_token_file_write.call_args_list
        )
        assert (
            expected_get_machine_id_call_args
            == m_get_machine_id.call_args_list
        )
        assert (
            expected_config_write_cache_call_args
            == m_config_write_cache.call_args_list
        )
        assert (
            expected_process_entitlements_delta_call_args
            == m_process_entitlements_delta.call_args_list
        )
        assert (
            expected_attachment_data_file_write_call_args
            == m_attachment_data_file_write.call_args_list
        )
        assert expected_status_call_args == m_status.call_args_list
        assert (
            expected_update_motd_messages_call_args
            == m_update_motd_messages.call_args_list
        )
        assert (
            expected_get_instance_id_call_args
            == m_get_instance_id.call_args_list
        )
        assert expected_timer_start_call_args == m_timer_start.call_args_list


class TestAutoAttach:
    @mock.patch(M_PATH + "attach_with_token")
    @mock.patch(
        M_PATH
        + "contract.UAContractClient.get_contract_token_for_cloud_instance",
        return_value={"contractToken": "token"},
    )
    def test_happy_path_on_auto_attach(
        self,
        _m_get_contract_token_for_cloud_instances,
        m_attach_with_token,
        FakeConfig,
    ):
        cfg = FakeConfig()

        auto_attach(cfg, fake_instance_factory())

        assert [
            mock.call(cfg, token="token", allow_enable=True)
        ] == m_attach_with_token.call_args_list

    @mock.patch(
        M_PATH
        + "contract.UAContractClient.get_contract_token_for_cloud_instance"  # noqa
    )
    @mock.patch(M_PATH + "identity.get_instance_id", return_value="my-iid")
    def test_raise_unexpected_errors(
        self,
        _m_get_instance_id,
        m_get_contract_token_for_cloud_instances,
        FakeConfig,
    ):
        """Any unexpected errors will be raised."""
        cfg = FakeConfig()

        unexpected_error = ContractAPIError(
            "http://me", 500, json.dumps({"message": "something unexpected"})
        )
        m_get_contract_token_for_cloud_instances.side_effect = unexpected_error

        with pytest.raises(ContractAPIError) as excinfo:
            auto_attach(cfg, fake_instance_factory())

        assert unexpected_error == excinfo.value


@mock.patch("uaclient.actions._write_command_output_to_file")
class TestCollectLogs:
    @mock.patch("uaclient.actions.logging.warning")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    @mock.patch("uaclient.system.write_file")
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.actions._get_state_files")
    @mock.patch("glob.glob")
    @mock.patch("uaclient.log.get_user_log_file")
    def test_collect_logs_invalid_file(
        self,
        m_get_user,
        m_glob,
        m_get_state_files,
        m_load_file,
        m_write_file,
        m_we_are_currently_root,
        m_log_warning,
        m_write_cmd,
        tmpdir,
    ):
        log_file = tmpdir.join("user-log").strpath
        m_get_user.return_value = log_file
        m_get_state_files.return_value = ["a", "b"]
        m_load_file.side_effect = ["test", UnicodeError("test"), "test"]
        m_glob.return_value = []

        with mock.patch("os.path.isfile", return_value=True):
            collect_logs(cfg=mock.MagicMock(), output_dir="test")

        assert 3 == m_load_file.call_count
        assert [
            mock.call(log_file),
            mock.call("a"),
            mock.call("b"),
        ] == m_load_file.call_args_list
        assert 2 == m_write_file.call_count
        print(m_write_file.call_args_list)
        assert [
            mock.call("test/user0.log", "test"),
            mock.call("test/b", "test"),
        ] == m_write_file.call_args_list
        assert [
            mock.call("Failed to load file: %s\n%s", "a", "test")
        ] in m_log_warning.call_args_list


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
