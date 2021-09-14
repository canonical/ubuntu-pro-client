import textwrap

import mock
import pytest

from uaclient.cli import (
    action_collect_logs,
    collect_logs_parser,
    get_parser,
    main,
)
from uaclient.exceptions import NonRootUserError

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: ua collect-logs [flags]

Collect UA logs and relevant system information into a tarball.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        tarball where the logs will be stored. (Defaults to
                        ./ua_logs.tar.gz)
"""
)


@mock.patch(M_PATH + "os.getuid")
def test_non_root_users_are_rejected(getuid, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_collect_logs(mock.MagicMock(), cfg=cfg)


@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionAutoAttach:
    def test_collect_logs_help(self, _getuid, capsys):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "collect-logs", "--help"]
            ):
                main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @mock.patch(M_PATH + "tarfile.open")
    # let's pretend all files exist
    @mock.patch(M_PATH + "os.path.isfile", return_value=True)
    @mock.patch(M_PATH + "util.write_file")
    @mock.patch(M_PATH + "shutil.copy")
    @mock.patch(M_PATH + "util.subp", return_value=(None, None))
    def test_collect_logs(
        self,
        m_subp,
        m_copy,
        _write_file,
        _isfile,
        _tarfile,
        _getuid,
        FakeConfig,
    ):
        cfg = FakeConfig()
        action_collect_logs(mock.MagicMock(), cfg=cfg)

        assert m_subp.call_args_list == [
            mock.call(["cloud-id"], rcs=None),
            mock.call(["ua", "status", "--format", "json"], rcs=None),
            mock.call(["canonical-livepatch", "status"], rcs=None),
            mock.call(["systemctl", "list-timers", "--all"], rcs=None),
            mock.call(
                [
                    "journalctl",
                    "--boot=0",
                    "-o",
                    "short-precise",
                    "-u",
                    "ua-timer.service",
                    "-u",
                    "ua-auto-attach.service",
                    "-u",
                    "ua-reboot-cmds.service",
                    "-u",
                    "ua-license-check.service",
                    "-u",
                    "cloud-init-local.service",
                    "-u",
                    "cloud-init-config.service",
                    "-u",
                    "cloud-config.service",
                ],
                rcs=None,
            ),
            mock.call(["systemctl", "status", "ua-timer.service"], rcs=[0, 3]),
            mock.call(["systemctl", "status", "ua-timer.timer"], rcs=[0, 3]),
            mock.call(
                ["systemctl", "status", "ua-auto-attach.path"], rcs=[0, 3]
            ),
            mock.call(
                ["systemctl", "status", "ua-auto-attach.service"], rcs=[0, 3]
            ),
            mock.call(
                ["systemctl", "status", "ua-reboot-cmds.service"], rcs=[0, 3]
            ),
            mock.call(
                ["systemctl", "status", "ua-license-check.path"], rcs=[0, 3]
            ),
            mock.call(
                ["systemctl", "status", "ua-license-check.service"], rcs=[0, 3]
            ),
            mock.call(
                ["systemctl", "status", "ua-license-check.timer"], rcs=[0, 3]
            ),
        ]

        assert m_copy.call_count == 13


class TestParser:
    def test_collect_logs_parser_updates_parser_config(self):
        """Update the parser configuration for 'collect-logs'."""
        m_parser = collect_logs_parser(mock.Mock())
        assert "ua collect-logs [flags]" == m_parser.usage
        assert "collect-logs" == m_parser.prog

        full_parser = get_parser()
        with mock.patch("sys.argv", ["ua", "collect-logs"]):
            args = full_parser.parse_args()
        assert "collect-logs" == args.command
        assert "action_collect_logs" == args.action.__name__
