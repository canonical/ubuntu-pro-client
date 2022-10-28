import textwrap
from typing import Optional

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


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(exceptions.NonRootUserError):
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

    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_happy_path(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        _m_getuid,
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

    @pytest.mark.parametrize(
        "faa_side_effect, event_info, exit_code",
        [
            (
                exceptions.UrlError(cause="does-not-matter"),
                "Failed to attach machine. See https://ubuntu.com/pro",
                1,
            ),
            (api_exceptions.AutoAttachDisabledError, None, 0),
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
        event_info: Optional[str],
        exit_code,
        FakeConfig,
    ):
        m_full_auto_attach.side_effect = faa_side_effect
        cfg = FakeConfig()

        assert exit_code == action_auto_attach(mock.MagicMock(), cfg=cfg)

        if event_info is not None:
            assert [mock.call(event_info)] == m_event.info.call_args_list
        else:
            assert [] == m_event.info.call_args_list
        assert [] == m_post_cli_attach.call_args_list

    @pytest.mark.parametrize(
        "api_side_effect",
        [exceptions.UserFacingError, exceptions.AlreadyAttachedError],
    )
    @mock.patch(M_PATH + "_post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_uncaught_errors_are_handled(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        _m_getuid,
        api_side_effect,
        capsys,
        FakeConfig,
    ):
        m_full_auto_attach.side_effect = api_side_effect
        cfg = FakeConfig()
        with pytest.raises(SystemExit):
            assert 1 == main_error_handler(action_auto_attach)(
                mock.MagicMock(), cfg
            )
        _out, err = capsys.readouterr()
        assert (
            "Unexpected error(s) occurred.\n"
            "For more details, see the log: /var/log/ubuntu-advantage.log\n"
            "To file a bug run: ubuntu-bug ubuntu-advantage-tools\n" == err
        )


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
