import contextlib
import io
import json
from textwrap import dedent

import mock
import pytest

from uaclient import event_logger, exceptions, lock, messages
from uaclient.cli import main_error_handler
from uaclient.cli.detach import detach_command
from uaclient.testing.fakes import FakeContractClient

M_PATH = "uaclient.cli.detach."


def entitlement_cls_mock_factory(can_disable, name=None):
    m_instance = mock.MagicMock()
    m_instance.enabled_variant = None
    m_instance.can_disable.return_value = (can_disable, None)
    m_instance.disable.return_value = (can_disable, None)
    type(m_instance).dependent_services = mock.PropertyMock(return_value=())
    if name:
        type(m_instance).name = mock.PropertyMock(return_value=name)

    return m_instance


@mock.patch(M_PATH + "util.prompt_for_confirmation", return_value=True)
class TestActionDetach:
    @mock.patch(M_PATH + "util.we_are_currently_root", return_value=False)
    def test_non_root_users_are_rejected(
        self,
        m_we_are_currently_root,
        _m_prompt,
        FakeConfig,
        fake_machine_token_file,
        event,
        capsys,
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        m_we_are_currently_root.return_value = False
        args = mock.MagicMock()

        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        with pytest.raises(exceptions.NonRootUserError):
            detach_command.action(args, cfg=cfg)

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(detach_command.action)(args, cfg)

        expected_message = messages.E_NONROOT_USER
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

    def test_unattached_error_message(
        self, _m_prompt, FakeConfig, capsys, event
    ):
        """Check that root user gets unattached message."""

        cfg = FakeConfig()
        args = mock.MagicMock()
        with pytest.raises(exceptions.UnattachedError) as err:
            detach_command.action(args, cfg=cfg)
        assert messages.E_UNATTACHED.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(detach_command.action)(args, cfg)

        expected_message = messages.E_UNATTACHED
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

    @mock.patch("uaclient.lock.check_lock_info")
    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self,
        m_subp,
        m_sleep,
        m_check_lock_info,
        m_prompt,
        FakeConfig,
        fake_machine_token_file,
        capsys,
        event,
    ):
        """Check when an operation holds a lock file, detach cannot run."""
        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        args = mock.MagicMock()
        m_check_lock_info.return_value = (123, "pro enable")

        with pytest.raises(exceptions.LockHeldError) as err:
            detach_command.action(args, cfg=cfg)

        assert 12 == m_check_lock_info.call_count
        expected_error_msg = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro detach", lock_holder="pro enable", pid="123"
        )
        assert expected_error_msg.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(detach_command.action)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "additional_info": {
                        "lock_holder": "pro enable",
                        "lock_request": "pro detach",
                        "pid": 123,
                    },
                    "message": expected_error_msg.msg,
                    "message_code": expected_error_msg.name,
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
        "prompt_response,assume_yes,expect_disable",
        [(True, False, True), (False, False, False), (True, True, True)],
    )
    @mock.patch("uaclient.files.state_files.delete_state_files")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch(M_PATH + "update_motd_messages")
    @mock.patch(M_PATH + "entitlements.entitlements_disable_order")
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    def test_entitlements_disabled_appropriately(
        self,
        m_ent_factory,
        m_disable_order,
        m_update_apt_and_motd_msgs,
        m_client,
        _m_check_lock_info,
        _m_delete_state_files,
        m_prompt,
        prompt_response,
        assume_yes,
        expect_disable,
        FakeConfig,
        fake_machine_token_file,
        event,
        capsys,
    ):
        # The three parameters:
        #   prompt_response: the user's response to the prompt
        #   assume_yes: the value of the --assume-yes flag in the args passed
        #               to the action
        #   expect_disable: whether or not the enabled entitlement is expected
        #                   to be disabled by the action

        cfg = FakeConfig()
        fake_machine_token_file.attached = True
        fake_client = FakeContractClient(cfg)
        m_client.return_value = fake_client

        m_prompt.return_value = prompt_response

        m_disable_order.return_value = ["test"]
        m_ent = entitlement_cls_mock_factory(True, name="test")
        m_ent_factory.return_value = m_ent

        args = mock.MagicMock(assume_yes=assume_yes)
        with mock.patch.object(lock, "lock_data_file"):
            return_code = detach_command.action(args, cfg=cfg)

        assert [
            mock.call(ignore_dependent_services=True)
        ] == m_ent.can_disable.call_args_list

        if expect_disable:
            assert [mock.call(mock.ANY)] == m_ent.disable.call_args_list
            assert 0 == return_code
        else:
            assert 0 == m_ent.disable.call_count
            assert 1 == return_code
        assert [mock.call(assume_yes=assume_yes)] == m_prompt.call_args_list
        if expect_disable:
            assert [
                mock.call(cfg)
            ] == m_update_apt_and_motd_msgs.call_args_list

        fake_stdout = io.StringIO()
        # On json response, we will never prompt the user
        m_prompt.return_value = True
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
                    main_error_handler(detach_command.action)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "success",
            "errors": [],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": ["test"],
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())

    @mock.patch("uaclient.files.state_files.delete_state_files")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(M_PATH + "cli_util._is_attached")
    @mock.patch(M_PATH + "entitlements.entitlements_disable_order")
    @mock.patch(M_PATH + "update_motd_messages")
    def test_correct_message_emitted(
        self,
        m_update_apt_and_motd_msgs,
        m_disable_order,
        m_is_attached,
        _m_check_lock_info,
        m_delete_state_files,
        _m_prompt,
        capsys,
        tmpdir,
    ):
        m_disable_order.return_value = []
        m_is_attached.return_value = mock.MagicMock(
            is_attached=True,
            contract_status="active",
            contract_remaining_days=100,
        )

        m_cfg = mock.MagicMock()
        with mock.patch.object(lock, "lock_data_file"):
            detach_command.action(mock.MagicMock(), m_cfg)

        out, _err = capsys.readouterr()
        assert messages.DETACH_SUCCESS + "\n" == out
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list
        assert [mock.call()] == m_delete_state_files.call_args_list

    @mock.patch("uaclient.files.state_files.delete_state_files")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(M_PATH + "cli_util._is_attached")
    @mock.patch(M_PATH + "entitlements.entitlements_disable_order")
    @mock.patch(M_PATH + "update_motd_messages")
    def test_returns_zero(
        self,
        m_update_apt_and_motd_msgs,
        m_disable_order,
        m_is_attached,
        _m_check_lock_info,
        m_delete_state_files,
        _m_prompt,
        tmpdir,
    ):
        m_disable_order.return_value = []
        m_is_attached.return_value = mock.MagicMock(
            is_attached=True,
            contract_status="active",
            contract_remaining_days=100,
        )

        m_cfg = mock.MagicMock()
        with mock.patch.object(lock, "lock_data_file"):
            ret = detach_command.action(mock.MagicMock(), m_cfg)

        assert 0 == ret
        assert [mock.call()] == m_delete_state_files.call_args_list
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

    @pytest.mark.parametrize(
        "classes,disable_order,expected_message,disabled_services",
        [
            (
                [
                    entitlement_cls_mock_factory(True, name="ent1"),
                    entitlement_cls_mock_factory(False, name="ent2"),
                    entitlement_cls_mock_factory(True, name="ent3"),
                ],
                ["ent1", "ent2", "ent3"],
                dedent(
                    """\
                    Detach will disable the following services:
                        ent1
                        ent3"""
                ),
                ["ent1", "ent3"],
            ),
            (
                [
                    entitlement_cls_mock_factory(True, name="ent1"),
                    entitlement_cls_mock_factory(False, name="ent2"),
                ],
                ["ent1", "ent2"],
                dedent(
                    """\
                    Detach will disable the following service:
                        ent1"""
                ),
                ["ent1"],
            ),
        ],
    )
    @mock.patch("uaclient.files.state_files.delete_state_files")
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch(M_PATH + "cli_util._is_attached")
    @mock.patch(M_PATH + "update_motd_messages")
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch(M_PATH + "entitlements.entitlements_disable_order")
    def test_informational_message_emitted(
        self,
        m_disable_order,
        m_ent_factory,
        m_update_apt_and_motd_msgs,
        m_is_attached,
        _m_check_lock_info,
        _m_delete_state_files,
        _m_prompt,
        capsys,
        classes,
        disable_order,
        expected_message,
        disabled_services,
        tmpdir,
        FakeConfig,
        fake_machine_token_file,
        event,
    ):
        m_ent_factory.side_effect = classes
        m_disable_order.return_value = disable_order
        m_is_attached.return_value = mock.MagicMock(
            is_attached=True,
            contract_status="active",
            contract_remaining_days=100,
        )

        m_cfg = mock.MagicMock()
        args = mock.MagicMock()

        with mock.patch.object(lock, "lock_data_file"):
            detach_command.action(args, m_cfg)

        out, _err = capsys.readouterr()

        assert expected_message in out
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

        fake_stdout = io.StringIO()
        m_ent_factory.side_effect = classes
        fake_machine_token_file.attached = True
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
                    main_error_handler(detach_command.action)(
                        args, FakeConfig()
                    )

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "success",
            "errors": [],
            "failed_services": [],
            "needs_reboot": False,
            "processed_services": disabled_services,
            "warnings": [],
        }
        assert expected == json.loads(fake_stdout.getvalue())
