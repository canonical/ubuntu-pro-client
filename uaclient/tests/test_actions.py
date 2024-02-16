import json

import mock
import pytest

from uaclient import exceptions
from uaclient.actions import attach_with_token, auto_attach, collect_logs
from uaclient.testing import fakes, helpers

M_PATH = "uaclient.actions."
APPARMOR_DENIED = (
    'audit: type=1400 audit(1703513431.601:36): apparmor="DENIED" '
    'operation="open" profile="ubuntu_pro_apt_news" '
    'name="/proc/1422/status" pid=1422 comm="python3" '
    'requested_mask="r" denied_mask="r" fsuid=0 ouid=0'
)


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
            "expected_add_contract_machine_call_args",
            "expected_machine_token_file_write_call_args",
            "expected_get_machine_id_call_args",
            "expected_config_write_cache_call_args",
            "expected_process_entitlements_delta_call_args",
            "expected_attachment_data_file_write_call_args",
            "expected_status_call_args",
            "expected_update_motd_messages_call_args",
            "expected_update_activity_token_call_args",
            "expected_get_instance_id_call_args",
            "expected_timer_start_call_args",
            "expected_raises",
        ],
        [
            (
                "token",
                True,
                exceptions.ConnectivityError(cause=Exception(), url="url"),
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
                [],
                pytest.raises(exceptions.ConnectivityError),
            ),
            (
                "token",
                True,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                exceptions.ConnectivityError(cause=Exception(), url="url"),
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [mock.call("machine-id", "machine-id")],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [mock.call(cfg=mock.ANY)],
                [mock.call(mock.ANY)],
                [mock.call()],
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
                fakes.FakeUbuntuProError(),
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [mock.call("machine-id", "machine-id")],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [mock.call(cfg=mock.ANY)],
                [mock.call(mock.ANY)],
                [mock.call()],
                [],
                [],
                pytest.raises(exceptions.UbuntuProError),
            ),
            (
                "token",
                True,
                [{"machineTokenInfo": {"machineId": "machine-id"}}],
                "get-machine-id-result",
                mock.sentinel.entitlements,
                None,
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [mock.call("machine-id", "machine-id")],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY)],
                [],
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
                [mock.call(contract_token="token", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [
                    mock.call("machine-id", "machine-id"),
                ],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, True)],
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY)],
                [],
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
                [mock.call(contract_token="token2", attachment_dt=mock.ANY)],
                [mock.call({"machineTokenInfo": {"machineId": "machine-id"}})],
                [mock.call(mock.ANY)],
                [
                    mock.call("machine-id", "machine-id"),
                ],
                [mock.call(mock.ANY, {}, mock.sentinel.entitlements, False)],
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY)],
                [],
                [mock.call()],
                [mock.call()],
                helpers.does_not_raise(),
            ),
        ],
    )
    @mock.patch(
        "uaclient.entitlements.check_entitlement_apt_directives_are_unique",
        return_value=(True, None),
    )
    @mock.patch(M_PATH + "timer.start")
    @mock.patch(
        M_PATH + "contract.UAContractClient.update_activity_token",
    )
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
        m_update_activity_token,
        m_timer_start,
        _m_check_ent_apt_directives,
        token,
        allow_enable,
        add_contract_machine_side_effect,
        machine_id,
        entitlements,
        process_entitlements_delta_side_effect,
        expected_add_contract_machine_call_args,
        expected_machine_token_file_write_call_args,
        expected_get_machine_id_call_args,
        expected_config_write_cache_call_args,
        expected_process_entitlements_delta_call_args,
        expected_attachment_data_file_write_call_args,
        expected_status_call_args,
        expected_update_motd_messages_call_args,
        expected_update_activity_token_call_args,
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
            expected_update_activity_token_call_args
            == m_update_activity_token.call_args_list
        )
        assert expected_timer_start_call_args == m_timer_start.call_args_list

    @mock.patch(
        M_PATH + "contract.UAContractClient.add_contract_machine",
        return_value={},
    )
    @mock.patch(
        "uaclient.entitlements.check_entitlement_apt_directives_are_unique",
        side_effect=exceptions.EntitlementsAPTDirectivesAreNotUnique(
            url="test_url",
            names="ent1, ent2",
            apt_url="test",
            suite="release",
        ),
    )
    def test_attach_with_token_with_non_unique_entitlement_directives(
        self,
        _m_check_ent_apt_directives,
        _m_add_contract_machine,
    ):
        with pytest.raises(exceptions.EntitlementsAPTDirectivesAreNotUnique):
            attach_with_token(
                cfg=mock.MagicMock(),
                token="token",
                allow_enable=True,
            )


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
    def test_raise_unexpected_errors(
        self,
        m_get_contract_token_for_cloud_instances,
        FakeConfig,
    ):
        """Any unexpected errors will be raised."""
        cfg = FakeConfig()

        unexpected_error = exceptions.ContractAPIError(
            url="http://me",
            code=500,
            body=json.dumps({"message": "something unexpected"}),
        )
        m_get_contract_token_for_cloud_instances.side_effect = unexpected_error

        with pytest.raises(exceptions.ContractAPIError) as excinfo:
            auto_attach(cfg, fake_instance_factory())

        assert unexpected_error == excinfo.value


@mock.patch("uaclient.actions._write_command_output_to_file")
class TestCollectLogs:
    @mock.patch("uaclient.actions.status")
    @mock.patch("uaclient.actions.LOG.warning")
    @mock.patch("uaclient.util.get_pro_environment")
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    @mock.patch("uaclient.system.write_file")
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.actions._get_state_files")
    @mock.patch("glob.glob")
    @mock.patch("uaclient.log.get_user_log_file")
    @mock.patch("uaclient.system.subp", return_value=(APPARMOR_DENIED, ""))
    def test_collect_logs_invalid_file(
        self,
        m_system_subp,
        m_get_user,
        m_glob,
        m_get_state_files,
        m_load_file,
        m_write_file,
        m_we_are_currently_root,
        m_env_vars,
        m_log_warning,
        m_status,
        m_write_cmd,
        tmpdir,
    ):
        m_env_vars.return_value = {"test": "test"}
        m_status.return_value = ({"test": "test"}, 0)
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
        assert 5 == m_write_file.call_count

        # apparmor checks
        assert 1 == m_system_subp.call_count
        assert [
            mock.call(["journalctl", "-b", "-k", "--since=1 day ago"]),
        ] == m_system_subp.call_args_list

        print(m_write_file.call_args_list)
        assert [
            mock.call("test/pro-status.json", '{"test": "test"}'),
            mock.call("test/environment_vars.json", '{"test": "test"}'),
            mock.call("test/user0.log", "test"),
            mock.call("test/b", "test"),
            mock.call("test/apparmor_logs.txt", APPARMOR_DENIED),
        ] == m_write_file.call_args_list
        assert [
            mock.call("Failed to load file: %s\n%s", "a", "test")
        ] in m_log_warning.call_args_list
