import mock
import pytest

from uaclient.api import exceptions
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    _full_auto_attach,
    _is_incompatible_services_present,
)
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)
from uaclient.messages import NamedMessage

M_API = "uaclient.api.u.pro."


class TestFullAutoAttachV1:
    @mock.patch(
        "uaclient.actions.enable_entitlement_by_name",
        return_value=(True, None),
    )
    def test_error_when_beta_in_enable_list(
        self,
        enable_ent_by_name,
        FakeConfig,
    ):
        cfg = FakeConfig(root_mode=True)
        options = FullAutoAttachOptions(
            enable=["esm-infra", "realtime-kernel"]
        )
        with pytest.raises(exceptions.BetaServiceError):
            _full_auto_attach(options, cfg)

        assert 0 == enable_ent_by_name.call_count

    @mock.patch(
        "uaclient.actions.enable_entitlement_by_name",
        return_value=(True, None),
    )
    @mock.patch("uaclient.actions.get_cloud_instance")
    @mock.patch("uaclient.actions.auto_attach")
    def test_error_invalid_ent_names(
        self,
        _auto_attach,
        _get_cloud_instance,
        enable_ent_by_name,
        FakeConfig,
    ):
        cfg = FakeConfig(root_mode=True)
        options = FullAutoAttachOptions(
            enable=["esm-infra", "cis"],
            enable_beta=["esm-apps", "realtime-kernel", "test", "wrong"],
        )
        with pytest.raises(exceptions.EntitlementNotFoundError):
            _full_auto_attach(options, cfg)

        assert 0 == enable_ent_by_name.call_count

    @mock.patch(
        "uaclient.actions.enable_entitlement_by_name",
        return_value=(
            False,
            CanEnableFailure(
                CanEnableFailureReason.ALREADY_ENABLED,
                NamedMessage("test", "test"),
            ),
        ),
    )
    @mock.patch("uaclient.actions.get_cloud_instance")
    @mock.patch("uaclient.actions.auto_attach")
    def test_error_ent_not_enabled(
        self,
        _auto_attach,
        _get_cloud_instance,
        enable_ent_by_name,
        FakeConfig,
    ):
        cfg = FakeConfig(root_mode=True)
        options = FullAutoAttachOptions(
            enable=["esm-infra", "cis"],
            enable_beta=["esm-apps", "realtime-kernel"],
        )
        with pytest.raises(exceptions.EntitlementNotEnabledError):
            _full_auto_attach(options, cfg)

        assert 1 == enable_ent_by_name.call_count

    @mock.patch(
        "uaclient.actions.enable_entitlement_by_name",
        return_value=(False, None),
    )
    @mock.patch("uaclient.actions.get_cloud_instance")
    @mock.patch("uaclient.actions.auto_attach")
    def test_error_full_auto_attach_fail(
        self,
        _auto_attach,
        _get_cloud_instance,
        enable_ent_by_name,
        FakeConfig,
    ):
        cfg = FakeConfig(root_mode=True)
        options = FullAutoAttachOptions(
            enable=["esm-infra", "fips"],
            enable_beta=["esm-apps", "ros"],
        )
        with pytest.raises(exceptions.EntitlementNotEnabledError):
            _full_auto_attach(options, cfg)

        assert 1 == enable_ent_by_name.call_count

    @mock.patch(
        "uaclient.lock.SpinLock.__enter__",
        side_effect=[
            exceptions.LockHeldError("request", "holder", 10),
        ],
    )
    def test_lock_held(self, _m_spinlock_enter, FakeConfig):
        with pytest.raises(exceptions.LockHeldError):
            _full_auto_attach(FullAutoAttachOptions, FakeConfig())

    def test_error_incompatible_services(
        self,
        FakeConfig,
    ):
        cfg = FakeConfig(root_mode=True)
        options = FullAutoAttachOptions(
            enable=["esm-infra", "fips"],
            enable_beta=["esm-apps", "livepatch"],
        )
        with pytest.raises(exceptions.IncompatibleEntitlementsDetected) as e:
            _full_auto_attach(options, cfg)

        expected_info = {
            "service": "fips",
            "incompatible_services": "livepatch,fips-updates,realtime-kernel",
        }

        assert expected_info == e.value.additional_info

    @pytest.mark.parametrize(
        "ent_list,service,incompatible_services,detected",
        (
            (
                ["fips", "esm-infra", "fips-updates", "esm-apps"],
                "fips",
                ["livepatch", "fips-updates", "realtime-kernel"],
                True,
            ),
            (
                ["fips-updates", "esm-infra", "realtime-kernel", "esm-apps"],
                "fips-updates",
                ["fips", "realtime-kernel"],
                True,
            ),
            (
                ["livepatch", "esm-infra", "esm-apps"],
                "",
                [],
                False,
            ),
        ),
    )
    def test_incompatible_services(
        self, ent_list, service, incompatible_services, detected, FakeConfig
    ):
        res = _is_incompatible_services_present(FakeConfig(), ent_list)
        assert detected == res[0]
        assert service == res[1]
        assert incompatible_services == res[2]
