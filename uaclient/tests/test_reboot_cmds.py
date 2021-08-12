import logging

import mock
import pytest

from lib.reboot_cmds import (
    fix_pro_pkg_holds,
    main,
    process_reboot_operations,
    run_command,
)
from uaclient.status import MESSAGE_REBOOT_SCRIPT_FAILED
from uaclient.util import ProcessExecutionError

M_FIPS_PATH = "uaclient.entitlements.fips.FIPSEntitlement."


class TestMain:
    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    def test_retries_on_lock_file(self, FakeConfig, caplog_text):
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(SystemExit) as excinfo:
            with mock.patch(
                "uaclient.config.UAConfig.check_lock_info"
            ) as m_check_lock:
                m_check_lock.return_value = (123, "ua auto-attach")
                with mock.patch("lib.reboot_cmds.time.sleep") as m_sleep:
                    main(cfg=cfg)
        assert [
            mock.call(1),
            mock.call(1),
            mock.call(5),
        ] == m_sleep.call_args_list
        assert 1 == excinfo.value.code
        assert (
            "Lock not released. Unable to perform: ua-reboot-cmds"
        ) in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("lib.reboot_cmds.subp")
    def test_main_unattached_removes_marker(
        self, m_subp, FakeConfig, caplog_text
    ):
        cfg = FakeConfig()
        cfg.write_cache("marker-reboot-cmds", "samplecontent")
        main(cfg=cfg)
        assert None is cfg.read_cache("marker-reboot-cmds")
        assert "Skipping reboot_cmds. Machine is unattached" in caplog_text()
        assert 0 == m_subp.call_count

    @mock.patch("lib.reboot_cmds.subp")
    def test_main_noops_when_no_marker(self, m_subp, FakeConfig):
        cfg = FakeConfig()
        assert None is cfg.read_cache("marker-reboot-cmds")
        main(cfg=cfg)
        assert 0 == m_subp.call_count

    @mock.patch("lib.reboot_cmds.subp")
    def test_main_unattached_removes_marker_file(
        self, m_subp, FakeConfig, tmpdir
    ):
        cfg = FakeConfig.for_attached_machine()
        assert None is cfg.read_cache("marker-reboot-cmds")
        main(cfg=cfg)
        assert 0 == m_subp.call_count


M_REPO_PATH = "uaclient.entitlements"


class TestFixProPkgHolds:
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
        fix_pro_pkg_holds(cfg=cfg)
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


class TestProcessRebootOperations:
    @pytest.mark.parametrize("caplog_text", [logging.ERROR], indirect=True)
    @mock.patch("uaclient.config.UAConfig.delete_cache_key")
    @mock.patch("uaclient.config.UAConfig.check_lock_info")
    @mock.patch("uaclient.config.UAConfig.add_notice")
    @mock.patch("lib.reboot_cmds.fix_pro_pkg_holds")
    def test_process_reboot_operations_create_notice_when_it_fails(
        self,
        m_fix_pro_pkg_holds,
        m_add_notice,
        m_check_lock_info,
        _m_delete_cache_key,
        FakeConfig,
        caplog_text,
    ):
        m_check_lock_info.return_value = (0, 0)
        m_fix_pro_pkg_holds.side_effect = ProcessExecutionError("error")

        cfg = FakeConfig()
        cfg.for_attached_machine()
        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("uaclient.config.UAConfig.write_cache"):
                process_reboot_operations(cfg=cfg)

        expected_calls = [
            mock.call("", "Operation in progress: ua-reboot-cmds"),
            mock.call("", MESSAGE_REBOOT_SCRIPT_FAILED),
        ]

        assert expected_calls == m_add_notice.call_args_list

        expected_msgs = [
            "Failed running commands on reboot.",
            "Invalid command specified 'error'.",
        ]
        assert all(
            expected_msg in caplog_text() for expected_msg in expected_msgs
        )
