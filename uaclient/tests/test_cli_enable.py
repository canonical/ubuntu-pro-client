import mock

import pytest

from uaclient.cli import _perform_enable, action_enable
from uaclient import exceptions
from uaclient import status


@mock.patch("uaclient.cli.os.getuid")
class TestActionEnable:
    def test_non_root_users_are_rejected(self, getuid, FakeConfig):
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
        self, m_getuid, uid, expected_error_template, FakeConfig
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
        self, m_getuid, uid, expected_error_template, FakeConfig
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

    @pytest.mark.parametrize("assume_yes", (True, False))
    @mock.patch("uaclient.contract.get_available_resources", return_value={})
    @mock.patch("uaclient.contract.request_updated_contract")
    @mock.patch("uaclient.cli.entitlements")
    def test_assume_yes_passed_to_service_init(
        self,
        m_entitlements,
        m_request_updated_contract,
        _m_get_available_resources,
        m_getuid,
        assume_yes,
        FakeConfig,
    ):
        """assume-yes parameter is passed to entitlement instantiation."""
        m_getuid.return_value = 0

        m_entitlement_cls = mock.MagicMock()
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "testitlement": m_entitlement_cls
        }

        cfg = FakeConfig.for_attached_machine()
        args = mock.MagicMock()
        args.name = "testitlement"
        args.assume_yes = assume_yes
        action_enable(args, cfg)
        assert [
            mock.call(cfg, assume_yes=assume_yes)
        ] == m_entitlement_cls.call_args_list


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

    @pytest.mark.parametrize(
        "allow_beta, beta_call_count", ((True, 0), (False, 1))
    )
    @pytest.mark.parametrize("silent_if_inapplicable", (True, False, None))
    @mock.patch("uaclient.contract.get_available_resources", return_value={})
    @mock.patch("uaclient.cli.entitlements")
    def test_entitlement_instantiated_and_enabled(
        self,
        m_entitlements,
        _m_get_available_resources,
        silent_if_inapplicable,
        allow_beta,
        beta_call_count,
    ):
        m_entitlement_cls = mock.Mock()
        m_cfg = mock.Mock()
        m_is_beta = mock.PropertyMock(return_value=allow_beta)
        type(m_entitlement_cls).is_beta = m_is_beta

        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "testitlement": m_entitlement_cls
        }

        kwargs = {"allow_beta": allow_beta}
        if silent_if_inapplicable is not None:
            kwargs["silent_if_inapplicable"] = silent_if_inapplicable
        ret = _perform_enable("testitlement", m_cfg, **kwargs)

        assert [
            mock.call(m_cfg, assume_yes=False)
        ] == m_entitlement_cls.call_args_list

        m_entitlement = m_entitlement_cls.return_value
        if silent_if_inapplicable:
            expected_enable_call = mock.call(silent_if_inapplicable=True)
        else:
            expected_enable_call = mock.call(silent_if_inapplicable=False)
        assert [expected_enable_call] == m_entitlement.enable.call_args_list
        assert ret == m_entitlement.enable.return_value

        assert 1 == m_cfg.status.call_count
        assert beta_call_count == m_is_beta.call_count

    @pytest.mark.parametrize("silent_if_inapplicable", (True, False, None))
    @mock.patch("uaclient.cli.entitlements")
    def test_beta_entitlement_not_enabled(
        self, m_entitlements, silent_if_inapplicable
    ):
        m_entitlement_cls = mock.Mock()
        m_cfg = mock.Mock()
        m_is_beta = mock.PropertyMock(return_value=True)
        type(m_entitlement_cls).is_beta = m_is_beta

        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            "testitlement": m_entitlement_cls
        }

        kwargs = {"allow_beta": False}
        if silent_if_inapplicable is not None:
            kwargs["silent_if_inapplicable"] = silent_if_inapplicable

        with pytest.raises(exceptions.UserFacingError):
            _perform_enable("testitlement", m_cfg, **kwargs)

        assert 1 == m_is_beta.call_count
