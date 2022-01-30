import contextlib
import io
import json
from textwrap import dedent

import mock
import pytest

from uaclient import event_logger, exceptions, status
from uaclient.cli import (
    action_detach,
    detach_parser,
    get_parser,
    main_error_handler,
)
from uaclient.testing.fakes import FakeContractClient


def entitlement_cls_mock_factory(can_disable, name=None):
    m_instance = mock.MagicMock()
    m_instance.can_disable.return_value = (can_disable, None)
    m_instance.disable.return_value = (can_disable, None)
    type(m_instance).dependent_services = mock.PropertyMock(return_value=())
    if name:
        type(m_instance).name = mock.PropertyMock(return_value=name)

    return mock.Mock(return_value=m_instance)


@mock.patch("uaclient.cli.util.prompt_for_confirmation", return_value=True)
@mock.patch("uaclient.cli.os.getuid")
class TestActionDetach:
    def test_non_root_users_are_rejected(
        self, m_getuid, _m_prompt, FakeConfig, event, capsys
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        m_getuid.return_value = 1
        args = mock.MagicMock()

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_detach(args, cfg=cfg)

        args.format = "json"
        # For json format, we need that flag
        args.assume_yes = True
        with pytest.raises(SystemExit):
            main_error_handler(action_detach)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": status.MESSAGE_NONROOT_USER,
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
        self, m_getuid, _m_prompt, FakeConfig, capsys, event
    ):
        """Check that root user gets unattached message."""

        m_getuid.return_value = 0
        cfg = FakeConfig()
        args = mock.MagicMock()
        with pytest.raises(exceptions.UnattachedError) as err:
            action_detach(args, cfg=cfg)
        assert status.MESSAGE_UNATTACHED == err.value.msg

        args.format = "json"
        # For json format, we need that flag
        args.assume_yes = True
        with pytest.raises(SystemExit):
            main_error_handler(action_detach)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": status.MESSAGE_UNATTACHED,
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

    @mock.patch("uaclient.cli.util.subp")
    def test_lock_file_exists(
        self, m_subp, m_getuid, m_prompt, FakeConfig, capsys, event
    ):
        """Check when an operation holds a lock file, detach cannot run."""
        m_getuid.return_value = 0
        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        with open(cfg.data_path("lock"), "w") as stream:
            stream.write("123:ua enable")
        with pytest.raises(exceptions.LockHeldError) as err:
            action_detach(args, cfg=cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        expected_error_msg = (
            "Unable to perform: ua detach.\n"
            "Operation in progress: ua enable (pid:123)"
        )
        assert expected_error_msg == err.value.msg

        args.format = "json"
        # For json format, we need that flag
        args.assume_yes = True
        with pytest.raises(SystemExit):
            main_error_handler(action_detach)(args, cfg)

        expected = {
            "_schema_version": event_logger.JSON_SCHEMA_VERSION,
            "result": "failure",
            "errors": [
                {
                    "message": expected_error_msg,
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
    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.cli.update_apt_and_motd_messages")
    def test_entitlements_disabled_appropriately(
        self,
        m_update_apt_and_motd_msgs,
        m_client,
        m_entitlements,
        m_getuid,
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
        m_getuid.return_value = 0

        cfg = FakeConfig.for_attached_machine()
        fake_client = FakeContractClient(cfg)
        m_client.return_value = fake_client

        m_prompt.return_value = prompt_response

        m_entitlements.ENTITLEMENT_CLASSES = [
            entitlement_cls_mock_factory(False),
            entitlement_cls_mock_factory(True, name="test"),
            entitlement_cls_mock_factory(False),
        ]

        args = mock.MagicMock(assume_yes=assume_yes)
        return_code = action_detach(args, cfg=cfg)

        # Check that can_disable is called correctly
        for ent_cls in m_entitlements.ENTITLEMENT_CLASSES:
            assert [
                mock.call(ignore_dependent_services=True)
            ] == ent_cls.return_value.can_disable.call_args_list

            assert [
                mock.call(cfg=cfg, assume_yes=assume_yes)
            ] == ent_cls.call_args_list

        # Check that disable is only called when can_disable is true
        for undisabled_cls in [
            m_entitlements.ENTITLEMENT_CLASSES[0],
            m_entitlements.ENTITLEMENT_CLASSES[2],
        ]:
            assert 0 == undisabled_cls.return_value.disable.call_count
        disabled_cls = m_entitlements.ENTITLEMENT_CLASSES[1]
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
        args.format = "json"
        # For json format, we need that flag
        args.assume_yes = True
        fake_stdout = io.StringIO()
        # On json response, we will never prompt the user
        m_prompt.return_value = True
        with contextlib.redirect_stdout(fake_stdout):
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

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.cli.update_apt_and_motd_messages")
    def test_config_cache_deleted(
        self,
        m_update_apt_and_motd_msgs,
        m_client,
        m_entitlements,
        m_getuid,
        _m_prompt,
        FakeConfig,
        tmpdir,
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = []

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        action_detach(mock.MagicMock(), m_cfg)

        assert [mock.call()] == m_cfg.delete_cache.call_args_list
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.cli.update_apt_and_motd_messages")
    def test_correct_message_emitted(
        self,
        m_update_apt_and_motd_msgs,
        m_client,
        m_entitlements,
        m_getuid,
        _m_prompt,
        capsys,
        FakeConfig,
        tmpdir,
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = []

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        action_detach(mock.MagicMock(), m_cfg)

        out, _err = capsys.readouterr()

        assert status.MESSAGE_DETACH_SUCCESS + "\n" == out
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.cli.update_apt_and_motd_messages")
    def test_returns_zero(
        self,
        m_update_apt_and_motd_msgs,
        m_client,
        m_entitlements,
        m_getuid,
        _m_prompt,
        FakeConfig,
        tmpdir,
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = []

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        ret = action_detach(mock.MagicMock(), m_cfg)

        assert 0 == ret
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

    @pytest.mark.parametrize(
        "classes,expected_message,disabled_services",
        [
            (
                [
                    entitlement_cls_mock_factory(True, name="ent1"),
                    entitlement_cls_mock_factory(False, name="ent2"),
                    entitlement_cls_mock_factory(True, name="ent3"),
                ],
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
                dedent(
                    """\
                    Detach will disable the following service:
                        ent1"""
                ),
                ["ent1"],
            ),
        ],
    )
    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.cli.update_apt_and_motd_messages")
    def test_informational_message_emitted(
        self,
        m_update_apt_and_motd_msgs,
        m_client,
        m_entitlements,
        m_getuid,
        _m_prompt,
        capsys,
        classes,
        expected_message,
        disabled_services,
        FakeConfig,
        tmpdir,
        event,
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = classes

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        args = mock.MagicMock()

        action_detach(args, m_cfg)

        out, _err = capsys.readouterr()

        assert expected_message in out
        assert [mock.call(m_cfg)] == m_update_apt_and_motd_msgs.call_args_list

        cfg = FakeConfig.for_attached_machine()
        args.format = "json"
        # For json format, we need that flag
        args.assume_yes = True
        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
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
        assert "ua detach [flags]" == parser.usage

    def test_detach_parser_prog(self):
        parser = detach_parser(mock.Mock())
        assert "detach" == parser.prog

    def test_detach_parser_optionals_title(self):
        parser = detach_parser(mock.Mock())
        assert "Flags" == parser._optionals.title

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_detach_parser_accepts_and_stores_assume_yes(self, _m_resources):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "detach", "--assume-yes"]):
            args = full_parser.parse_args()

        assert args.assume_yes

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_detach_parser_defaults_to_not_assume_yes(self, _m_resources):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "detach"]):
            args = full_parser.parse_args()

        assert not args.assume_yes

    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_detach_parser_with_json_format(self, _m_resources):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "detach", "--format", "json"]):
            args = full_parser.parse_args()

        assert "json" == args.format
