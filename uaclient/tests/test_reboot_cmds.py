import logging
import mock
import pytest

from uaclient import exceptions
from uaclient.util import ProcessExecutionError

from lib.reboot_cmds import main, fix_pro_pkg_holds, run_command

M_FIPS_PATH = "uaclient.entitlements.fips.FIPSEntitlement."


class TestMain:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("lib.reboot_cmds.subp")
    def test_main_unattached_removes_marker(
        self, m_subp, FakeConfig, caplog_text
    ):
        cfg = FakeConfig()
        cfg.write_cache("marker-reboot-cmds", "samplecontent")
        main(args="notused", cfg=cfg)
        assert None is cfg.read_cache("marker-reboot-cmds")
        assert "Skipping reboot_cmds. Machine is unattached" in caplog_text()
        assert 0 == m_subp.call_count

    @mock.patch("lib.reboot_cmds.subp")
    def test_main_noops_when_no_marker(self, m_subp, FakeConfig):
        cfg = FakeConfig()
        assert None is cfg.read_cache("marker-reboot-cmds")
        main(args="notused", cfg=cfg)
        assert 0 == m_subp.call_count

    @mock.patch("lib.reboot_cmds.subp")
    def test_main_unattached_removes_marker_file(
        self, m_subp, FakeConfig, tmpdir
    ):
        cfg = FakeConfig.for_attached_machine()
        assert None is cfg.read_cache("marker-reboot-cmds")
        main(args="notused", cfg=cfg)
        assert 0 == m_subp.call_count


M_REPO_PATH = "uaclient.entitlements"


class TestFixProPkgHolds:
    def test_attempts_lock_file(self, FakeConfig):
        cfg = FakeConfig()
        with mock.patch("uaclient.config.UAConfig.check_lock_info") as m_lock:
            m_lock.return_value = (123, "ua refresh")
            with pytest.raises(exceptions.LockHeldError):
                fix_pro_pkg_holds(args=None, cfg=cfg)

    @pytest.mark.parametrize("caplog_text", [logging.WARN], indirect=True)
    @pytest.mark.parametrize("fips_status", ("enabled", "disabled"))
    @mock.patch("sys.exit")
    @mock.patch(M_FIPS_PATH + "install_packages")
    @mock.patch(M_FIPS_PATH + "setup_apt_config")
    def test_calls_setup_apt_config_and_install_packages_when_enabled(
        self,
        setup_apt_config,
        install_packages,
        exit,
        fips_status,
        FakeConfig,
        caplog_text,
    ):
        cfg = FakeConfig()
        fake_status_cache = {
            "services": [{"name": "fips", "status": fips_status}]
        }
        cfg.write_cache("status-cache", fake_status_cache)
        fix_pro_pkg_holds(args=None, cfg=cfg)
        if fips_status == "enabled":
            assert [mock.call()] == setup_apt_config.call_args_list
            assert [
                mock.call(cleanup_on_failure=False)
            ] == install_packages.call_args_list
        else:
            assert 0 == setup_apt_config.call_count
            assert 0 == install_packages.call_count
        assert 0 == exit.call_count


class TestRunCommand:
    @pytest.mark.parametrize("caplog_text", [logging.WARN], indirect=True)
    @mock.patch("sys.exit")
    @mock.patch("lib.reboot_cmds.subp")
    def test_run_command_failure(self, m_subp, m_exit, caplog_text):
        cmd = "foobar"
        m_cfg = mock.MagicMock()

        m_subp.side_effect = ProcessExecutionError(
            cmd=cmd, exit_code=1, stdout="foo", stderr="bar"
        )

        run_command(cmd=cmd, cfg=m_cfg)
        expected_msgs = [
            "Failed running cmd: foobar",
            "Return code: 1",
            "Stderr: bar",
            "Stdout: foo",
        ]

        for expected_msg in expected_msgs:
            assert expected_msg in caplog_text()

        assert m_subp.call_args_list == [mock.call(["foobar"], capture=True)]
        assert m_cfg.delete_cache_key.call_args_list == [
            mock.call("marker-reboot-cmds")
        ]
        assert m_exit.call_args_list == [mock.call(1)]
