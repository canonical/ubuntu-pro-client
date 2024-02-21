import datetime

import mock
import pytest

from uaclient import messages
from uaclient.api.u.pro.packages.updates.v1 import (
    PackageUpdatesResult,
    UpdateSummary,
)
from uaclient.api.u.pro.status.is_attached.v1 import ContractExpiryStatus
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.timer.update_messaging import (
    update_contract_expiry,
    update_motd_messages,
)

M_PATH = "uaclient.timer.update_messaging."


class TestGetContractExpiryStatus:
    @pytest.mark.parametrize(
        "expiry,is_updated",
        (
            (
                datetime.datetime(
                    2040,
                    5,
                    8,
                    19,
                    2,
                    26,
                    tzinfo=datetime.timezone.utc,
                ),
                False,
            ),
            (
                datetime.datetime(
                    2042,
                    5,
                    8,
                    19,
                    2,
                    26,
                    tzinfo=datetime.timezone.utc,
                ),
                True,
            ),
        ),
    )
    @mock.patch("uaclient.files.MachineTokenFile.write")
    @mock.patch(M_PATH + "contract.UAContractClient.get_contract_machine")
    def test_update_contract_expiry(
        self,
        m_get_contract_machine,
        m_machine_token_write,
        expiry,
        is_updated,
        FakeConfig,
    ):
        m_get_contract_machine.return_value = {
            "machineTokenInfo": {"contractInfo": {"effectiveTo": expiry}}
        }
        cfg = FakeConfig.for_attached_machine()
        update_contract_expiry(cfg)
        if is_updated:
            assert 1 == m_machine_token_write.call_count
        else:
            assert 0 == m_machine_token_write.call_count


class TestUpdateMotdMessages:
    @pytest.mark.parametrize(
        [
            "is_attached_side_effect",
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
                [
                    mock.MagicMock(
                        is_attached=False,
                        contract_status=None,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=False,
                    )
                ],
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
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.NONE.value,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=False,
                    )
                ],
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
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE.value,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    )
                ],
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
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE_EXPIRED_SOON.value,  # noqa
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE.value,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    ),
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
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED_GRACE_PERIOD.value,  # noqa
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE.value,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    ),
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
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE.value,
                        contract_remaining_days=0,
                        is_attached_and_contract_valid=True,
                    ),
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
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE_EXPIRED_SOON.value,  # noqa
                        contract_remaining_days=3,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.ACTIVE_EXPIRED_SOON.value,  # noqa
                        contract_remaining_days=3,
                        is_attached_and_contract_valid=True,
                    ),
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
                        messages.CONTRACT_EXPIRES_SOON.pluralize(3).format(
                            remaining_days=3
                        )
                        + "\n\n",
                    )
                ],
            ),
            (
                # expired grace period for real
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED_GRACE_PERIOD.value,  # noqa
                        contract_remaining_days=-3,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED_GRACE_PERIOD.value,  # noqa
                        contract_remaining_days=-3,
                        is_attached_and_contract_valid=True,
                    ),
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
                        messages.CONTRACT_EXPIRED_GRACE_PERIOD.pluralize(
                            11
                        ).format(remaining_days=11, expired_date="21 Dec 2012")
                        + "\n\n",
                    )
                ],
            ),
            (
                # expired, eol release, esm-infra not enabled
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                ],
                True,
                (ApplicationStatus.DISABLED, None),
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY, messages.CONTRACT_EXPIRED + "\n\n")],
            ),
            (
                # expired, lts release, esm-apps not enabled
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                ],
                False,
                None,
                True,
                (ApplicationStatus.DISABLED, None),
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY, messages.CONTRACT_EXPIRED + "\n\n")],
            ),
            (
                # expired, interim release
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                ],
                False,
                None,
                False,
                None,
                None,
                True,
                [mock.call(mock.ANY)],
                [],
                [mock.call(mock.ANY, messages.CONTRACT_EXPIRED + "\n\n")],
            ),
            (
                # expired, eol release, esm-infra enabled
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
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
                        messages.CONTRACT_EXPIRED_WITH_PKGS.pluralize(
                            4
                        ).format(service="esm-infra", pkg_num=4)
                        + "\n\n",
                    )
                ],
            ),
            (
                # expired, lts release, esm-apps enabled
                [
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
                    mock.MagicMock(
                        is_attached=True,
                        contract_status=ContractExpiryStatus.EXPIRED.value,
                        contract_remaining_days=-30,
                        is_attached_and_contract_valid=True,
                    ),
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
                        messages.CONTRACT_EXPIRED_WITH_PKGS.pluralize(
                            5
                        ).format(service="esm-apps", pkg_num=5)
                        + "\n\n",
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
    @mock.patch(M_PATH + "_is_attached")
    def test_update_motd_messages(
        self,
        m_is_attached,
        m_update_contract_expiry,
        m_ensure_file_absent,
        m_write_file,
        m_machine_token_file,
        m_is_current_series_active_esm,
        m_infra_status,
        m_is_current_series_lts,
        m_apps_status,
        m_api_updates_v1,
        is_attached_side_effect,
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

        m_is_attached.side_effect = is_attached_side_effect
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
