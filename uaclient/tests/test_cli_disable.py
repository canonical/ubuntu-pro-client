import mock
import pytest

from uaclient.cli import action_disable
from uaclient import exceptions
from uaclient import status
from uaclient.testing.fakes import FakeConfig


class TestDisable:
    @pytest.mark.parametrize(
        "disable_return,return_code", ((True, 0), (False, 1))
    )
    @mock.patch("uaclient.cli.entitlements")
    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    def test_entitlement_instantiated_and_disabled(
        self, _m_getuid, m_entitlements, disable_return, return_code
    ):
        m_entitlement_cls = mock.Mock()
        m_entitlement = m_entitlement_cls.return_value
        m_entitlement.disable.return_value = disable_return
        m_cfg = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "testitlement": m_entitlement_cls
        }

        args_mock = mock.Mock()
        args_mock.name = "testitlement"

        ret = action_disable(args_mock, m_cfg)

        assert [mock.call(m_cfg)] == m_entitlement_cls.call_args_list

        expected_disable_call = mock.call()
        assert [expected_disable_call] == m_entitlement.disable.call_args_list
        assert return_code == ret

        assert 1 == m_cfg.status.call_count

    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    def test_invalid_service_error_message(self, m_getuid):
        """Check invalid service name results in custom error message."""
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.name = "bogus"
            action_disable(args, cfg)
        assert status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL.format(
            operation="disable", name="bogus"
        ) == str(err.value)

    @mock.patch("uaclient.cli.os.getuid", return_value=0)
    def test_unattached_error_message(self, m_getuid):
        """Check that root user gets unattached message."""
        cfg = FakeConfig()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.name = "esm-infra"
            action_disable(args, cfg)
        assert status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL.format(
            name="esm-infra"
        ) == str(err.value)
