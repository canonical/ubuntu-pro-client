"""Tests related to uaclient.entitlement.base module."""

import copy
import logging
from functools import partial

import mock
import pytest

from uaclient import exceptions, messages, system, util
from uaclient.entitlements import base
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
    CanDisableFailure,
    CanDisableFailureReason,
    CanEnableFailure,
    CanEnableFailureReason,
    UserFacingStatus,
)
from uaclient.status import ContractStatus


class ConcreteTestEntitlement(base.UAEntitlement):
    name = "testconcreteentitlement"
    title = "Test Concrete Entitlement"
    description = "Entitlement for testing"

    def __init__(
        self,
        cfg=None,
        disable=None,
        enable=None,
        applicability_status=None,
        application_status=(ApplicationStatus.DISABLED, ""),
        supports_access_only=False,
        access_only=False,
        supports_purge=False,
        purge=False,
        dependent_services=None,
        required_services=None,
        incompatible_services=None,
        blocking_incompatible_services=None,
        variant_name="",
        **kwargs
    ):
        super().__init__(
            cfg,
            access_only=access_only,
            purge=purge,
        )
        self.supports_access_only = supports_access_only
        self.supports_purge = supports_purge
        self._disable = disable
        self._enable = enable
        self._applicability_status = applicability_status
        self._application_status = application_status
        self._dependent_services = dependent_services
        self._required_services = required_services
        self._incompatible_services = incompatible_services
        self._blocking_incompatible_services = blocking_incompatible_services
        self._variant_name = variant_name

    def _perform_disable(self, *args, **kwargs):
        self._application_status = (
            ApplicationStatus.DISABLED,
            "disable() called",
        )
        return self._disable

    def _perform_enable(self, *args, **kwargs):
        return self._enable

    def enable_steps(self):
        return 1

    def disable_steps(self):
        return 1

    def applicability_status(self):
        if self._applicability_status is not None:
            return self._applicability_status
        else:
            return super().applicability_status()

    def application_status(self):
        return self._application_status

    def blocking_incompatible_services(self):
        if self._blocking_incompatible_services is not None:
            return self._blocking_incompatible_services
        else:
            return super().blocking_incompatible_services()

    @property
    def variant_name(self):
        return self._variant_name

    @property
    def is_variant(self):
        return False if not self._variant_name else True


@pytest.fixture
def base_entitlement_factory(entitlement_factory):
    return partial(entitlement_factory, ConcreteTestEntitlement)


class TestEntitlement:
    def test_entitlement_abstract_class(self):
        """UAEntitlement is abstract requiring concrete methods."""
        with pytest.raises(TypeError):
            base.UAEntitlement()

    def test_init_default_sets_up_uaconfig(self):
        """UAEntitlement sets up a uaconfig instance upon init."""
        entitlement = ConcreteTestEntitlement()
        assert "/var/lib/ubuntu-advantage" == entitlement.cfg.data_dir

    def test_init_accepts_a_uaconfig(self, FakeConfig):
        """An instance of UAConfig can be passed to UAEntitlement."""
        cfg = FakeConfig(cfg_overrides={"data_dir": "/some/path"})
        entitlement = ConcreteTestEntitlement(cfg)
        assert "/some/path" == entitlement.cfg.data_dir


class TestEntitlementNames:
    def test_presentation_name(self, entitlement_factory):
        entitlement = entitlement_factory(
            ConcreteTestEntitlement,
            entitled=True,
        )
        assert "testconcreteentitlement" == entitlement.presentation_name


class TestEntitlementCanEnable:
    def test_can_enable_false_on_unentitled(self, base_entitlement_factory):
        """When entitlement contract is not enabled, can_enable is False."""
        entitlement = base_entitlement_factory(
            entitled=False,
        )

        can_enable, reason = entitlement.can_enable()
        assert not can_enable
        assert reason.reason == CanEnableFailureReason.NOT_ENTITLED
        assert (
            reason.message.msg
            == messages.UNENTITLED.format(
                title=ConcreteTestEntitlement.title
            ).msg
        )

    def test_can_enable_false_on_access_only_not_supported(
        self, base_entitlement_factory
    ):
        """When entitlement contract is not enabled, can_enable is False."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "supports_access_only": False,
                "access_only": True,
            },
        )

        can_enable, reason = entitlement.can_enable()
        assert not can_enable
        assert (
            reason.reason == CanEnableFailureReason.ACCESS_ONLY_NOT_SUPPORTED
        )
        assert (
            reason.message.msg
            == messages.ENABLE_ACCESS_ONLY_NOT_SUPPORTED.format(
                title=ConcreteTestEntitlement.title
            ).msg
        )

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.contract.refresh")
    def test_can_enable_updates_expired_contract(
        self,
        m_refresh,
        caplog_text,
        base_entitlement_factory,
    ):
        """When entitlement contract is not enabled, can_enable is False."""
        entitlement = base_entitlement_factory(
            entitled=False,
        )

        with mock.patch.object(
            entitlement, "is_access_expired", return_value=True
        ):
            assert not entitlement.can_enable()[0]

        assert [mock.call(entitlement.cfg)] == m_refresh.call_args_list
        assert (
            "Updating contract on service 'testconcreteentitlement' expiry"
            in caplog_text()
        )

    def test_can_enable_false_on_entitlement_active(
        self, base_entitlement_factory
    ):
        """When entitlement is ENABLED, can_enable returns False."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.ENABLED, ""),
            },
        )

        can_enable, reason = entitlement.can_enable()
        assert not can_enable
        assert reason.reason == CanEnableFailureReason.ALREADY_ENABLED
        assert (
            reason.message.msg
            == messages.ALREADY_ENABLED.format(
                title=ConcreteTestEntitlement.title
            ).msg
        )

    @pytest.mark.parametrize(
        "applicability_status,expected_ret,expected_reason",
        (
            (
                (ApplicabilityStatus.INAPPLICABLE, "msg"),
                False,
                CanEnableFailure(CanEnableFailureReason.INAPPLICABLE, "msg"),
            ),
            (
                (ApplicabilityStatus.APPLICABLE, ""),
                True,
                None,
            ),
        ),
    )
    def test_can_enable_on_entitlement_given_applicability_status(
        self,
        applicability_status,
        expected_ret,
        expected_reason,
        base_entitlement_factory,
    ):
        """When entitlement is INAPPLICABLE, can_enable returns False."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.DISABLED, ""),
                "applicability_status": applicability_status,
            },
        )

        can_enable, reason = entitlement.can_enable()
        assert expected_ret is can_enable

        if reason:
            assert expected_reason.reason == reason.reason
            assert expected_reason.message == reason.message
        else:
            assert expected_reason is None

    def test_can_enable_when_incompatible_service_found(
        self, base_entitlement_factory, mock_entitlement
    ):
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
            },
        )
        m_incompatible_cls, _ = mock_entitlement(
            application_status=(ApplicationStatus.ENABLED, "")
        )

        entitlement._incompatible_services = (
            base.EntitlementWithMessage(
                m_incompatible_cls, messages.NamedMessage("test", "test")
            ),
        )

        ret, reason = entitlement.can_enable()

        assert ret is False
        assert reason.reason == CanEnableFailureReason.INCOMPATIBLE_SERVICE
        assert reason.message is None

    def test_can_enable_when_required_service_found(
        self, base_entitlement_factory, mock_entitlement
    ):
        m_required_service_cls, _ = mock_entitlement(
            application_status=(ApplicationStatus.DISABLED, "")
        )

        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
                "required_services": (
                    mock.MagicMock(entitlement=m_required_service_cls),
                ),
            },
        )

        ret, reason = entitlement.can_enable()

        assert ret is False
        assert (
            reason.reason == CanEnableFailureReason.INACTIVE_REQUIRED_SERVICES
        )
        assert reason.message is None


class TestEntitlementEnable:
    @pytest.mark.parametrize(
        "block_disable_on_enable",
        [(False, False), (False, True), (True, False), (True, True)],
    )
    @mock.patch("uaclient.util.is_config_value_true")
    def test_enable_when_incompatible_service_found(
        self,
        m_is_config_value_true,
        block_disable_on_enable,
        base_entitlement_factory,
        mock_entitlement,
    ):
        m_is_config_value_true.return_value = block_disable_on_enable
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
                "enable": True,
            },
        )

        m_incompatible_cls, m_incompatible_obj = mock_entitlement(
            application_status=(ApplicationStatus.ENABLED, ""),
            disable=(True, None),
        )
        entitlement._incompatible_services = (
            base.EntitlementWithMessage(
                m_incompatible_cls, messages.NamedMessage("test", "test")
            ),
        )

        ret, reason = entitlement.enable(mock.MagicMock())

        expected_ret = False
        expected_reason = CanEnableFailureReason.INCOMPATIBLE_SERVICE
        if not block_disable_on_enable:
            expected_ret = True
            expected_reason = None
        expected_disable_call = 1 if expected_ret else 0

        assert ret == expected_ret
        if expected_reason is None:
            assert reason is None
        else:
            assert reason.reason == expected_reason
        assert m_is_config_value_true.call_count == 1
        assert m_incompatible_obj.disable.call_count == expected_disable_call

    def test_enable_when_required_service_found(
        self, base_entitlement_factory, mock_entitlement
    ):
        m_required_service_cls, m_required_service_obj = mock_entitlement(
            application_status=(ApplicationStatus.DISABLED, ""),
            enable=(True, None),
        )

        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
                "enable": True,
                "required_services": (
                    mock.MagicMock(entitlement=m_required_service_cls),
                ),
            },
        )

        ret, reason = entitlement.enable(mock.MagicMock())

        assert ret is True
        assert reason is None
        assert m_required_service_obj.enable.call_count == 1

    @pytest.mark.parametrize(
        "can_enable_fail,handle_incompat_calls,enable_req_calls",
        [
            (
                CanEnableFailure(
                    CanEnableFailureReason.NOT_ENTITLED, message="msg"
                ),
                0,
                0,
            ),
            (
                CanEnableFailure(
                    CanEnableFailureReason.ALREADY_ENABLED,
                    message="msg",
                ),
                0,
                0,
            ),
            (
                CanEnableFailure(CanEnableFailureReason.INAPPLICABLE, "msg"),
                0,
                0,
            ),
            (
                CanEnableFailure(CanEnableFailureReason.INCOMPATIBLE_SERVICE),
                1,
                0,
            ),
            (
                CanEnableFailure(
                    CanEnableFailureReason.INACTIVE_REQUIRED_SERVICES
                ),
                0,
                1,
            ),
        ],
    )
    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement._enable_required_services",
        return_value=(False, "required error msg"),
    )
    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement.handle_incompatible_services",  # noqa: E501
        return_value=False,
    )
    @mock.patch("uaclient.entitlements.base.UAEntitlement.can_enable")
    def test_enable_false_when_can_enable_false(
        self,
        m_can_enable,
        m_handle_incompat,
        m_enable_required,
        can_enable_fail,
        handle_incompat_calls,
        enable_req_calls,
        base_entitlement_factory,
    ):
        """When can_enable returns False enable returns False."""
        m_can_enable.return_value = (False, can_enable_fail)
        m_handle_incompat.return_value = (False, None)
        entitlement = base_entitlement_factory(entitled=True)
        entitlement._perform_enable = mock.Mock()

        assert (False, can_enable_fail) == entitlement.enable(mock.MagicMock())

        assert 1 == m_can_enable.call_count
        assert handle_incompat_calls == m_handle_incompat.call_count
        assert enable_req_calls == m_enable_required.call_count
        assert 0 == entitlement._perform_enable.call_count

        if enable_req_calls:
            assert can_enable_fail.message == "required error msg"

    @pytest.mark.parametrize("enable_fail_message", (("not entitled"), (None)))
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.util.prompt_for_confirmation")
    def test_enable_false_when_fails_to_enable_required_service(
        self,
        m_handle_msg,
        m_prompt_for_confirmation,
        enable_fail_message,
        base_entitlement_factory,
        mock_entitlement,
    ):
        m_handle_msg.return_value = True

        fail_reason = CanEnableFailure(
            CanEnableFailureReason.INACTIVE_REQUIRED_SERVICES
        )

        if enable_fail_message:
            msg = messages.NamedMessage("test-code", enable_fail_message)
        else:
            msg = None

        enable_fail_reason = CanEnableFailure(
            CanEnableFailureReason.NOT_ENTITLED, message=msg
        )

        m_prompt_for_confirmation.return_vale = True

        m_required_service_cls, m_required_service_obj = mock_entitlement(
            application_status=(ApplicationStatus.DISABLED, ""),
            title="Test",
            enable=(False, enable_fail_reason),
        )

        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.DISABLED, ""),
                "required_services": (
                    mock.MagicMock(entitlement=m_required_service_cls),
                ),
            },
        )

        with mock.patch.object(entitlement, "can_enable") as m_can_enable:
            m_can_enable.return_value = (False, fail_reason)
            ret, fail = entitlement.enable(mock.MagicMock())

        assert not ret
        expected_msg = "Cannot enable required service: Test"
        if enable_fail_reason.message:
            expected_msg += "\n" + enable_fail_reason.message.msg
        assert expected_msg == fail.message.msg
        assert 1 == m_can_enable.call_count

    @mock.patch("uaclient.util.handle_message_operations")
    def test_enable_fails_when_blocking_service_is_enabled(
        self,
        _m_handle_message_op,
        mock_entitlement,
        base_entitlement_factory,
    ):
        expected_msg = messages.E_INCOMPATIBLE_SERVICE_STOPS_ENABLE.format(
            service_being_enabled=ConcreteTestEntitlement.title,
            incompatible_service="Test",
        )
        incompatible_service_cls, _ = mock_entitlement(
            application_status=(ApplicationStatus.ENABLED, ""),
            title="Test",
            disable=(
                False,
                CanDisableFailure(
                    CanDisableFailureReason.ACTIVE_DEPENDENT_SERVICES,
                    message=expected_msg,
                ),
            ),
        )
        incompatible_services_definition = base.EntitlementWithMessage(
            incompatible_service_cls, messages.NamedMessage("code", "msg")
        )
        entitlement = base_entitlement_factory(
            extra_args={
                "blocking_incompatible_services": [
                    incompatible_services_definition
                ],
                "incompatible_services": [incompatible_services_definition],
            },
        )

        result, reason = entitlement.enable(mock.MagicMock())
        assert not result
        assert expected_msg.msg == reason.message.msg.strip()


class TestEntitlementCanDisable:
    def test_can_disable_false_on_purge_not_supported(
        self, base_entitlement_factory
    ):
        """When the entitlement doesn't support purge, can_disable is FALSE."""
        entitlement = base_entitlement_factory(
            entitled=True,
            purge=True,
            extra_args={
                "supports_purge": False,
                "application_status": (ApplicationStatus.ENABLED, ""),
            },
        )

        can_disable, reason = entitlement.can_disable()
        assert can_disable is False
        assert reason.reason == CanDisableFailureReason.PURGE_NOT_SUPPORTED
        assert (
            reason.message.msg
            == messages.DISABLE_PURGE_NOT_SUPPORTED.format(
                title=ConcreteTestEntitlement.title
            ).msg
        )

    @pytest.mark.parametrize(
        "application_status,expected_ret,expected_fail",
        (
            (
                (ApplicationStatus.DISABLED, ""),
                False,
                CanDisableFailure(
                    CanDisableFailureReason.ALREADY_DISABLED,
                    messages.ALREADY_DISABLED.format(
                        title=ConcreteTestEntitlement.title
                    ),
                ),
            ),
            (
                (ApplicationStatus.ENABLED, ""),
                True,
                None,
            ),
        ),
    )
    def test_can_disable_given_entitlement_status(
        self,
        application_status,
        expected_ret,
        expected_fail,
        base_entitlement_factory,
    ):
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": application_status,
            },
        )

        ret, fail = entitlement.can_disable()
        assert expected_ret is ret

        if fail:
            assert expected_fail.message.msg == fail.message.msg
            assert expected_fail.reason == fail.reason
        else:
            assert expected_fail is None

    def test_can_disable_false_on_dependent_service(
        self, base_entitlement_factory, mock_entitlement
    ):
        m_required_service_cls, _ = mock_entitlement(
            application_status=(ApplicationStatus.ENABLED, None)
        )

        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.ENABLED, ""),
                "dependent_services": (m_required_service_cls,),
            },
        )

        ret, fail = entitlement.can_disable()
        assert not ret
        assert fail.reason == CanDisableFailureReason.ACTIVE_DEPENDENT_SERVICES
        assert fail.message is None

    @mock.patch("uaclient.entitlements.entitlement_factory")
    def test_can_disable_when_ignoring_dependent_service(
        self, m_ent_factory, base_entitlement_factory, mock_entitlement
    ):
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.ENABLED, ""),
                "dependent_services": ("test",),
            },
        )

        m_dependent_service_cls, _ = mock_entitlement(
            application_status=(ApplicationStatus.ENABLED, None)
        )
        m_ent_factory.return_value = m_dependent_service_cls

        ret, fail = entitlement.can_disable(ignore_dependent_services=True)
        assert ret is True
        assert fail is None


class TestEntitlementDisable:
    def test_disable_when_dependent_service_found(
        self, base_entitlement_factory, mock_entitlement
    ):
        m_dependent_service_cls, m_dependent_service_obj = mock_entitlement(
            application_status=(ApplicationStatus.ENABLED, ""),
            disable=(True, None),
        )
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.ENABLED, ""),
                "disable": True,
                "dependent_services": (m_dependent_service_cls,),
            },
        )

        ret, fail = entitlement.disable(mock.MagicMock())

        expected_ret = True
        expected_disable_call = 1

        assert ret == expected_ret
        assert fail is None
        assert (
            m_dependent_service_obj.disable.call_count == expected_disable_call
        )

    @pytest.mark.parametrize("disable_fail_message", (("error"), (None)))
    @mock.patch("uaclient.util.handle_message_operations")
    def test_disable_false_when_fails_to_disable_dependent_service(
        self,
        m_handle_msg,
        disable_fail_message,
        base_entitlement_factory,
        mock_entitlement,
    ):
        m_handle_msg.return_value = True

        fail_reason = CanDisableFailure(
            CanDisableFailureReason.ACTIVE_DEPENDENT_SERVICES
        )

        msg = None
        if disable_fail_message:
            msg = messages.NamedMessage("test-code", disable_fail_message)

        disable_fail_reason = CanDisableFailure(
            CanDisableFailureReason.ALREADY_DISABLED, message=msg
        )
        m_dependent_service_cls, _ = mock_entitlement(
            name="Test",
            title="Test",
            disable=(False, disable_fail_reason),
            application_status=(ApplicationStatus.ENABLED, ""),
        )

        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.DISABLED, ""),
                "dependent_services": (m_dependent_service_cls,),
            },
        )

        with mock.patch.object(entitlement, "can_disable") as m_can_disable:
            m_can_disable.return_value = (False, fail_reason)
            ret, fail = entitlement.disable(mock.MagicMock())

        assert not ret
        expected_msg = messages.FAILED_DISABLING_DEPENDENT_SERVICE.format(
            required_service="Test",
            error="\n" + msg.msg if msg else "",
        ).msg
        assert expected_msg == fail.message.msg
        assert 1 == m_can_disable.call_count

    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
        self,
        base_entitlement_factory,
    ):
        """When can_disable is false disable returns false and noops."""
        entitlement = base_entitlement_factory()

        with mock.patch.object(
            entitlement, "can_disable", return_value=(False, None)
        ) as m_can_disable:
            ret, fail = entitlement.disable(mock.MagicMock())

        assert ret is False
        assert fail is None
        assert [mock.call()] == m_can_disable.call_args_list


class TestEntitlementContractStatus:
    @pytest.mark.parametrize(
        "entitled,expected_contract_status",
        (
            (
                True,
                ContractStatus.ENTITLED,
            ),
            (
                False,
                ContractStatus.UNENTITLED,
            ),
        ),
    )
    def test_contract_status(
        self, entitled, expected_contract_status, base_entitlement_factory
    ):
        entitlement = base_entitlement_factory(entitled=entitled)
        assert expected_contract_status == entitlement.contract_status()


class TestUserFacingStatus:
    @pytest.mark.parametrize(
        "entitled,applicability_status,application_status,expected_status,expected_details",  # noqa
        (
            (
                True,
                (
                    ApplicabilityStatus.INAPPLICABLE,
                    None,
                ),
                (
                    ApplicationStatus.DISABLED,
                    None,
                ),
                UserFacingStatus.INAPPLICABLE,
                None,
            ),
            (
                False,
                (
                    ApplicabilityStatus.APPLICABLE,
                    "",
                ),
                (
                    ApplicationStatus.DISABLED,
                    None,
                ),
                UserFacingStatus.UNAVAILABLE,
                messages.SERVICE_NOT_ENTITLED.format(
                    title=ConcreteTestEntitlement.title
                ),
            ),
            (
                True,
                (
                    ApplicabilityStatus.APPLICABLE,
                    "",
                ),
                (
                    ApplicationStatus.DISABLED,
                    None,
                ),
                UserFacingStatus.INACTIVE,
                None,
            ),
            (
                True,
                (
                    ApplicabilityStatus.APPLICABLE,
                    "",
                ),
                (
                    ApplicationStatus.WARNING,
                    None,
                ),
                UserFacingStatus.WARNING,
                None,
            ),
        ),
    )
    def test_user_facing_status(
        self,
        entitled,
        applicability_status,
        application_status,
        expected_status,
        expected_details,
        base_entitlement_factory,
    ):
        entitlement = base_entitlement_factory(
            entitled=entitled,
            extra_args={
                "applicability_status": applicability_status,
                "application_status": application_status,
            },
        )

        user_facing_status, details = entitlement.user_facing_status()
        assert expected_status == user_facing_status

        if details:
            assert expected_details.msg == details.msg
        else:
            assert expected_details is None

    def test_unavailable_when_applicable_but_no_entitlement_cfg(
        self, base_entitlement_factory
    ):
        entitlement = base_entitlement_factory(
            entitled=False,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, "")
            },
        )
        with mock.patch.object(
            entitlement, "_base_entitlement_cfg", return_value={}
        ):
            user_facing_status, details = entitlement.user_facing_status()

        assert UserFacingStatus.UNAVAILABLE == user_facing_status
        expected_details = messages.SERVICE_NOT_ENTITLED.format(
            title=entitlement.title
        ).msg
        assert expected_details == details.msg


class TestApplicabilityStatus:
    @pytest.mark.parametrize(
        (
            "arch,series,version,min_kernel,kernel_flavors,"
            "expected_status,expected_message"
        ),
        (
            (
                "arm64",
                "xenial",
                "16.04 LTS (Xenial Xerus)",
                "4.4",
                ["generic", "lowlatency"],
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_ARCH.format(
                    title=ConcreteTestEntitlement.title,
                    arch="arm64",
                    supported_arches=", ".join(["amd64", "s390x"]),
                ),
            ),
            (
                "s390x",
                "bionic",
                "18.04 LTS (Bionic Beaver)",
                "4.4",
                ["generic", "lowlatency"],
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_SERIES.format(
                    title=ConcreteTestEntitlement.title,
                    series="18.04 LTS (Bionic Beaver)",
                ),
            ),
            (
                "s390x",
                "xenial",
                "16.04 LTS (Xenial Xerus)",
                "5.0",
                ["generic", "lowlatency"],
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_KERNEL_VER.format(
                    title=ConcreteTestEntitlement.title,
                    kernel="4.19.0-00-generic",
                    min_kernel="5.0",
                ),
            ),
            (
                "s390x",
                "xenial",
                "16.04 LTS (Xenial Xerus)",
                "5.0",
                ["lowlatency"],
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_KERNEL.format(
                    title=ConcreteTestEntitlement.title,
                    kernel="4.19.0-00-generic",
                    supported_kernels="lowlatency",
                ),
            ),
            (
                "s390x",
                "xenial",
                "16.04 LTS (Xenial Xerus)",
                "4.4",
                ["generic", "lowlatency"],
                ApplicabilityStatus.APPLICABLE,
                None,
            ),
        ),
    )
    @mock.patch("uaclient.system.get_kernel_info")
    @mock.patch("uaclient.system.get_dpkg_arch")
    @mock.patch("uaclient.system.get_release_info")
    def test_applicability_status(
        self,
        m_release_info,
        m_dpkg_arch,
        m_get_kernel_info,
        arch,
        series,
        version,
        min_kernel,
        kernel_flavors,
        expected_status,
        expected_message,
        base_entitlement_factory,
    ):
        m_release_info.return_value = system.ReleaseInfo(
            distribution="", release="", series=series, pretty_version=version
        )
        m_get_kernel_info.return_value = system.KernelInfo(
            uname_machine_arch="",
            uname_release="4.19.0-00-generic",
            proc_version_signature_version="",
            build_date=None,
            major=4,
            minor=19,
            patch=0,
            abi="00",
            flavor="generic",
        )

        m_dpkg_arch.return_value = arch

        entitlement = base_entitlement_factory(
            directives={
                "aptURL": "http://CC",
                "aptKey": "APTKEY",
                "suites": ["xenial"],
                "additionalPackages": ["test-package"],
            },
            affordances={
                "architectures": ["x86_64", "s390x"],
                "series": ["xenial"],
                "minKernelVersion": min_kernel,
                "kernelFlavors": kernel_flavors,
            },
        )

        actual_status, actual_message = entitlement.applicability_status()
        assert expected_status == actual_status

        if expected_message:
            assert expected_message.msg == actual_message.msg
        else:
            assert actual_message is None


class TestEntitlementProcessContractDeltas:
    @pytest.mark.parametrize(
        "orig_access,delta",
        (({}, {}), ({}, {"entitlement": {"entitled": False}})),
    )
    def test_process_contract_deltas_does_nothing_on_empty_orig_access(
        self, base_entitlement_factory, orig_access, delta
    ):
        """When orig_acccess dict is empty perform no work."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
            },
        )
        with mock.patch.object(entitlement, "can_disable") as m_can_disable:
            entitlement.process_contract_deltas(orig_access, delta)
        assert 0 == m_can_disable.call_count

    @pytest.mark.parametrize(
        "orig_access,delta",
        (
            ({"entitlement": {"entitled": True}}, {}),  # no deltas
            (
                {"entitlement": {"entitled": False}},
                {"entitlement": {"entitled": True}},
            ),  # transition to entitled
            (
                {"entitlement": {"entitled": False}},
                {
                    "entitlement": {
                        "entitled": False,  # overridden by series 'example'
                        "series": {"example": {"entitled": True}},
                    }
                },
            ),
        ),
    )
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=system.ReleaseInfo(
            distribution="", release="", series="example", pretty_version=""
        ),
    )
    def test_process_contract_deltas_does_nothing_when_delta_remains_entitled(
        self, m_platform_info, base_entitlement_factory, orig_access, delta
    ):
        """If deltas do not represent transition to unentitled, do nothing."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
            },
        )
        entitlement.process_contract_deltas(orig_access, delta)
        assert (
            ApplicationStatus.DISABLED,
            mock.ANY,
        ) == entitlement.application_status()

    @pytest.mark.parametrize(
        "orig_access,delta",
        (
            (
                {
                    "entitlement": {"entitled": True}
                },  # Full entitlement dropped
                {"entitlement": {"entitled": util.DROPPED_KEY}},
            ),
            (
                {"entitlement": {"entitled": True}},
                {"entitlement": {"entitled": False}},
            ),  # transition to unentitled
        ),
    )
    def test_process_contract_deltas_clean_cache_on_inactive_unentitled(
        self, base_entitlement_factory, orig_access, delta, caplog_text
    ):
        """Only clear cache when deltas transition inactive to unentitled."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.DISABLED, ""),
            },
        )
        entitlement.process_contract_deltas(orig_access, delta)
        # If an entitlement is disabled, we don't need to tell the user
        # anything about it becoming unentitled
        # (FIXME: Something on bionic means that DEBUG log lines are being
        # picked up by caplog_text(), so work around that here)
        assert [] == [
            line for line in caplog_text().splitlines() if "DEBUG" not in line
        ]

    @pytest.mark.parametrize(
        "orig_access,delta",
        (
            (
                {
                    "entitlement": {"entitled": True}
                },  # Full entitlement dropped
                {"entitlement": {"entitled": util.DROPPED_KEY}},
            ),
            (
                {"entitlement": {"entitled": True}},
                {"entitlement": {"entitled": False}},
            ),  # transition to unentitled
        ),
    )
    def test_process_contract_deltas_disable_on_active_unentitled(
        self, base_entitlement_factory, orig_access, delta
    ):
        """Disable when deltas transition from active to unentitled."""
        entitlement = base_entitlement_factory(
            entitled=True,
            extra_args={
                "application_status": (ApplicationStatus.ENABLED, ""),
            },
        )

        with mock.patch.object(
            entitlement, "can_disable", return_value=(True, None)
        ):
            entitlement.process_contract_deltas(orig_access, delta)

        assert (
            ApplicationStatus.DISABLED,
            mock.ANY,
        ) == entitlement.application_status()


class TestEntitlementCfg:
    @pytest.mark.parametrize(
        "variant_name", ((""), ("test-variant"), ("invalid-variant"))
    )
    def test_entitlement_cfg_respects_variant(
        self, variant_name, base_entitlement_factory
    ):
        entitlement = base_entitlement_factory(
            entitled=True,
            obligations={"enableByDefault": False},
            affordances={
                "architectures": [
                    "amd64",
                    "ppc64el",
                ],
                "series": ["xenial", "bionic", "focal"],
            },
            directives={
                "additionalPackages": ["test-package"],
                "suites": ["xenial", "bionic", "focal"],
            },
            overrides=[
                {
                    "directives": {
                        "additionalPackages": ["test-package-variant"]
                    },
                    "selector": {
                        "variant": "test-variant",
                    },
                },
                {
                    "directives": {
                        "additionalPackages": ["test-package-unused"]
                    },
                    "selector": {"cloud": "aws", "series": "focal"},
                },
            ],
            extra_args={
                "applicability_status": (ApplicabilityStatus.APPLICABLE, ""),
                "application_status": (ApplicationStatus.DISABLED, ""),
                "variant_name": variant_name,
            },
        )
        expected_entitlement = copy.deepcopy(
            entitlement._base_entitlement_cfg()
        )
        if variant_name == "test-variant":
            expected_entitlement["entitlement"]["directives"][
                "additionalPackages"
            ] = ["test-package-variant"]

        assert expected_entitlement == entitlement.entitlement_cfg


class TestVariant:
    @pytest.mark.parametrize(
        "contract_variants",
        (
            ([]),
            (["not-found-variant"]),
            (["test_variant"]),
            (["test_variant", "test_variant2"]),
        ),
    )
    @mock.patch("uaclient.entitlements.base.UAEntitlement._get_variants")
    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement._get_contract_variants"
    )
    def test_variant_property(
        self,
        m_get_contract_variants,
        m_get_variants,
        contract_variants,
        base_entitlement_factory,
    ):
        entitlement = base_entitlement_factory()
        service_variants = {"test_variant": "test", "generic": "generic"}
        m_get_contract_variants.return_value = contract_variants
        m_get_variants.return_value = service_variants
        actual_variants = entitlement.variants

        expected_variants = (
            {} if "test_variant" not in contract_variants else service_variants
        )
        assert expected_variants == actual_variants
        assert 1 == m_get_contract_variants.call_count
        assert 1 == m_get_variants.call_count


class TestGetContractVariant:
    @pytest.mark.parametrize(
        "overrides",
        (
            ([]),
            (
                [
                    {
                        "selector": {
                            "variant": "test1",
                        },
                    },
                    {
                        "selector": {
                            "variant": "test2",
                        }
                    },
                    {
                        "selector": {
                            "cloud": "cloud",
                        },
                    },
                ]
            ),
        ),
    )
    def test_get_contract_variant(self, overrides, base_entitlement_factory):
        entitlement = base_entitlement_factory(overrides=overrides)
        actual_contract_variants = entitlement._get_contract_variants()
        expected_contract_variants = (
            set() if not overrides else set(["test1", "test2"])
        )

        assert expected_contract_variants == actual_contract_variants


class TestHandleRequiredSnaps:
    @pytest.mark.parametrize(
        "directives",
        (
            ({}),
            (
                {
                    "requiredSnaps": [
                        {"name": "test1", "channel": "latest/stable"},
                        {
                            "name": "test2",
                            "classicConfinementSupport": True,
                        },
                        {"name": "test3"},
                    ]
                }
            ),
        ),
    )
    @mock.patch(
        "uaclient.snap.is_snapd_installed_as_a_snap", return_value=True
    )
    @mock.patch("uaclient.snap.is_snapd_installed", return_value=True)
    @mock.patch("uaclient.snap.run_snapd_wait_cmd")
    @mock.patch("uaclient.snap.get_snap_info")
    @mock.patch("uaclient.snap.install_snap")
    @mock.patch("uaclient.http.validate_proxy")
    @mock.patch("uaclient.snap.configure_snap_proxy")
    def test_handle_required_snaps(
        self,
        m_configure_snap_proxy,
        m_validate_proxy,
        m_install_snap,
        m_get_snap_info,
        m_run_snapd_wait_cmd,
        m_is_snapd_installed,
        m_is_snapd_installed_as_a_snap,
        directives,
        base_entitlement_factory,
    ):
        entitlement = base_entitlement_factory(directives=directives)
        m_get_snap_info.side_effect = [
            exceptions.SnapNotInstalledError(snap="snap"),
            exceptions.SnapNotInstalledError(snap="snap"),
            mock.MagicMock,
        ]

        assert entitlement.handle_required_snaps(mock.MagicMock())

        if not directives:
            assert 0 == m_is_snapd_installed.call_count
            assert 0 == m_is_snapd_installed_as_a_snap.call_count
            assert 0 == m_run_snapd_wait_cmd.call_count
            assert 0 == m_validate_proxy.call_count
            assert 0 == m_configure_snap_proxy.call_count
        else:
            assert 1 == m_is_snapd_installed.call_count
            assert 1 == m_is_snapd_installed_as_a_snap.call_count
            assert 1 == m_run_snapd_wait_cmd.call_count
            assert 2 == m_validate_proxy.call_count
            assert 1 == m_configure_snap_proxy.call_count
            assert [
                mock.call(
                    "test1",
                    channel="latest/stable",
                    classic_confinement_support=False,
                ),
                mock.call(
                    "test2", channel=None, classic_confinement_support=True
                ),
            ] == m_install_snap.call_args_list


class TestHandleRequiredPackages:
    @pytest.mark.parametrize(
        [
            "required_packages_directive",
            "expected_apt_update_calls",
            "expected_apt_install_calls",
            "expected_result",
        ],
        [
            (
                None,
                [],
                [],
                True,
            ),
            (
                [],
                [],
                [],
                True,
            ),
            (
                [{"name": "package"}],
                [mock.call("/etc/apt/sources.list")],
                [mock.call(["package"])],
                True,
            ),
            (
                [{"name": "package"}, {"name": "package2"}],
                [mock.call("/etc/apt/sources.list")],
                [mock.call(["package", "package2"])],
                True,
            ),
        ],
    )
    @mock.patch(
        "uaclient.apt.get_system_sources_file",
        return_value="/etc/apt/sources.list",
    )
    @mock.patch("uaclient.apt.update_sources_list")
    @mock.patch("uaclient.apt.run_apt_install_command")
    @mock.patch("uaclient.apt.run_apt_update_command")
    def test_handle_required_packages(
        self,
        m_apt_update,
        m_apt_install,
        m_update_sources_list,
        m_get_system_sources_file,
        required_packages_directive,
        expected_apt_update_calls,
        expected_apt_install_calls,
        expected_result,
        base_entitlement_factory,
    ):
        entitlement = base_entitlement_factory(
            directives={"requiredPackages": required_packages_directive},
        )

        assert expected_result == entitlement.handle_required_packages(
            mock.MagicMock()
        )
        assert [] == m_apt_update.call_args_list
        assert (
            expected_apt_update_calls == m_update_sources_list.call_args_list
        )
        assert expected_apt_install_calls == m_apt_install.call_args_list

    @pytest.mark.parametrize(
        [
            "required_packages_directive",
            "expected_apt_remove_calls",
            "expected_result",
        ],
        [
            (
                None,
                [],
                True,
            ),
            (
                [],
                [],
                True,
            ),
            (
                [{"name": "package"}],
                [],
                True,
            ),
            (
                [{"name": "package"}, {"name": "package2"}],
                [],
                True,
            ),
            (
                [
                    {"name": "package"},
                    {"name": "package2", "removeOnDisable": True},
                ],
                [mock.call(["package2"], mock.ANY)],
                True,
            ),
            (
                [
                    {"name": "package"},
                    {"name": "package2", "removeOnDisable": True},
                    {"name": "package3", "removeOnDisable": False},
                    {"name": "package4", "removeOnDisable": True},
                ],
                [mock.call(["package2", "package4"], mock.ANY)],
                True,
            ),
        ],
    )
    @mock.patch("uaclient.apt.remove_packages")
    def test_handle_removing_required_packages(
        self,
        m_apt_remove,
        required_packages_directive,
        expected_apt_remove_calls,
        expected_result,
        base_entitlement_factory,
    ):
        entitlement = base_entitlement_factory(
            directives={"requiredPackages": required_packages_directive},
        )

        assert (
            expected_result == entitlement.handle_removing_required_packages()
        )
        assert expected_apt_remove_calls == m_apt_remove.call_args_list
