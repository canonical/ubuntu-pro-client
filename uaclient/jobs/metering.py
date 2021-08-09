"""
Functions to be used when running metering jobs
"""

from uaclient import config, exceptions
from uaclient.contract import UAContractClient
from uaclient.entitlements import ENTITLEMENT_CLASSES
from uaclient.status import UserFacingStatus


def metering_enabled_resources(cfg: config.UAConfig) -> None:
    # We only run this job if there is no other job running.
    # The reason for that is to avoid potential conflicts with
    # auto-attach, attach and enable operations.
    lock_pid, curr_lock_holder = cfg.check_lock_info()
    if lock_pid > 0:
        raise exceptions.LockHeldError(
            lock_request="metering job",
            lock_holder=curr_lock_holder,
            pid=lock_pid,
        )

    if not cfg.is_attached:
        return

    enabled_services = [
        ent(cfg).name
        for ent in ENTITLEMENT_CLASSES
        if ent(cfg).user_facing_status()[0] == UserFacingStatus.ACTIVE
    ]

    contract = UAContractClient(cfg)
    contract.report_machine_activity(enabled_services=enabled_services)
