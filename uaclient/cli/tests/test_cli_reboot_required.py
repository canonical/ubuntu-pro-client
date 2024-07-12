import mock

from uaclient.cli.system import reboot_required_subcommand

M_PATH = "uaclient.cli.system."


class TestActionRebootRequired:
    @mock.patch(M_PATH + "_reboot_required")
    def test_returns_the_api_response(self, m_api_reboot_required, event):
        m_cfg = mock.MagicMock()
        with mock.patch.object(event, "info") as m_event_info:
            reboot_required_subcommand.action(mock.MagicMock(), cfg=m_cfg)

        assert [mock.call(m_cfg)] == m_api_reboot_required.call_args_list
        assert [
            mock.call(m_api_reboot_required.return_value.reboot_required)
        ] == m_event_info.call_args_list
