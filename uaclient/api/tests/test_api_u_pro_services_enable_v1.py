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
            "we_are_currently_root",
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
            # success already enabled
            (
                EnableOptions(service="s1"),
                True,
                True,
                ["s1"],
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
        ],
    )
    @mock.patch(M_PATH + "status.status")
    @mock.patch(M_PATH + "lock.clear_lock_file_if_present")
    @mock.patch(M_PATH + "lock.RetryLock")
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "_enabled_services_names")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "util.we_are_currently_root")
    def test_enable(
        self,
        m_we_are_currently_root,
        m_is_attached,
        m_enabled_services_names,
        m_entitlement_factory,
        m_spin_lock,
        m_clear_lock_file_if_present,
        m_status,
        options,
        is_attached,
        we_are_currently_root,
        enabled_services_names_before,
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
            assert m_ent.enable.call_args_list == [mock.call(mock.ANY)]
