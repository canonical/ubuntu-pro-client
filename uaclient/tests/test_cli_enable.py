import mock

import pytest

from uaclient.cli import _perform_enable, action_enable
from uaclient import exceptions
from uaclient import status
from uaclient.testing.fakes import FakeConfig


@mock.patch("uaclient.cli.os.getuid")
class TestActionEnable:
    def test_non_root_users_are_rejected(self, getuid):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_enable(mock.MagicMock(), cfg)

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_unattached_error_message(
        self, m_getuid, uid, expected_error_template
    ):
        """Check that root user gets unattached message."""

        m_getuid.return_value = uid
        cfg = FakeConfig()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.name = "esm-infra"
            action_enable(args, cfg)
        assert (
            expected_error_template.format(name="esm-infra") == err.value.msg
        )

    @pytest.mark.parametrize(
        "uid,expected_error_template",
        [
            (0, status.MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL),
            (1000, status.MESSAGE_NONROOT_USER),
        ],
    )
    def test_invalid_service_error_message(
        self, m_getuid, uid, expected_error_template
    ):
        """Check invalid service name results in custom error message."""

        m_getuid.return_value = uid
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as err:
            args = mock.MagicMock()
            args.name = "bogus"
            action_enable(args, cfg)
        assert (
            expected_error_template.format(operation="enable", name="bogus")
            == err.value.msg
        )


class TestPerformEnable:
    @mock.patch("uaclient.cli.entitlements")
    def test_missing_entitlement_raises_keyerror(self, m_entitlements):
        """We raise a KeyError on missing entitlements

        (This isn't a problem because any callers of _perform_enable should
        already have rejected invalid names.)
        """
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {}

        with pytest.raises(KeyError):
            _perform_enable("entitlement", mock.Mock())

    @pytest.mark.parametrize("silent_if_inapplicable", (True, False, None))
    @mock.patch("uaclient.cli.entitlements")
    def test_entitlement_instantiated_and_enabled(
        self, m_entitlements, silent_if_inapplicable
    ):
        m_entitlement_cls = mock.Mock()
        m_cfg = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "testitlement": m_entitlement_cls
        }

        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs["silent_if_inapplicable"] = silent_if_inapplicable
        ret = _perform_enable("testitlement", m_cfg, **kwargs)

        assert [mock.call(m_cfg)] == m_entitlement_cls.call_args_list

        m_entitlement = m_entitlement_cls.return_value
        if silent_if_inapplicable:
            expected_enable_call = mock.call(silent_if_inapplicable=True)
        else:
            expected_enable_call = mock.call(silent_if_inapplicable=False)
        assert [expected_enable_call] == m_entitlement.enable.call_args_list
        assert ret == m_entitlement.enable.return_value

        assert 1 == m_cfg.status.call_count
