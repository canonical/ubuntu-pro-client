import mock
import pytest

from lib.add_esm_snapshot_auth import add_esm_snapshot_auth
from uaclient.entitlements.entitlement_status import ApplicationStatus

MOCK_ESM_INFRA_AUTH_UPDATE_CALL = mock.call(
    override_snapshot_urls=[
        "snapshot.infra-security.esm.ubuntu.com/infra/ubuntu/",
        "snapshot.infra-updates.esm.ubuntu.com/infra/ubuntu/",
    ]
)
MOCK_ESM_APPS_AUTH_UPDATE_CALL = mock.call(
    override_snapshot_urls=[
        "snapshot.apps-security.esm.ubuntu.com/apps/ubuntu/",
        "snapshot.apps-updates.esm.ubuntu.com/apps/ubuntu/",
    ]
)


class TestAddEsmSnapshotAuth:
    @pytest.mark.parametrize(
        [
            "is_attached",
            "esm_infra_application_status",
            "esm_apps_application_status",
            "esm_infra_apt_url",
            "esm_apps_apt_url",
            "esm_infra_update_apt_auth_calls",
            "esm_apps_update_apt_auth_calls",
        ],
        [
            (False, None, None, None, None, [], []),
            (
                True,
                ApplicationStatus.DISABLED,
                ApplicationStatus.DISABLED,
                None,
                None,
                [],
                [],
            ),
            (
                True,
                ApplicationStatus.ENABLED,
                ApplicationStatus.ENABLED,
                None,
                None,
                [],
                [],
            ),
            (
                True,
                ApplicationStatus.ENABLED,
                ApplicationStatus.ENABLED,
                "http://custom",
                "http://custom",
                [],
                [],
            ),
            (
                True,
                ApplicationStatus.ENABLED,
                ApplicationStatus.WARNING,
                "https://esm.ubuntu.com/infra",
                "https://esm.ubuntu.com/apps",
                [MOCK_ESM_INFRA_AUTH_UPDATE_CALL],
                [MOCK_ESM_APPS_AUTH_UPDATE_CALL],
            ),
            (
                True,
                ApplicationStatus.WARNING,
                ApplicationStatus.DISABLED,
                "https://esm.ubuntu.com/infra",
                "https://esm.ubuntu.com/apps",
                [MOCK_ESM_INFRA_AUTH_UPDATE_CALL],
                [],
            ),
            (
                True,
                ApplicationStatus.DISABLED,
                ApplicationStatus.ENABLED,
                "https://esm.ubuntu.com/infra",
                "https://esm.ubuntu.com/apps",
                [],
                [MOCK_ESM_APPS_AUTH_UPDATE_CALL],
            ),
        ],
    )
    @mock.patch("lib.add_esm_snapshot_auth.ESMAppsEntitlement.update_apt_auth")
    @mock.patch(
        "lib.add_esm_snapshot_auth.ESMInfraEntitlement.update_apt_auth"
    )
    @mock.patch(
        "lib.add_esm_snapshot_auth.ESMAppsEntitlement.apt_url",
        new_callable=mock.PropertyMock,
    )
    @mock.patch(
        "lib.add_esm_snapshot_auth.ESMInfraEntitlement.apt_url",
        new_callable=mock.PropertyMock,
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
        m_esm_infra_apt_url,
        m_esm_apps_apt_url,
        m_esm_infra_update_apt_auth,
        m_esm_apps_update_apt_auth,
        is_attached,
        esm_infra_application_status,
        esm_apps_application_status,
        esm_infra_apt_url,
        esm_apps_apt_url,
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
        m_esm_infra_apt_url.return_value = esm_infra_apt_url
        m_esm_apps_apt_url.return_value = esm_apps_apt_url
        add_esm_snapshot_auth(FakeConfig())
        assert (
            m_esm_infra_update_apt_auth.call_args_list
            == esm_infra_update_apt_auth_calls
        )
        assert (
            m_esm_apps_update_apt_auth.call_args_list
            == esm_apps_update_apt_auth_calls
        )
