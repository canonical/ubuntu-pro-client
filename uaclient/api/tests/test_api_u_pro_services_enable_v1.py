import mock
import pytest

from uaclient.api import exceptions
from uaclient.api.u.pro.services.enable.v1 import (
    EnableOptions,
    EnableResult,
    _enable,
)
from uaclient.testing.helpers import does_not_raise

M_PATH = "uaclient.api.u.pro.services.enable.v1."


class TestEnable:
    @pytest.mark.parametrize(
        [
            "options",
            "is_attached",
            "enabled_services_names_before",
            "enabled_services_names_after",
            "enable_result",
            "messaging_ops",
            "reboot_required",
            "expected_raises",
            "expected_result",
        ],
        [
            (
                EnableOptions(service="s1"),
                False,
                None,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.UnattachedError),
                None,
            ),
            (
                EnableOptions(service="s1"),
                True,
                [],
                None,
                (False, None),
                None,
                None,
                pytest.raises(exceptions.EntitlementNotEnabledError),
                None,
            ),
            (
                EnableOptions(service="s1"),
                True,
                [],
                ["s1"],
                (True, None),
                {},
                False,
                does_not_raise(),
                EnableResult(
                    enabled=["s1"],
                    disabled=[],
                    reboot_required=False,
                    messages=[],
                ),
            ),
            (
                EnableOptions(service="s1"),
                True,
                [],
                ["s1"],
                (True, None),
                {},
                True,
                does_not_raise(),
                EnableResult(
                    enabled=["s1"],
                    disabled=[],
                    reboot_required=True,
                    messages=[],
                ),
            ),
            (
                EnableOptions(service="s1"),
                True,
                [],
                ["s1"],
                (True, None),
                {"post_enable": ["one", "two", 3]},
                False,
                does_not_raise(),
                EnableResult(
                    enabled=["s1"],
                    disabled=[],
                    reboot_required=False,
                    messages=["one", "two"],
                ),
            ),
            (
                EnableOptions(service="s1"),
                True,
                ["s2"],
                ["s1", "s3"],
                (True, None),
                {},
                False,
                does_not_raise(),
                EnableResult(
                    enabled=["s1", "s3"],
                    disabled=["s2"],
                    reboot_required=False,
                    messages=[],
                ),
            ),
            (
                EnableOptions(
                    service="s1",
                    enable_required_services=False,
                    disable_incompatible_services=False,
                    access_only=True,
                ),
                True,
                [],
                ["s1"],
                (True, None),
                {},
                False,
                does_not_raise(),
                EnableResult(
                    enabled=["s1"],
                    disabled=[],
                    reboot_required=False,
                    messages=[],
                ),
            ),
        ],
    )
    @mock.patch(M_PATH + "lock.clear_lock_file_if_present")
    @mock.patch(M_PATH + "lock.SpinLock")
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "_enabled_services_names")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "event.set_event_mode")
    def test_enable(
        self,
        m_set_event_mode,
        m_is_attached,
        m_enabled_services_names,
        m_entitlement_factory,
        m_spin_lock,
        m_clear_lock_file_if_present,
        options,
        is_attached,
        enabled_services_names_before,
        enabled_services_names_after,
        enable_result,
        messaging_ops,
        reboot_required,
        expected_raises,
        expected_result,
        FakeConfig,
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=is_attached)
        m_enabled_services_names.side_effect = [
            enabled_services_names_before,
            enabled_services_names_after,
        ]
        m_ent_class = m_entitlement_factory.return_value
        m_ent = m_ent_class.return_value
        m_ent.enable.return_value = enable_result
        m_ent.messaging = messaging_ops
        m_ent._check_for_reboot.return_value = reboot_required

        cfg = FakeConfig()

        actual_result = None
        with expected_raises:
            actual_result = _enable(options, cfg)

        assert actual_result == expected_result

        if expected_result is not None:
            assert m_entitlement_factory.call_args_list == [
                mock.call(
                    cfg=cfg,
                    name=options.service,
                    variant=options.variant or "",
                )
            ]
            assert m_ent_class.call_args_list == [
                mock.call(
                    cfg,
                    assume_yes=True,
                    allow_beta=True,
                    called_name=options.service,
                    access_only=options.access_only,
                )
            ]
            assert m_ent.enable.call_args_list == [
                mock.call(
                    enable_required_services=options.enable_required_services,
                    disable_incompatible_services=options.disable_incompatible_services,  # noqa: E501
                    api=True,
                )
            ]
