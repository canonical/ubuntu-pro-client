import textwrap

import mock
import pytest

from uaclient import event_logger, exceptions
from uaclient.api import exceptions as api_exceptions
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from uaclient.cli import (
    action_auto_attach,
    auto_attach_parser,
    get_parser,
    main,
    main_error_handler,
)

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


@mock.patch(M_PATH + "util.we_are_currently_root", return_value=False)
def test_non_root_users_are_rejected(we_are_currently_root, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""

    cfg = FakeConfig()
    with pytest.raises(exceptions.NonRootUserError):
        action_auto_attach(mock.MagicMock(), cfg=cfg)


class TestActionAutoAttach:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_auto_attach_help(self, _m_resources, capsys, FakeConfig):
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

    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_happy_path(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        FakeConfig,
    ):
        cfg = FakeConfig()

        assert 0 == action_auto_attach(mock.MagicMock(), cfg=cfg)

        assert [
            mock.call(
                FullAutoAttachOptions(enable=None, enable_beta=None),
                cfg=cfg,
                mode=event_logger.EventLoggerMode.CLI,
            )
        ] == m_full_auto_attach.call_args_list
        assert [mock.call(cfg)] == m_post_cli_attach.call_args_list

    @mock.patch(M_PATH + "event")
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_handle_full_auto_attach_errors(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        m_event,
        FakeConfig,
    ):
        m_full_auto_attach.side_effect = exceptions.UrlError(
            cause="does-not-matter"
        )
        cfg = FakeConfig()

        assert 1 == action_auto_attach(mock.MagicMock(), cfg=cfg)

        assert [
            mock.call("Failed to attach machine. See https://ubuntu.com/pro")
        ] == m_event.info.call_args_list
        assert [] == m_post_cli_attach.call_args_list

    @pytest.mark.parametrize(
        "api_side_effect, expected_err",
        [
            (exceptions.UserFacingError("foo"), "foo\n"),
            (
                exceptions.AlreadyAttachedError("foo"),
                "This machine is already attached to 'foo'\n"
                "To use a different subscription first run: sudo pro"
                " detach.\n",
            ),
            (
                api_exceptions.AutoAttachDisabledError,
                "features.disable_auto_attach set in config\n",
            ),
        ],
    )
    @mock.patch(M_PATH + "logging")
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_uncaught_errors_are_handled(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        m_logging,
        api_side_effect,
        expected_err,
        capsys,
        FakeConfig,
    ):
        m_full_auto_attach.side_effect = api_side_effect
        cfg = FakeConfig()
        with pytest.raises(SystemExit):
            assert 1 == main_error_handler(action_auto_attach)(
                mock.MagicMock(), cfg=cfg
            )
        _out, err = capsys.readouterr()
        assert expected_err == err
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
