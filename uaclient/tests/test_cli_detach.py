import mock

# from textwrap import dedent

import pytest

from uaclient.cli import action_detach, detach_parser, get_parser
from uaclient import exceptions
from uaclient import status
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

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    def test_config_cache_deleted(
        self, m_client, m_entitlements, m_getuid, _m_prompt, FakeConfig, tmpdir
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = []

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        m_cfg.read_cache.return_value = ""
        m_cfg.write_cache.return_value = True
        action_detach(mock.MagicMock(), m_cfg)

        assert [mock.call()] == m_cfg.delete_cache.call_args_list
        assert [mock.call("machine-token")] == m_cfg.read_cache.call_args_list
        assert (
            mock.call("machine-token-saved", "")
            == m_cfg.write_cache.call_args_list[-1]
        )

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    def test_correct_message_emitted(
        self,
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
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        m_cfg.read_cache.return_value = ""
        m_cfg.write_cache.return_value = True
        action_detach(mock.MagicMock(), m_cfg)

        out, _err = capsys.readouterr()

        assert status.MESSAGE_DETACH_SUCCESS + "\n" == out
        assert [mock.call("machine-token")] == m_cfg.read_cache.call_args_list
        assert (
            mock.call("machine-token-saved", "")
            == m_cfg.write_cache.call_args_list[-1]
        )

    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.contract.UAContractClient")
    def test_returns_zero(
        self, m_client, m_entitlements, m_getuid, _m_prompt, FakeConfig, tmpdir
    ):
        m_getuid.return_value = 0
        m_entitlements.ENTITLEMENT_CLASSES = []

        fake_client = FakeContractClient(FakeConfig.for_attached_machine())
        m_client.return_value = fake_client

        m_cfg = mock.MagicMock()
        m_cfg.data_path.return_value = tmpdir.join("lock").strpath
        m_cfg.read_cache.return_value = ""
        m_cfg.write_cache.return_value = True
        ret = action_detach(mock.MagicMock(), m_cfg)

        assert 0 == ret
        assert [mock.call("machine-token")] == m_cfg.read_cache.call_args_list
        assert (
            mock.call("machine-token-saved", "")
            == m_cfg.write_cache.call_args_list[-1]
        )


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
