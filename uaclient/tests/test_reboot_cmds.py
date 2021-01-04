import logging
import mock
import pytest

from uaclient.util import ProcessExecutionError
from lib.reboot_cmds import run_command


class TestRebootCmds:
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
