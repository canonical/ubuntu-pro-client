import mock
import pytest

from uaclient import entitlements
from uaclient.api import exceptions
from uaclient.api.u.pro.services.enable.v1 import (
    EnableOptions,
    EnableResult,
    _auto_select_variant,
    _enable,
)
from uaclient.testing.helpers import does_not_raise, mock_with_name_attr

M_PATH = "uaclient.api.u.pro.services.enable.v1."


class TestEnable:
    @pytest.mark.parametrize(
        [
            "options",
            "we_are_currently_root",
            "is_attached",
            "enabled_services_before",
            "enabled_services_names_after",
            "enable_result",
            "messaging_ops",
            "reboot_required",
            "expected_raises",
            "expected_result",
        ],
        [
            # not root
            (
                EnableOptions(service="s1"),
                False,
                False,
                None,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.NonRootUserError),
                None,
            ),
            # not attached
            (
                EnableOptions(service="s1"),
                True,
                False,
                None,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.UnattachedError),
                None,
            ),
            # landscape fail
            (
                EnableOptions(service="landscape"),
                True,
                True,
                None,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.NotSupported),
                None,
            ),
            # generic enable failure
            (
                EnableOptions(service="s1"),
                True,
                True,
                [],
                None,
                (False, None),
                None,
                None,
                pytest.raises(exceptions.EntitlementNotEnabledError),
                None,
            ),
            # success
            (
                EnableOptions(service="s1"),
                True,
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
            # success already enabled no variant
            (
                EnableOptions(service="s1"),
                True,
                True,
                [
                    mock_with_name_attr(
                        name="s1", variant_enabled=False, variant_name=""
                    )
                ],
                None,
                None,
                None,
                None,
                does_not_raise(),
                EnableResult(
                    enabled=[],
                    disabled=[],
                    reboot_required=False,
                    messages=[],
                ),
            ),
            # success already enabled no variant specified but variant enabled
            (
                EnableOptions(service="s1"),
                True,
                True,
                [
                    mock_with_name_attr(
                        name="s1", variant_enabled=True, variant_name="v1"
                    )
                ],
                None,
                None,
                None,
                None,
                does_not_raise(),
                EnableResult(
                    enabled=[],
                    disabled=[],
                    reboot_required=False,
                    messages=[],
                ),
            ),
            # success already enabled variant specified same variant enabled
            (
                EnableOptions(service="s1", variant="v1"),
                True,
                True,
                [
                    mock_with_name_attr(
                        name="s1", variant_enabled=True, variant_name="v1"
                    )
                ],
                None,
                None,
                None,
                None,
                does_not_raise(),
                EnableResult(
                    enabled=[],
                    disabled=[],
                    reboot_required=False,
                    messages=[],
                ),
            ),
            # success with reboot required
            (
                EnableOptions(service="s1"),
                True,
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
            # success with reboot required and different variant
            (
                EnableOptions(service="s1", variant="v1"),
                True,
                True,
                [
                    mock_with_name_attr(
                        name="s1", variant_enabled=True, variant_name="v2"
                    )
                ],
                ["s1"],
                (True, None),
                {},
                True,
                does_not_raise(),
                EnableResult(
                    enabled=[],
                    disabled=[],
                    reboot_required=True,
                    messages=[],
                ),
            ),
            # success with post enable messages
            (
                EnableOptions(service="s1"),
                True,
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
            # success with additional enablements and disablements
            (
                EnableOptions(service="s1"),
                True,
                True,
                [
                    mock_with_name_attr(
                        name="s2", variant_enabled=False, variant_name=""
                    )
                ],
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
        ],
    )
    @mock.patch(M_PATH + "status.status")
    @mock.patch(M_PATH + "lock.clear_lock_file_if_present")
    @mock.patch(M_PATH + "lock.RetryLock")
    @mock.patch(M_PATH + "_auto_select_variant")
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "_enabled_services_names")
    @mock.patch(M_PATH + "_enabled_services")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "util.we_are_currently_root")
    def test_enable(
        self,
        m_we_are_currently_root,
        m_is_attached,
        m_enabled_services,
        m_enabled_services_names,
        m_entitlement_factory,
        m_auto_select_variant,
        m_spin_lock,
        _m_clear_lock_file_if_present,
        m_status,
        options,
        is_attached,
        we_are_currently_root,
        enabled_services_before,
        enabled_services_names_after,
        enable_result,
        messaging_ops,
        reboot_required,
        expected_raises,
        expected_result,
        FakeConfig,
    ):
        m_we_are_currently_root.return_value = we_are_currently_root
        m_is_attached.return_value = mock.MagicMock(is_attached=is_attached)
        m_enabled_services.return_value.enabled_services = (
            enabled_services_before
        )
        enabled_services_names_before = (
            [s.name for s in enabled_services_before]
            if enabled_services_before
            else enabled_services_before
        )
        m_enabled_services_names.side_effect = [
            enabled_services_names_before,
            enabled_services_names_after,
        ]
        m_ent = m_entitlement_factory.return_value
        m_auto_select_variant.return_value = (m_ent, None)
        m_ent.applicability_status.return_value = (
            entitlements.ApplicabilityStatus.APPLICABLE,
            None,
        )
        m_ent.enable.return_value = enable_result
        m_ent.messaging = messaging_ops
        m_ent._check_for_reboot.return_value = reboot_required

        cfg = FakeConfig()

        actual_result = None
        with expected_raises:
            actual_result = _enable(
                options, cfg, progress_object=mock.MagicMock()
            )

        assert actual_result == expected_result

        if expected_result is not None and len(expected_result.enabled) > 0:
            assert m_entitlement_factory.call_args_list == [
                mock.call(
                    cfg=cfg,
                    name=options.service,
                    variant=options.variant or "",
                    access_only=options.access_only,
                )
            ]
            assert m_ent.enable.call_args_list == [mock.call(mock.ANY)]

    @pytest.mark.parametrize(
        [
            "original_applicability_status",
            "original_is_variant",
            "original_variants",
            "auto_select_variant_return_value",
            "expected_original_enable_calls",
            "expected_variant_enable_calls",
        ],
        [
            # base entitlement not applicable
            (
                (entitlements.ApplicabilityStatus.INAPPLICABLE, None),
                True,
                {"variant": mock.MagicMock()},
                None,
                [mock.call(mock.ANY)],
                [],
            ),
            # not a variant
            (
                (entitlements.ApplicabilityStatus.APPLICABLE, None),
                False,
                {"variant": mock.MagicMock()},
                None,
                [mock.call(mock.ANY)],
                [],
            ),
            # is already a variant and therefore no variants
            (
                (entitlements.ApplicabilityStatus.APPLICABLE, None),
                True,
                {},
                None,
                [mock.call(mock.ANY)],
                [],
            ),
            # variants but nothing returned for some reason
            (
                (entitlements.ApplicabilityStatus.APPLICABLE, None),
                False,
                {"variant": mock.MagicMock()},
                None,
                [mock.call(mock.ANY)],
                [],
            ),
            # variant returned
            (
                (entitlements.ApplicabilityStatus.APPLICABLE, None),
                False,
                {"variant": mock.MagicMock()},
                (mock.MagicMock(), mock.MagicMock()),
                [],
                [mock.call(mock.ANY)],
            ),
        ],
    )
    @mock.patch(M_PATH + "status.status")
    @mock.patch(M_PATH + "lock.clear_lock_file_if_present")
    @mock.patch(M_PATH + "lock.RetryLock")
    @mock.patch(
        M_PATH + "_auto_select_variant",
    )
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "_enabled_services_names")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "util.we_are_currently_root")
    def test_enable_auto_selects_variant(
        self,
        m_we_are_currently_root,
        m_is_attached,
        m_enabled_services_names,
        m_entitlement_factory,
        m_auto_select_variant,
        m_spin_lock,
        _m_clear_lock_file_if_present,
        m_status,
        original_applicability_status,
        original_is_variant,
        original_variants,
        auto_select_variant_return_value,
        expected_original_enable_calls,
        expected_variant_enable_calls,
        FakeConfig,
    ):
        m_ent = m_entitlement_factory.return_value
        m_ent.applicability_status.return_value = original_applicability_status
        m_ent.enable.return_value = (True, None)
        m_ent.is_variant = original_is_variant
        m_ent.variants = original_variants
        if auto_select_variant_return_value is not None:
            auto_select_variant_return_value[0].enable.return_value = (
                True,
                None,
            )
            m_auto_select_variant.return_value = (
                auto_select_variant_return_value
            )
        else:
            m_auto_select_variant.return_value = (m_ent, None)

        result = _enable(
            mock.MagicMock(), FakeConfig(), progress_object=mock.MagicMock()
        )

        assert expected_original_enable_calls == m_ent.enable.call_args_list
        if auto_select_variant_return_value is not None:
            assert (
                expected_variant_enable_calls
                == auto_select_variant_return_value[0].enable.call_args_list
            )
            assert len(result.warnings) == 1


class TestAutoSelectVariant:
    @pytest.mark.parametrize(
        [
            "variant_applicability_statuses",
            "variant_auto_selects",
            "default_variant",
            "expected_result",
        ],
        [
            # no variants
            (
                [],
                [],
                None,
                "original",
            ),
            # one variant, not applicable
            (
                [entitlements.ApplicabilityStatus.INAPPLICABLE],
                [False],
                None,
                "original",
            ),
            # one variant, applicable, but not autoselected
            (
                [entitlements.ApplicabilityStatus.APPLICABLE],
                [False],
                None,
                "original",
            ),
            # one variant, applicable, but not autoselected, with default
            (
                [entitlements.ApplicabilityStatus.APPLICABLE],
                [False],
                mock.MagicMock(),
                "default",
            ),
            # two variants, applicable, one autoselected, with default
            (
                [
                    entitlements.ApplicabilityStatus.APPLICABLE,
                    entitlements.ApplicabilityStatus.APPLICABLE,
                ],
                [False, True],
                mock.MagicMock(),
                1,
            ),
            # three variants, applicable, one autoselected, with default
            (
                [
                    entitlements.ApplicabilityStatus.INAPPLICABLE,
                    entitlements.ApplicabilityStatus.APPLICABLE,
                    entitlements.ApplicabilityStatus.APPLICABLE,
                ],
                [False, False, True],
                mock.MagicMock(),
                2,
            ),
            # three variants, applicable, two autoselected, takes first one
            (
                [
                    entitlements.ApplicabilityStatus.INAPPLICABLE,
                    entitlements.ApplicabilityStatus.APPLICABLE,
                    entitlements.ApplicabilityStatus.APPLICABLE,
                ],
                [False, True, True],
                mock.MagicMock(),
                1,
            ),
        ],
    )
    def test_auto_select_variant(
        self,
        variant_applicability_statuses,
        variant_auto_selects,
        default_variant,
        expected_result,
        FakeConfig,
    ):
        original = mock.MagicMock(name="original")
        original.default_variant = default_variant
        variants = []
        for i in range(len(variant_auto_selects)):
            v = mock.MagicMock(name="variant" + str(i))
            v.return_value.applicability_status.return_value = (
                variant_applicability_statuses[i],
                None,
            )
            v.return_value.variant_auto_select.return_value = (
                variant_auto_selects[i]
            )
            variants.append(v)

        if expected_result == "original":
            expected = (original, None)
        elif expected_result == "default":
            expected = (default_variant.return_value, mock.ANY)
        else:
            expected = (variants[expected_result].return_value, mock.ANY)

        assert expected == _auto_select_variant(
            FakeConfig(),
            mock.MagicMock(),
            original,
            variants,
            False,
        )
