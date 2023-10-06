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
from uaclient.defaults import APPARMOR_PROFILES

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro collect-logs \[flags\]

Collect logs and relevant system information into a tarball.

(optional arguments|options):
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        tarball where the logs will be stored. \(Defaults to
                        ./pro_logs.tar.gz\)
"""  # noqa
)


class TestActionCollectLogs:
    @mock.patch("uaclient.log.setup_cli_logging")
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

    @pytest.mark.parametrize(
        "series,extension", (("jammy", "list"), ("noble", "sources"))
    )
    @pytest.mark.parametrize("is_root", ((True), (False)))
    @mock.patch("uaclient.util.we_are_currently_root")
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
    @mock.patch("pathlib.Path.stat")
    @mock.patch("os.chown")
    @mock.patch("os.path.isfile", return_value=True)
    @mock.patch("shutil.copy")
    @mock.patch("uaclient.actions.status")
    @mock.patch("uaclient.system.write_file")
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.system.subp", return_value=(None, None))
    @mock.patch("uaclient.log.get_user_log_file")
    @mock.patch("uaclient.log.get_all_user_log_files")
    @mock.patch("uaclient.system.get_release_info")
    def test_collect_logs(
        self,
        m_get_release_info,
        m_get_users,
        m_get_user,
        m_subp,
        _load_file,
        _write_file,
        m_status,
        m_shutilcopy,
        m_isfile,
        _chown,
        _stat,
        redact,
        _fopen,
        _tarfile,
        _glob,
        util_we_are_currently_root,
        is_root,
        series,
        extension,
        FakeConfig,
        tmpdir,
    ):
        m_status.return_value = {"user-id": ""}, 0
        m_get_release_info.return_value.series = series
        util_we_are_currently_root.return_value = is_root
        m_get_user.return_value = tmpdir.join("user-log").strpath
        m_get_users.return_value = [
            tmpdir.join("user1-log").strpath,
            tmpdir.join("user2-log").strpath,
        ]
        is_file_calls = 17 + len(APPARMOR_PROFILES)
        user_log_files = [mock.call(m_get_user())]
        if util_we_are_currently_root():
            user_log_files = [
                mock.call(m_get_users()[0]),
                mock.call(m_get_users()[1]),
            ]

        cfg = FakeConfig()
        action_collect_logs(mock.MagicMock(), cfg=cfg)

        assert m_subp.call_args_list == [
            mock.call(["cloud-id"], rcs=None),
            mock.call(["/snap/bin/canonical-livepatch", "status"], rcs=None),
            mock.call(["systemctl", "list-timers", "--all"], rcs=None),
            mock.call(
                [
                    "journalctl",
                    "--boot=0",
                    "-o",
                    "short-precise",
                    "-u",
                    "cloud-init-local.service",
                    "-u",
                    "cloud-init-config.service",
                    "-u",
                    "cloud-config.service",
                ],
                rcs=None,
            ),
            mock.call(
                [
                    "journalctl",
                    "-o",
                    "short-precise",
                    "-u",
                    "apt-news.service",
                    "-u",
                    "esm-cache.service",
                    "-u",
                    "ua-timer.service",
                    "-u",
                    "ua-auto-attach.service",
                    "-u",
                    "ua-reboot-cmds.service",
                    "-u",
                    "ubuntu-advantage.service",
                ],
                rcs=None,
            ),
            mock.call(["systemctl", "status", "apt-news.service"], rcs=[0, 3]),
            mock.call(
                ["systemctl", "status", "esm-cache.service"], rcs=[0, 3]
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
            mock.call(["journalctl", "-b", "-k", "--since=1 day ago"]),
        ]

        assert m_isfile.call_count == is_file_calls
        assert m_isfile.call_args_list == [
            mock.call("/etc/ubuntu-advantage/uaclient.conf"),
            mock.call(cfg.log_file),
            mock.call("/var/lib/ubuntu-advantage/jobs-status.json"),
            mock.call("/etc/cloud/build.info"),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-anbox-cloud.{}".format(
                    extension
                )
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-cc-eal.{}".format(extension)
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-cis.{}".format(extension)
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-esm-apps.{}".format(extension)
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-esm-infra.{}".format(extension)
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-fips.{}".format(extension)
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-fips-updates.{}".format(
                    extension
                )
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-fips-preview.{}".format(
                    extension
                )
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-realtime-kernel.{}".format(
                    extension
                )
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-ros.{}".format(extension)
            ),
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-ros-updates.{}".format(
                    extension
                )
            ),
            mock.call("/var/log/ubuntu-advantage.log"),
            mock.call("/var/log/ubuntu-advantage.log.1"),
            *[mock.call(f) for f in APPARMOR_PROFILES],
        ]
        # APPARMOR_PROFILES are not redacted
        assert redact.call_count == is_file_calls + len(user_log_files) - len(
            APPARMOR_PROFILES
        )
        assert m_shutilcopy.call_count == len(APPARMOR_PROFILES)


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
