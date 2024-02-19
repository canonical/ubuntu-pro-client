import contextlib
import io
import json
from textwrap import dedent

import mock
import pytest

from uaclient import event_logger, exceptions, lock, messages
from uaclient.cli import (
    action_detach,
    detach_parser,
    get_parser,
    main_error_handler,
)
from uaclient.testing.fakes import FakeContractClient


def entitlement_cls_mock_factory(can_disable, name=None):
    m_instance = mock.MagicMock()
    m_instance.enabled_variant = None
    m_instance.can_disable.return_value = (can_disable, None)
    m_instance.disable.return_value = (can_disable, None)
    type(m_instance).dependent_services = mock.PropertyMock(return_value=())
    if name:
        type(m_instance).name = mock.PropertyMock(return_value=name)

    return mock.Mock(return_value=m_instance)


@mock.patch("uaclient.cli.util.prompt_for_confirmation", return_value=True)
class TestActionDetach:
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    def test_non_root_users_are_rejected(
        self, m_we_are_currently_root, _m_prompt, FakeConfig, event, capsys
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        m_we_are_currently_root.return_value = False
        args = mock.MagicMock()

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_detach(args, cfg=cfg)

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_detach)(args, cfg)

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
            action_detach(args, cfg=cfg)
        assert messages.E_UNATTACHED.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_detach)(args, cfg)

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
        capsys,
        event,
    ):
        """Check when an operation holds a lock file, detach cannot run."""
        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        m_check_lock_info.return_value = (123, "pro enable")

        with pytest.raises(exceptions.LockHeldError) as err:
            action_detach(args, cfg=cfg)

        assert 12 == m_check_lock_info.call_count
        expected_error_msg = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro detach", lock_holder="pro enable", pid="123"
        )
        assert expected_error_msg.msg == err.value.msg

        with pytest.raises(SystemExit):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                main_error_handler(action_detach)(args, cfg)

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
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.cli.update_motd_messages")
    @mock.patch("uaclient.cli.entitlements_disable_order")
    @mock.patch("uaclient.cli.entitlements.entitlement_factory")
    def test_entitlements_disabled_appropriately(
        self,
        m_ent_factory,
        m_disable_order,
        m_update_apt_and_motd_msgs,
        m_client,
        _m_check_lock_info,
        m_prompt,
        prompt_response,
        assume_yes,
        expect_disable,
        FakeConfig,
        event,
        capsys,
    ):
        # The three parameters:
        #   prompt_response: the user's response to the prompt
        #   assume_yes: the value of the --assume-yes flag in the args passed
        #               to the action
        #   expect_disable: whether or not the enabled entitlement is expected
        #                   to be disabled by the action

        cfg = FakeConfig.for_attached_machine()
        fake_client = FakeContractClient(cfg)
        m_client.return_value = fake_client

        m_prompt.return_value = prompt_response
        disabled_cls = entitlement_cls_mock_factory(True, name="test")

        m_disable_order.return_value = ["test"]
        m_ent_factory.return_value = disabled_cls

        args = mock.MagicMock(assume_yes=assume_yes)
        with mock.patch.object(lock, "lock_data_file"):
            return_code = action_detach(args, cfg=cfg)

        assert [
            mock.call(ignore_dependent_services=True)
        ] == disabled_cls.return_value.can_disable.call_args_list

        if expect_disable:
            assert [
                mock.call()
            ] == disabled_cls.return_value.disable.call_args_list
            assert 0 == return_code
        else:
            assert 0 == disabled_cls.return_value.disable.call_count
            assert 1 == return_code
        assert [mock.call(assume_yes=assume_yes)] == m_prompt.call_args_list
        if expect_disable:
            assert [
                mock.call(cfg)
            ] == m_update_apt_and_motd_msgs.call_args_list

        cfg = FakeConfig.for_attached_machine()
        fake_stdout = io.StringIO()
        # On json response, we will never prompt the user
        m_prompt.return_value = True
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
                    main_error_handler(action_detach)(args, cfg)

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

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.cli.entitlements_disable_order")
    @mock.patch("uaclient.cli.update_motd_messages")
    def test_config_cache_deleted(
        self,
        m_update_apt_and_motd_msgs,
        m_disable_order,
        _m_check_lock_info,
        _m_prompt,
        capsys,
    ):
        m_disable_order.return_value = []

        m_cfg = mock.MagicMock()
        with mock.patch.object(lock, "lock_data_file"):
            ret = action_detach(mock.MagicMock(), m_cfg)

        out, _err = capsys.readouterr()
        assert messages.DETACH_SUCCESS + "\n" == out

        assert 0 == ret
        assert [mock.call()] == m_cfg.delete_cache.call_args_list
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
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.cli.update_motd_messages")
    @mock.patch("uaclient.entitlements.entitlement_factory")
    @mock.patch("uaclient.cli.entitlements_disable_order")
    def test_informational_message_emitted(
        self,
        m_disable_order,
        m_ent_factory,
        m_update_apt_and_motd_msgs,
        _m_check_lock_info,
        _m_prompt,
        capsys,
        classes,
        disable_order,
        expected_message,
        disabled_services,
        FakeConfig,
        tmpdir,
        event,
    ):
        m_ent_factory.side_effect = classes
        m_disable_order.return_value = disable_order

        m_cfg = mock.MagicMock()
        args = mock.MagicMock()

        with mock.patch.object(lock, "lock_data_file"):
            action_detach(args, m_cfg)

        out, _err = capsys.readouterr()

        assert expected_message in out
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

        cfg = FakeConfig.for_attached_machine()
        fake_stdout = io.StringIO()
        m_ent_factory.side_effect = classes
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger.EventLoggerMode.JSON
            ):
                with mock.patch.object(lock, "lock_data_file"):
                    main_error_handler(action_detach)(args, cfg)

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


class TestParser:
    def test_detach_parser_usage(self):
        parser = detach_parser(mock.Mock())
        assert "pro detach [flags]" == parser.usage

    def test_detach_parser_prog(self):
        parser = detach_parser(mock.Mock())
        assert "detach" == parser.prog

    def test_detach_parser_optionals_title(self):
        parser = detach_parser(mock.Mock())
        assert "Flags" == parser._optionals.title

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_detach_parser_accepts_and_stores_assume_yes(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "detach", "--assume-yes"]):
            args = full_parser.parse_args()

        assert args.assume_yes

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_detach_parser_defaults_to_not_assume_yes(
        self, _m_resources, FakeConfig
    ):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "detach"]):
            args = full_parser.parse_args()

        assert not args.assume_yes

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_detach_parser_with_json_format(self, _m_resources, FakeConfig):
        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "detach", "--format", "json"]):
            args = full_parser.parse_args()

        assert "json" == args.format
