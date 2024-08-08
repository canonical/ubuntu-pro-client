import contextlib
import io
import json

import mock
import pytest

from uaclient import messages, status
from uaclient.cli.help import help_command
from uaclient.exceptions import UbuntuProError


class TestCLIParser:
    @pytest.mark.parametrize(
        "out_format, expected_return",
        (
            (
                "tabular",
                "\n\n".join(
                    ["Name:\ntest", "Available:\nyes", "Help:\nTest\n\n"]
                ),
            ),
            ("json", {"name": "test", "available": "yes", "help": "Test"}),
        ),
    )
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.status._is_attached")
    def test_help_command_when_unnatached(
        self, m_attached, m_available_resources, out_format, expected_return
    ):
        """
        Test help command for a valid service in an unattached pro client.
        """
        m_args = mock.MagicMock()
        m_service_name = mock.PropertyMock(return_value="test")
        type(m_args).service = m_service_name
        m_format = mock.PropertyMock(return_value=out_format)
        type(m_args).format = m_format

        m_ent_help_info = mock.PropertyMock(return_value="Test")
        m_entitlement_obj = mock.MagicMock()
        type(m_entitlement_obj).help_info = m_ent_help_info

        m_attached.return_value = mock.MagicMock(is_attached=False)

        m_available_resources.return_value = [
            {"name": "test", "available": True}
        ]

        fake_stdout = io.StringIO()
        with mock.patch(
            "uaclient.status.entitlement_factory",
            return_value=m_entitlement_obj,
        ):
            with contextlib.redirect_stdout(fake_stdout):
                help_command.action(m_args, cfg=None)

        if out_format == "tabular":
            assert expected_return.strip() == fake_stdout.getvalue().strip()
        else:
            assert expected_return == json.loads(fake_stdout.getvalue())

        assert 1 == m_service_name.call_count
        assert 1 == m_ent_help_info.call_count
        assert 1 == m_available_resources.call_count
        assert 1 == m_attached.call_count
        assert 1 == m_format.call_count

    @pytest.mark.parametrize(
        "ent_status, ent_msg",
        (
            (status.ContractStatus.ENTITLED, "yes"),
            (status.ContractStatus.UNENTITLED, "no"),
        ),
    )
    @mock.patch("uaclient.status.get_available_resources")
    @mock.patch("uaclient.status._is_attached")
    def test_help_command_when_attached(
        self, m_attached, m_available_resources, ent_status, ent_msg
    ):
        """Test help command for a valid service in an attached pro client."""
        m_args = mock.MagicMock()
        m_service_name = mock.PropertyMock(return_value="test")
        type(m_args).service = m_service_name

        m_ent_help_info = mock.PropertyMock(
            return_value="Test service\nService is being tested"
        )
        m_entitlement_obj = mock.MagicMock()
        type(m_entitlement_obj).help_info = m_ent_help_info

        m_entitlement_obj.contract_status.return_value = ent_status
        m_entitlement_obj.user_facing_status.return_value = (
            status.UserFacingStatus.ACTIVE,
            messages.NamedMessage("test-code", "active"),
        )
        m_ent_name = mock.PropertyMock(return_value="test")
        type(m_entitlement_obj).name = m_ent_name
        m_ent_desc = mock.PropertyMock(return_value="description")
        type(m_entitlement_obj).description = m_ent_desc

        m_attached.return_value = mock.MagicMock(is_attached=True)
        m_available_resources.return_value = [
            {"name": "test", "available": True}
        ]

        status_msg = "enabled" if ent_msg == "yes" else "—"
        ufs_call_count = 1 if ent_msg == "yes" else 0
        ent_name_call_count = 2 if ent_msg == "yes" else 1

        expected_msgs = [
            "Name:\ntest",
            "Entitled:\n{}".format(ent_msg),
            "Status:\n{}".format(status_msg),
        ]

        expected_msgs.append(
            "Help:\nTest service\nService is being tested\n\n"
        )

        expected_msg = "\n\n".join(expected_msgs)

        fake_stdout = io.StringIO()
        with mock.patch(
            "uaclient.status.entitlement_factory",
            return_value=m_entitlement_obj,
        ):
            with contextlib.redirect_stdout(fake_stdout):
                help_command.action(m_args, cfg=None)

        assert expected_msg.strip() == fake_stdout.getvalue().strip()
        assert 1 == m_service_name.call_count
        assert 1 == m_ent_help_info.call_count
        assert 1 == m_available_resources.call_count
        assert 1 == m_attached.call_count
        assert 1 == m_ent_desc.call_count
        assert ent_name_call_count == m_ent_name.call_count
        assert 1 == m_entitlement_obj.contract_status.call_count
        assert (
            ufs_call_count == m_entitlement_obj.user_facing_status.call_count
        )

    @mock.patch("uaclient.status.get_available_resources")
    def test_help_command_for_invalid_service(self, m_available_resources):
        """Test help command when an invalid service is provided."""
        m_args = mock.MagicMock()
        m_service_name = mock.PropertyMock(return_value="test")
        type(m_args).service = m_service_name

        m_available_resources.return_value = [
            {"name": "ent1", "available": True}
        ]

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            with pytest.raises(UbuntuProError) as excinfo:
                help_command.action(m_args, cfg=None)

        assert "No help available for 'test'" == str(excinfo.value)
        assert 1 == m_service_name.call_count
        assert 1 == m_available_resources.call_count
