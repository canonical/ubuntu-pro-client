import mock
import pytest

from uaclient.cli import action_disable
from uaclient import exceptions
from uaclient import status


@mock.patch("uaclient.cli.os.getuid", return_value=0)
class TestDisable:
    @pytest.mark.parametrize(
        "disable_return,return_code", ((True, 0), (False, 1))
    )
    @mock.patch("uaclient.cli.entitlements")
    def test_entitlement_instantiated_and_disabled(
        self, m_entitlements, _m_getuid, disable_return, return_code
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

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_invalid_service_error_message(
        self, m_getuid, uid, expected_error_template, FakeConfig
    ):
        """Check invalid service name results in custom error message."""
        m_getuid.return_value = uid

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.name = "bogus"
            action_disable(args, cfg)
        assert (
            expected_error_template.format(operation="disable", name="bogus")
            == err.value.msg
        )

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_unattached_error_message(
        self, m_getuid, uid, expected_error_template, FakeConfig
    ):
        """Check that root user gets unattached message."""
        m_getuid.return_value = uid

        cfg = FakeConfig()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.name = "esm-infra"
            action_disable(args, cfg)
        assert (
            expected_error_template.format(name="esm-infra") == err.value.msg
        )
