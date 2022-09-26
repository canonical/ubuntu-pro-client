from subprocess import TimeoutExpired

import mock
import pytest

from uaclient import exceptions
from uaclient.daemon import start, stop

M_PATH = "uaclient.daemon."


@mock.patch(M_PATH + "system.subp")
class TestStart:
    def test_start_success(self, m_subp):
        start()
        assert [
            mock.call(
                ["systemctl", "start", "ubuntu-advantage.service"], timeout=2.0
            )
        ] == m_subp.call_args_list

    @pytest.mark.parametrize(
        "err",
        (
            exceptions.ProcessExecutionError("cmd"),
            TimeoutExpired("cmd", 2.0),
        ),
    )
    @mock.patch(M_PATH + "LOG.warning")
    def test_start_warning(self, m_log_warning, m_subp, err):
        m_subp.side_effect = err
        start()
        assert [
            mock.call(
                ["systemctl", "start", "ubuntu-advantage.service"], timeout=2.0
            )
        ] == m_subp.call_args_list
        assert [mock.call(err)] == m_log_warning.call_args_list


@mock.patch(M_PATH + "system.subp")
class TestStop:
    def test_stop_success(self, m_subp):
        stop()
        assert [
            mock.call(
                ["systemctl", "stop", "ubuntu-advantage.service"], timeout=2.0
            )
        ] == m_subp.call_args_list

    @pytest.mark.parametrize(
        "err",
        (
            exceptions.ProcessExecutionError("cmd"),
            TimeoutExpired("cmd", 2.0),
        ),
    )
    @mock.patch(M_PATH + "LOG.warning")
    def test_stop_warning(self, m_log_warning, m_subp, err):
        m_subp.side_effect = err
        stop()
        assert [
            mock.call(
                ["systemctl", "stop", "ubuntu-advantage.service"], timeout=2.0
            )
        ] == m_subp.call_args_list
        assert [mock.call(err)] == m_log_warning.call_args_list
