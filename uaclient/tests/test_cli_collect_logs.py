import re
import textwrap

import mock
import pytest

from uaclient.cli import (
    action_collect_logs,
    collect_logs_parser,
    get_parser,
    main,
)

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro collect-logs \[flags\]

Collect logs and relevant system information into a tarball.

(optional arguments|options):
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        tarball where the logs will be stored. \(Defaults to
                        ./ua_logs.tar.gz\)
"""  # noqa
)


class TestActionCollectLogs:
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_collect_logs_help(
        self, _m_resources, _m_setup_logging, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "collect-logs", "--help"]
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert re.match(HELP_OUTPUT, out)

    @mock.patch(
        "glob.glob",
        return_value=[
            "/var/log/ubuntu-advantage.log",
            "/var/log/ubuntu-advantage.log.1",
        ],
    )
    @mock.patch("tarfile.open")
    @mock.patch("builtins.open")
    @mock.patch(M_PATH + "util.redact_sensitive_logs", return_value="test")
    # let's pretend all files exist
    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch("uaclient.system.write_file")
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.system.subp", return_value=(None, None))
    def test_collect_logs(
        self,
        m_subp,
        _load_file,
        _write_file,
        m_isfile,
        redact,
        _fopen,
        _tarfile,
        _glob,
        FakeConfig,
    ):
        cfg = FakeConfig()
        action_collect_logs(mock.MagicMock(), cfg=cfg)

        assert m_subp.call_args_list == [
            mock.call(["cloud-id"], rcs=None),
            mock.call(["pro", "status", "--format", "json"], rcs=None),
            mock.call(["/snap/bin/canonical-livepatch", "status"], rcs=None),
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
                    "ubuntu-advantage.service",
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
                ["systemctl", "status", "ubuntu-advantage.service"], rcs=[0, 3]
            ),
        ]

        assert m_isfile.call_count == 17
        assert m_isfile.call_args_list == [
            mock.call("/etc/ubuntu-advantage/uaclient.conf"),
            mock.call(cfg.log_file),
            mock.call("/var/log/ubuntu-advantage-timer.log"),
            mock.call("/var/log/ubuntu-advantage-daemon.log"),
            mock.call("/var/lib/ubuntu-advantage/jobs-status.json"),
            mock.call("/etc/cloud/build.info"),
            mock.call("/etc/apt/sources.list.d/ubuntu-cc-eal.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-cis.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-esm-apps.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-esm-infra.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-fips.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-fips-updates.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-realtime-kernel.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-ros.list"),
            mock.call("/etc/apt/sources.list.d/ubuntu-ros-updates.list"),
            mock.call("/var/log/ubuntu-advantage.log"),
            mock.call("/var/log/ubuntu-advantage.log.1"),
        ]
        assert redact.call_count == 17


class TestParser:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_collect_logs_parser_updates_parser_config(
        self, _m_resources, FakeConfig
    ):
        """Update the parser configuration for 'collect-logs'."""
        m_parser = collect_logs_parser(mock.Mock())
        assert "pro collect-logs [flags]" == m_parser.usage
        assert "collect-logs" == m_parser.prog

        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "collect-logs"]):
            args = full_parser.parse_args()
        assert "collect-logs" == args.command
        assert "action_collect_logs" == args.action.__name__
