import mock
import pytest

from uaclient.api import exceptions
from uaclient.api.u.pro.services.disable.v1 import (
    DisableOptions,
    DisableResult,
    _disable,
)
from uaclient.testing.helpers import does_not_raise

M_PATH = "uaclient.api.u.pro.services.disable.v1."


class TestDisable:
    @pytest.mark.parametrize(
        [
            "series",
            "options",
            "we_are_currently_root",
            "is_attached",
            "enabled_services_names_before",
            "enabled_services_names_after",
            "disable_result",
            "expected_service",
            "expected_raises",
            "expected_result",
        ],
        [
            # not root
            (
                "any_series",
                DisableOptions(service="s1"),
                False,
                False,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.NonRootUserError),
                None,
            ),
            # not attached
            (
                "any_series",
                DisableOptions(service="s1"),
                True,
                False,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.UnattachedError),
                None,
            ),
            # generic disable failure
            (
                "any_series",
                DisableOptions(service="s1"),
                True,
                True,
                ["s1"],
                None,
                (False, None),
                "s1",
                pytest.raises(exceptions.EntitlementNotDisabledError),
                None,
            ),
            # success
            (
                "any_series",
                DisableOptions(service="s1"),
                True,
                True,
                ["s1"],
                [],
                (True, None),
                "s1",
                does_not_raise(),
                DisableResult(
                    disabled=["s1"],
                ),
            ),
            # cis on focal
            (
                "focal",
                DisableOptions(service="cis"),
                True,
                True,
                ["usg"],
                [],
                (True, None),
                "usg",
                does_not_raise(),
                DisableResult(
                    disabled=["usg"],
                ),
            ),
            # success already disabled
            (
                "any_series",
                DisableOptions(service="s1"),
                True,
                True,
                [],
                None,
                None,
                "s1",
                does_not_raise(),
                DisableResult(
                    disabled=[],
                ),
            ),
            # success with additional disablements
            (
                "any_series",
                DisableOptions(service="s1"),
                True,
                True,
                ["s1", "s2", "s3"],
                ["s2"],
                (True, None),
                "s1",
                does_not_raise(),
                DisableResult(
                    disabled=["s1", "s3"],
                ),
            ),
        ],
    )
    @mock.patch(M_PATH + "status.status")
    @mock.patch(M_PATH + "lock.clear_lock_file_if_present")
    @mock.patch(M_PATH + "lock.RetryLock")
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "_enabled_services_names")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "util.we_are_currently_root")
    @mock.patch(M_PATH + "system.get_release_info")
    def test_disable(
        self,
        m_get_release_info,
        m_we_are_currently_root,
        m_is_attached,
        m_enabled_services_names,
        m_entitlement_factory,
        m_spin_lock,
        m_clear_lock_file_if_present,
        m_status,
        series,
        options,
        we_are_currently_root,
        is_attached,
        enabled_services_names_before,
        enabled_services_names_after,
        disable_result,
        expected_service,
        expected_raises,
        expected_result,
        FakeConfig,
    ):
        m_get_release_info.return_value.series = series
        m_we_are_currently_root.return_value = we_are_currently_root
        m_is_attached.return_value = mock.MagicMock(is_attached=is_attached)
        m_enabled_services_names.side_effect = [
            enabled_services_names_before,
            enabled_services_names_after,
        ]
        m_ent = m_entitlement_factory.return_value
        m_ent_variant = m_ent.enabled_variant
        m_ent_variant.disable.return_value = disable_result

        cfg = FakeConfig()

        actual_result = None
        with expected_raises:
            actual_result = _disable(
                options, cfg, progress_object=mock.MagicMock()
            )

        assert actual_result == expected_result

        if expected_result is not None and len(expected_result.disabled) > 0:
            assert m_entitlement_factory.call_args_list == [
                mock.call(
                    cfg=cfg,
                    name=expected_service,
                    purge=options.purge,
                )
            ]
            assert m_ent_variant.disable.call_args_list == [
                mock.call(mock.ANY)
            ]
