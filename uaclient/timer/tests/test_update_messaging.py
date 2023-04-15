import datetime

import mock
import pytest

from uaclient import messages
from uaclient.api.u.pro.packages.updates.v1 import (
    PackageUpdatesResult,
    UpdateSummary,
)
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.timer.update_messaging import (
    ContractExpiryStatus,
    get_contract_expiry_status,
    update_motd_messages,
)

M_PATH = "uaclient.timer.update_messaging."


class TestGetContractExpiryStatus:
    @pytest.mark.parametrize(
        "contract_remaining_days,expected_status",
        (
            (21, ContractExpiryStatus.ACTIVE),
            (20, ContractExpiryStatus.ACTIVE_EXPIRED_SOON),
            (-1, ContractExpiryStatus.EXPIRED_GRACE_PERIOD),
            (-20, ContractExpiryStatus.EXPIRED),
        ),
    )
    def test_contract_expiry_status_based_on_remaining_days(
        self, contract_remaining_days, expected_status, FakeConfig
    ):
        """Return a tuple of ContractExpiryStatus and remaining_days"""
        now = datetime.datetime.utcnow()
        expire_date = now + datetime.timedelta(days=contract_remaining_days)
        cfg = FakeConfig.for_attached_machine()
        m_token = cfg.machine_token
        m_token["machineTokenInfo"]["contractInfo"][
            "effectiveTo"
        ] = expire_date

        assert (
            expected_status,
            contract_remaining_days,
        ) == get_contract_expiry_status(cfg)

    @pytest.mark.parametrize(
        "expiry,is_updated",
        (("2040-05-08T19:02:26Z", False), ("2042-05-08T19:02:26Z", True)),
    )
    @mock.patch("uaclient.files.MachineTokenFile.write")
    @mock.patch(M_PATH + "contract.UAContractClient.get_updated_contract_info")
    def test_update_contract_expiry(
        self,
        get_updated_contract_info,
        machine_token_write,
        expiry,
        is_updated,
    ):
        get_updated_contract_info.return_value = {
            "machineTokenInfo": {"contractInfo": {"effectiveTo": expiry}}
        }
        if is_updated:
            1 == machine_token_write.call_count
        else:
            0 == machine_token_write.call_count


class TestUpdateMotdMessages:
    @pytest.mark.parametrize(
        [
            "attached",
            "contract_expiry_statuses",
            "is_current_series_active_esm",
            "infra_status",
            "is_current_series_lts",
            "apps_status",
            "updates",
            "expected",
            "update_contract_expiry_calls",
            "ensure_file_absent_calls",
            "write_file_calls",
        ],
        [
            (
                # not attached
                False,
                [],
                False,
                None,
                False,
                None,
                None,
                False,
                [],
                [],
                [],
            ),
            (
                # somehow attached but none contract status
                True,
                [(ContractExpiryStatus.NONE, None)],
                False,
                None,
                False,
                None,
                None,
                True,
                [],
                [mock.call(mock.ANY)],
                [],
            ),
            (
                # active contract
                True,
                [(ContractExpiryStatus.ACTIVE, None)],
                False,
                None,
                False,
                None,
                None,
                True,
                [],
                [mock.call(mock.ANY)],
                [],
            ),
            (
                # expiring soon contract, updated to be active
                True,
                [
                    (ContractExpiryStatus.ACTIVE_EXPIRED_SOON, None),
                    (ContractExpiryStatus.ACTIVE, None),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [mock.call(mock.ANY)],
                [],
            ),
            (
                # expired grace period contract, updated to be active
                True,
                [
                    (ContractExpiryStatus.EXPIRED_GRACE_PERIOD, None),
                    (ContractExpiryStatus.ACTIVE, None),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [mock.call(mock.ANY)],
                [],
            ),
            (
                # expired contract, updated to be active
                True,
                [
                    (ContractExpiryStatus.EXPIRED, None),
                    (ContractExpiryStatus.ACTIVE, None),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [mock.call(mock.ANY)],
                [],
            ),
            (
                # expiring soon for real
                True,
                [
                    (ContractExpiryStatus.ACTIVE_EXPIRED_SOON, 3),
                    (ContractExpiryStatus.ACTIVE_EXPIRED_SOON, 3),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [
                    mock.call(
                        mock.ANY,
                        messages.CONTRACT_EXPIRES_SOON_MOTD.format(
                            remaining_days=3
                        ),
                    )
                ],
            ),
            (
                # expired grace period for real
                True,
                [
                    (ContractExpiryStatus.EXPIRED_GRACE_PERIOD, -3),
                    (ContractExpiryStatus.EXPIRED_GRACE_PERIOD, -3),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [
                    mock.call(
                        mock.ANY,
                        messages.CONTRACT_EXPIRED_GRACE_PERIOD_MOTD.format(
                            remaining_days=11, expired_date="21 Dec 2012"
                        ),
                    )
                ],
            ),
            (
                # expired, eol release, esm-infra not enabled
                True,
                [
                    (ContractExpiryStatus.EXPIRED, 3),
                    (ContractExpiryStatus.EXPIRED, 3),
                ],
                True,
                (ApplicationStatus.DISABLED, None),
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY, messages.CONTRACT_EXPIRED_MOTD_NO_PKGS)],
            ),
            (
                # expired, lts release, esm-apps not enabled
                True,
                [
                    (ContractExpiryStatus.EXPIRED, 3),
                    (ContractExpiryStatus.EXPIRED, 3),
                ],
                False,
                None,
                True,
                (ApplicationStatus.DISABLED, None),
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY, messages.CONTRACT_EXPIRED_MOTD_NO_PKGS)],
            ),
            (
                # expired, interim release
                True,
                [
                    (ContractExpiryStatus.EXPIRED, 3),
                    (ContractExpiryStatus.EXPIRED, 3),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY, messages.CONTRACT_EXPIRED_MOTD_NO_PKGS)],
            ),
            (
                # expired, eol release, esm-infra enabled
                True,
                [
                    (ContractExpiryStatus.EXPIRED, 3),
                    (ContractExpiryStatus.EXPIRED, 3),
                ],
                True,
                (ApplicationStatus.ENABLED, None),
                False,
                None,
                PackageUpdatesResult(UpdateSummary(0, 0, 4, 0, 0), []),
                True,
                [mock.call(mock.ANY)],
                [],
                [
                    mock.call(
                        mock.ANY,
                        messages.CONTRACT_EXPIRED_MOTD_PKGS.format(
                            service="esm-infra", pkg_num=4
                        ),
                    )
                ],
            ),
            (
                # expired, lts release, esm-apps enabled
                True,
                [
                    (ContractExpiryStatus.EXPIRED, 3),
                    (ContractExpiryStatus.EXPIRED, 3),
                ],
                False,
                None,
                True,
                (ApplicationStatus.ENABLED, None),
                PackageUpdatesResult(UpdateSummary(0, 5, 0, 0, 0), []),
                True,
                [mock.call(mock.ANY)],
                [],
                [
                    mock.call(
                        mock.ANY,
                        messages.CONTRACT_EXPIRED_MOTD_PKGS.format(
                            service="esm-apps", pkg_num=5
                        ),
                    )
                ],
            ),
        ],
    )
    @mock.patch(M_PATH + "api_u_pro_packages_updates_v1")
    @mock.patch(M_PATH + "ESMAppsEntitlement.application_status")
    @mock.patch(M_PATH + "system.is_current_series_lts")
    @mock.patch(M_PATH + "ESMInfraEntitlement.application_status")
    @mock.patch(M_PATH + "system.is_current_series_active_esm")
    @mock.patch(
        M_PATH + "UAConfig.machine_token_file", new_callable=mock.PropertyMock
    )
    @mock.patch(M_PATH + "system.write_file")
    @mock.patch(M_PATH + "system.ensure_file_absent")
    @mock.patch(M_PATH + "update_contract_expiry")
    @mock.patch(M_PATH + "get_contract_expiry_status")
    @mock.patch(
        M_PATH + "UAConfig.is_attached", new_callable=mock.PropertyMock
    )
    def test_update_motd_messages(
        self,
        m_is_attached,
        m_get_contract_expiry_status,
        m_update_contract_expiry,
        m_ensure_file_absent,
        m_write_file,
        m_machine_token_file,
        m_is_current_series_active_esm,
        m_infra_status,
        m_is_current_series_lts,
        m_apps_status,
        m_api_updates_v1,
        attached,
        contract_expiry_statuses,
        is_current_series_active_esm,
        infra_status,
        is_current_series_lts,
        apps_status,
        updates,
        expected,
        update_contract_expiry_calls,
        ensure_file_absent_calls,
        write_file_calls,
        FakeConfig,
    ):
        m_is_attached.return_value = attached
        m_get_contract_expiry_status.side_effect = contract_expiry_statuses
        m_is_current_series_active_esm.return_value = (
            is_current_series_active_esm
        )
        m_infra_status.return_value = infra_status
        m_is_current_series_lts.return_value = is_current_series_lts
        m_apps_status.return_value = apps_status
        m_api_updates_v1.return_value = updates

        machine_token_file = mock.MagicMock()
        machine_token_file.contract_expiry_datetime = datetime.datetime(
            2012, 12, 21
        )
        m_machine_token_file.return_value = machine_token_file

        assert expected == update_motd_messages(FakeConfig())

        assert (
            update_contract_expiry_calls
            == m_update_contract_expiry.call_args_list
        )
        assert ensure_file_absent_calls == m_ensure_file_absent.call_args_list
        assert write_file_calls == m_write_file.call_args_list
