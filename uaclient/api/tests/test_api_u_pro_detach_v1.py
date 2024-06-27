import mock
import pytest

from uaclient import entitlements, exceptions, messages
from uaclient.api.data_types import ErrorWarningObject
from uaclient.api.u.pro.detach.v1 import DetachResult, _detach
from uaclient.entitlements.entitlement_status import (
    CanDisableFailure,
    CanDisableFailureReason,
)

M_PATH = "uaclient.api.u.pro.detach.v1."


@mock.patch("uaclient.lock.RetryLock.__enter__")
class TestDetachV1:
    @mock.patch(M_PATH + "_is_attached")
    def test_detach_when_unattached(self, m_is_attached, _m_lock_enter):
        m_is_attached.return_value = mock.MagicMock(is_attached=False)
        assert DetachResult(disabled=[], reboot_required=False) == _detach(
            mock.MagicMock()
        )

    @mock.patch("uaclient.util.we_are_currently_root")
    def test_detach_when_non_root(
        self, m_we_are_currently_root, _m_lock_enter
    ):
        m_we_are_currently_root.return_value = False
        with pytest.raises(exceptions.NonRootUserError):
            _detach(mock.MagicMock())

    @mock.patch("uaclient.timer.stop")
    @mock.patch("uaclient.daemon.start")
    @mock.patch("uaclient.files.state_files.delete_state_files")
    @mock.patch(M_PATH + "_reboot_required")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "update_motd_messages")
    def test_detach(
        self,
        m_update_motd_messages,
        m_is_attached,
        m_reboot_required,
        m_delete_state_files,
        m_daemon_start,
        m_timer_stop,
        _m_lock_enter,
        mock_entitlement,
        fake_machine_token_file,
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)
        m_reboot_required.return_value = mock.MagicMock(reboot_required="yes")

        _, m_ent1_obj = mock_entitlement(
            name="ent1",
            disable=(True, None),
            can_disable=(True, None),
        )

        _, m_ent2_obj = mock_entitlement(
            name="ent2",
            disable=(True, None),
            can_disable=(True, None),
        )

        _, m_ent3_obj = mock_entitlement(
            name="ent3",
            can_disable=(False, None),
        )

        _, m_ent4_obj = mock_entitlement(
            name="ent4",
            can_disable=(True, None),
            disable=(
                False,
                CanDisableFailure(
                    reason=CanDisableFailureReason.NOT_APPLICABLE,
                    message=messages.CANNOT_DISABLE_NOT_APPLICABLE.format(
                        title="ent4"
                    ),
                ),
            ),
        )

        _, m_ent5_obj = mock_entitlement(
            name="ent5",
            can_disable=(True, None),
            disable=(
                False,
                None,
            ),
        )

        def ent_factory_side_effect(cfg, name):
            if name == "ent1":
                return m_ent1_obj
            elif name == "ent2":
                return m_ent2_obj
            elif name == "ent3":
                return m_ent3_obj
            elif name == "ent4":
                return m_ent4_obj
            else:
                return m_ent5_obj

        with mock.patch.object(
            entitlements,
            "entitlements_disable_order",
            return_value=["ent2", "ent3", "ent5", "ent1", "ent4"],
        ):
            with mock.patch.object(
                entitlements, "entitlement_factory"
            ) as m_factory:
                m_factory.side_effect = ent_factory_side_effect
                m_cfg = mock.MagicMock()
                m_machine_token = mock.MagicMock()
                m_cfg.machine_token_file = m_machine_token

                actual_result = _detach(m_cfg)

        expected_warn_msg = messages.CANNOT_DISABLE_NOT_APPLICABLE.format(
            title="ent4"
        )
        expected_result = DetachResult(
            disabled=["ent1", "ent2"],
            reboot_required=True,
        )
        expected_result.warnings = (
            [
                ErrorWarningObject(
                    title=messages.DISABLE_FAILED_TMPL.format(title="ent5"),
                    code="",
                    meta={"service": "ent_5"},
                ),
                ErrorWarningObject(
                    title=expected_warn_msg.msg,
                    code=expected_warn_msg.name,
                    meta={"service": "ent_4"},
                ),
            ],
        )

        assert expected_result == actual_result
        assert 1 == m_daemon_start.call_count
        assert 1 == m_timer_stop.call_count
        assert 1 == m_delete_state_files.call_count
        assert 1 == fake_machine_token_file.delete_calls
