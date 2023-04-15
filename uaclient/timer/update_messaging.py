"""
Update messaging text for use in MOTD and APT custom Ubuntu Pro messages.

Messaging files will be emitted to /var/lib/ubuntu-advantage/message-* which
will be sourced by apt-hook/hook.cc and various /etc/update-motd.d/ hooks to
present updated text about Ubuntu Pro service and token state.
"""

import enum
import logging
import os
from os.path import exists
from typing import Tuple

from uaclient import contract, defaults, messages, system
from uaclient.api.u.pro.packages.updates.v1 import (
    _updates as api_u_pro_packages_updates_v1,
)
from uaclient.config import UAConfig
from uaclient.entitlements import ESMAppsEntitlement, ESMInfraEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus

MOTD_CONTRACT_STATUS_FILE_NAME = "motd-contract-status"
UPDATE_NOTIFIER_MOTD_SCRIPT = (
    "/usr/lib/update-notifier/update-motd-updates-available"
)


@enum.unique
class ContractExpiryStatus(enum.Enum):
    NONE = 0
    ACTIVE = 1
    ACTIVE_EXPIRED_SOON = 2
    EXPIRED_GRACE_PERIOD = 3
    EXPIRED = 4


def update_contract_expiry(cfg: UAConfig):
    orig_token = cfg.machine_token
    machine_token = orig_token.get("machineToken", "")
    contract_id = (
        orig_token.get("machineTokenInfo", {})
        .get("contractInfo", {})
        .get("id", None)
    )
    contract_client = contract.UAContractClient(cfg)
    resp = contract_client.get_updated_contract_info(
        machine_token, contract_id
    )
    resp_expiry = (
        resp.get("machineTokenInfo", {})
        .get("contractInfo", {})
        .get("effectiveTo", None)
    )
    if (
        resp_expiry is not None
        and resp_expiry != cfg.machine_token_file.contract_expiry_datetime
    ):
        orig_token["machineTokenInfo"]["contractInfo"][
            "effectiveTo"
        ] = resp_expiry
        cfg.machine_token_file.write(orig_token)


def get_contract_expiry_status(
    cfg: UAConfig,
) -> Tuple[ContractExpiryStatus, int]:
    """Return a tuple [ContractExpiryStatus, num_days]"""
    if not cfg.is_attached:
        return ContractExpiryStatus.NONE, 0

    grace_period = defaults.CONTRACT_EXPIRY_GRACE_PERIOD_DAYS
    pending_expiry = defaults.CONTRACT_EXPIRY_PENDING_DAYS
    remaining_days = cfg.machine_token_file.contract_remaining_days

    # if unknown assume the worst
    if remaining_days is None:
        logging.warning(
            "contract effectiveTo date is null - assuming it is expired"
        )
        return ContractExpiryStatus.EXPIRED, -grace_period

    if 0 <= remaining_days <= pending_expiry:
        return ContractExpiryStatus.ACTIVE_EXPIRED_SOON, remaining_days
    elif -grace_period <= remaining_days < 0:
        return ContractExpiryStatus.EXPIRED_GRACE_PERIOD, remaining_days
    elif remaining_days < -grace_period:
        return ContractExpiryStatus.EXPIRED, remaining_days
    return ContractExpiryStatus.ACTIVE, remaining_days


def update_motd_messages(cfg: UAConfig) -> bool:
    """Emit human-readable status message used by motd.

    Used by /etc/update.motd.d/91-contract-ua-esm-status

    :param cfg: UAConfig instance for this environment.
    """
    if not cfg.is_attached:
        return False

    logging.debug("Updating Ubuntu Pro messages for MOTD.")
    motd_contract_status_msg_path = os.path.join(
        cfg.data_dir, "messages", MOTD_CONTRACT_STATUS_FILE_NAME
    )

    expiry_status, remaining_days = get_contract_expiry_status(cfg)
    if expiry_status in (
        ContractExpiryStatus.ACTIVE_EXPIRED_SOON,
        ContractExpiryStatus.EXPIRED_GRACE_PERIOD,
        ContractExpiryStatus.EXPIRED,
    ):
        update_contract_expiry(cfg)
        expiry_status, remaining_days = get_contract_expiry_status(cfg)

    if expiry_status in (
        ContractExpiryStatus.ACTIVE,
        ContractExpiryStatus.NONE,
    ):
        system.ensure_file_absent(motd_contract_status_msg_path)
    elif expiry_status == ContractExpiryStatus.ACTIVE_EXPIRED_SOON:
        system.write_file(
            motd_contract_status_msg_path,
            messages.CONTRACT_EXPIRES_SOON_MOTD.format(
                remaining_days=remaining_days,
            ),
        )
    elif expiry_status == ContractExpiryStatus.EXPIRED_GRACE_PERIOD:
        grace_period_remaining = (
            defaults.CONTRACT_EXPIRY_GRACE_PERIOD_DAYS + remaining_days
        )
        exp_dt = cfg.machine_token_file.contract_expiry_datetime
        if exp_dt is None:
            exp_dt_str = "Unknown"
        else:
            exp_dt_str = exp_dt.strftime("%d %b %Y")
        system.write_file(
            motd_contract_status_msg_path,
            messages.CONTRACT_EXPIRED_GRACE_PERIOD_MOTD.format(
                expired_date=exp_dt_str,
                remaining_days=grace_period_remaining,
            ),
        )
    elif expiry_status == ContractExpiryStatus.EXPIRED:
        service = "n/a"
        pkg_num = 0

        if system.is_current_series_active_esm():
            esm_infra_status, _ = ESMInfraEntitlement(cfg).application_status()
            if esm_infra_status == ApplicationStatus.ENABLED:
                service = "esm-infra"
                pkg_num = api_u_pro_packages_updates_v1(
                    cfg
                ).summary.num_esm_infra_updates
        elif system.is_current_series_lts():
            esm_apps_status, _ = ESMAppsEntitlement(cfg).application_status()
            if esm_apps_status == ApplicationStatus.ENABLED:
                service = "esm-apps"
                pkg_num = api_u_pro_packages_updates_v1(
                    cfg
                ).summary.num_esm_apps_updates

        if pkg_num == 0:
            system.write_file(
                motd_contract_status_msg_path,
                messages.CONTRACT_EXPIRED_MOTD_NO_PKGS,
            )
        else:
            system.write_file(
                motd_contract_status_msg_path,
                messages.CONTRACT_EXPIRED_MOTD_PKGS.format(
                    pkg_num=pkg_num,
                    service=service,
                ),
            )

    return True


def refresh_motd():
    # If update-notifier is present, we might as well update
    # the package updates count related to MOTD
    if exists(UPDATE_NOTIFIER_MOTD_SCRIPT):
        # If this command fails, we shouldn't break the entire command,
        # since this command should already be triggered by
        # update-notifier apt hooks
        try:
            system.subp([UPDATE_NOTIFIER_MOTD_SCRIPT, "--force"])
        except Exception as exc:
            logging.exception(exc)
