"""
Functions to be used when running metering jobs
"""

from uaclient import config
from uaclient.cli import assert_lock_file
from uaclient.contract import UAContractClient
from uaclient.entitlements import ENTITLEMENT_CLASSES
from uaclient.status import UserFacingStatus


@assert_lock_file("timer metering job")
def metering_enabled_resources(cfg: config.UAConfig) -> bool:
    # We only run this job if there is no other job running.
    # The reason for that is to avoid potential conflicts with
    # auto-attach, attach and enable operations.

    if not cfg.is_attached:
        return False

    enabled_services = [
        ent(cfg).name
        for ent in ENTITLEMENT_CLASSES
        if ent(cfg).user_facing_status()[0] == UserFacingStatus.ACTIVE
    ]

    contract = UAContractClient(cfg)
    contract.report_machine_activity(enabled_services=enabled_services)
    return True
