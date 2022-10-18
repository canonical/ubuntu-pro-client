import textwrap

import mock
import pytest

from uaclient import event_logger, exceptions
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from uaclient.cli import (
    action_auto_attach,
    auto_attach_parser,
    get_parser,
    main,
)
from uaclient.exceptions import AlreadyAttachedOnPROError, NonRootUserError

M_PATH = "uaclient.cli."
M_ID_PATH = "uaclient.clouds.identity."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro auto-attach [flags]

Automatically attach on an Ubuntu Pro cloud instance.

Flags:
  -h, --help  show this help message and exit
"""
)


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_auto_attach(mock.MagicMock(), cfg=cfg)


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAutoAttach:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_auto_attach_help(self, _m_resources, _getuid, capsys, FakeConfig):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "auto-attach", "--help"]
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    def test_error_if_attached(
        self,
        _m_getuid,
        FakeConfig,
    ):
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(AlreadyAttachedOnPROError):
            action_auto_attach(mock.MagicMock(), cfg=cfg)

    @pytest.mark.parametrize(
        "features_override", ((None), ({"disable_auto_attach": True}))
    )
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_disable_auto_attach_config(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        _m_getuid,
        features_override,
        FakeConfig,
    ):
        cfg = FakeConfig()
        if features_override:
            cfg.override_features(features_override)

        ret = action_auto_attach(mock.MagicMock(), cfg=cfg)

        assert 0 == ret
        if features_override:
            assert [] == m_full_auto_attach.call_args_list
            assert [] == m_post_cli_attach.call_args_list
        else:
            assert [
                mock.call(
                    FullAutoAttachOptions(enable=None, enable_beta=None),
                    cfg=cfg,
                    mode=event_logger.EventLoggerMode.CLI,
                )
            ] == m_full_auto_attach.call_args_list
            assert [mock.call(mock.ANY)] == m_post_cli_attach.call_args_list

    @pytest.mark.parametrize(
        "faa_side_effect, event_info",
        [
            (
                exceptions.UrlError(cause="cause"),
                "Failed to attach machine. See https://ubuntu.com/pro",
            ),
            (exceptions.UserFacingError("msg"), "msg"),
        ],
    )
    @mock.patch(M_PATH + "event")
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_handle_full_auto_attach_errors(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        m_event,
        _m_getuid,
        faa_side_effect,
        event_info,
        FakeConfig,
        capsys,
    ):
        m_full_auto_attach.side_effect = faa_side_effect
        cfg = FakeConfig()

        assert 1 == action_auto_attach(mock.MagicMock(), cfg=cfg)
        assert [mock.call(event_info)] == m_event.info.call_args_list
        assert [] == m_post_cli_attach.call_args_list


class TestParser:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_auto_attach_parser_updates_parser_config(
        self, _m_resources, FakeConfig
    ):
        """Update the parser configuration for 'auto-attach'."""
        m_parser = auto_attach_parser(mock.Mock())
        assert "pro auto-attach [flags]" == m_parser.usage
        assert "auto-attach" == m_parser.prog
        assert "Flags" == m_parser._optionals.title

        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "auto-attach"]):
            args = full_parser.parse_args()
        assert "auto-attach" == args.command
        assert "action_auto_attach" == args.action.__name__
