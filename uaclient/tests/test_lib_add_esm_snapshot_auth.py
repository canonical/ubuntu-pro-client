import mock
import pytest

from lib.add_esm_snapshot_auth import add_esm_snapshot_auth
from uaclient.entitlements.entitlement_status import ApplicationStatus


class TestAddEsmSnapshotAuth:
    @pytest.mark.parametrize(
        [
            "is_attached",
            "esm_infra_application_status",
            "esm_apps_application_status",
            "esm_infra_update_apt_auth_calls",
            "esm_apps_update_apt_auth_calls",
        ],
        [
            (False, None, None, [], []),
            (
                True,
                ApplicationStatus.DISABLED,
                ApplicationStatus.DISABLED,
                [],
                [],
            ),
            (
                True,
                ApplicationStatus.ENABLED,
                ApplicationStatus.WARNING,
                [mock.call()],
                [mock.call()],
            ),
            (
                True,
                ApplicationStatus.WARNING,
                ApplicationStatus.DISABLED,
                [mock.call()],
                [],
            ),
            (
                True,
                ApplicationStatus.DISABLED,
                ApplicationStatus.ENABLED,
                [],
                [mock.call()],
            ),
        ],
    )
    @mock.patch("lib.add_esm_snapshot_auth.ESMAppsEntitlement.update_apt_auth")
    @mock.patch(
        "lib.add_esm_snapshot_auth.ESMInfraEntitlement.update_apt_auth"
    )
    @mock.patch(
        "lib.add_esm_snapshot_auth.ESMAppsEntitlement.application_status"
    )
    @mock.patch(
        "lib.add_esm_snapshot_auth.ESMInfraEntitlement.application_status"
    )
    @mock.patch("lib.add_esm_snapshot_auth._is_attached")
    def test_add_esm_snapshot_auth(
        self,
        m_is_attached,
        m_esm_infra_application_status,
        m_esm_apps_application_status,
        m_esm_infra_update_apt_auth,
        m_esm_apps_update_apt_auth,
        is_attached,
        esm_infra_application_status,
        esm_apps_application_status,
        esm_infra_update_apt_auth_calls,
        esm_apps_update_apt_auth_calls,
        FakeConfig,
    ):
        m_is_attached.return_value.is_attached = is_attached
        m_esm_infra_application_status.return_value = (
            esm_infra_application_status,
            None,
        )
        m_esm_apps_application_status.return_value = (
            esm_apps_application_status,
            None,
        )
        add_esm_snapshot_auth(FakeConfig())
        assert (
            m_esm_infra_update_apt_auth.call_args_list
            == esm_infra_update_apt_auth_calls
        )
        assert (
            m_esm_apps_update_apt_auth.call_args_list
            == esm_apps_update_apt_auth_calls
        )
