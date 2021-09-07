from textwrap import dedent

import mock
import pytest

from uaclient import exceptions, status
from uaclient.cli import action_detach, detach_parser, get_parser
from uaclient.testing.fakes import FakeContractClient


def entitlement_cls_mock_factory(can_disable, name=None):
    m_instance = mock.Mock(can_disable=mock.Mock(return_value=can_disable))
    if name:
        m_instance.name = name
    return mock.Mock(return_value=m_instance)


@mock.patch("uaclient.cli.util.prompt_for_confirmation", return_value=True)
@mock.patch("uaclient.cli.os.getuid")
class TestActionDetach:
    def test_non_root_users_are_rejected(
        self, m_getuid, _m_prompt, FakeConfig
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        m_getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_detach(mock.MagicMock(), cfg)

    def test_unattached_error_message(self, m_getuid, _m_prompt, FakeConfig):
        """Check that root user gets unattached message."""

        m_getuid.return_value = 0
        cfg = FakeConfig()
        with pytest.raises(exceptions.UnattachedError) as err:
            action_detach(mock.MagicMock(), cfg)
        assert status.MESSAGE_UNATTACHED == err.value.msg

    @mock.patch("uaclient.cli.util.subp")
    def test_lock_file_exists(self, m_subp, m_getuid, m_prompt, FakeConfig):
        """Check when an operation holds a lock file, detach cannot run."""
        m_getuid.return_value = 0
        cfg = FakeConfig.for_attached_machine()
        with open(cfg.data_path("lock"), "w") as stream:
            stream.write("123:ua enable")
        with pytest.raises(exceptions.LockHeldError) as err:
            action_detach(mock.MagicMock(), cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: ua detach.\n"
            "Operation in progress: ua enable (pid:123)"
        ) == err.value.msg

    @pytest.mark.parametrize(
        "prompt_response,assume_yes,expect_disable",
        [(True, False, True), (False, False, False), (True, True, True)],
    )
    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.config.update_ua_messages")
    def test_entitlements_disabled_appropriately(
        self,
        update_ua_messages,
        m_client,
        m_entitlements,
        m_getuid,
        m_prompt,
        prompt_response,
        assume_yes,
        expect_disable,
        FakeConfig,
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
            entitlement_cls_mock_factory(True),
            entitlement_cls_mock_factory(False),
        ]

        args = mock.MagicMock(assume_yes=assume_yes)
        return_code = action_detach(args, cfg)

        # Check that can_disable is called correctly
        for ent_cls in m_entitlements.ENTITLEMENT_CLASSES:
            assert [
                mock.call(silent=True)
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
                mock.call(silent=False)
            ] == disabled_cls.return_value.disable.call_args_list
            assert 0 == return_code
        else:
            assert 0 == disabled_cls.return_value.disable.call_count
            assert 1 == return_code
        assert [mock.call(assume_yes=assume_yes)] == m_prompt.call_args_list

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.config.update_ua_messages")
    def test_config_cache_deleted(
        self,
        update_ua_messages,
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
        assert [mock.call(m_cfg)] == update_ua_messages.call_args_list

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.config.update_ua_messages")
    def test_correct_message_emitted(
        self,
        update_ua_messages,
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
        assert [mock.call(m_cfg)] == update_ua_messages.call_args_list

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.config.update_ua_messages")
    def test_returns_zero(
        self,
        update_ua_messages,
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
        assert [mock.call(m_cfg)] == update_ua_messages.call_args_list

    @pytest.mark.parametrize(
        "classes,expected_message",
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
            ),
        ],
    )
    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    @mock.patch("uaclient.config.update_ua_messages")
    def test_informational_message_emitted(
        self,
        m_update_ua_messages,
        m_client,
        m_entitlements,
        m_getuid,
        _m_prompt,
        capsys,
        classes,
        expected_message,
        FakeConfig,
        tmpdir,
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = classes

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.check_lock_info.return_value = (-1, "")
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath

        action_detach(mock.MagicMock(), m_cfg)

        out, _err = capsys.readouterr()

        assert expected_message in out


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

    def test_detach_parser_accepts_and_stores_assume_yes(self):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "detach", "--assume-yes"]):
            args = full_parser.parse_args()

        assert args.assume_yes

    def test_detach_parser_defaults_to_not_assume_yes(self):
        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "detach"]):
            args = full_parser.parse_args()

        assert not args.assume_yes
