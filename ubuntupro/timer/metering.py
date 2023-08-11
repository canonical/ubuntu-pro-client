"""
Functions to be used when running metering jobs
"""

from ubuntupro import config
from ubuntupro.api.u.pro.status.is_attached.v1 import _is_attached
from ubuntupro.cli import assert_lock_file
from ubuntupro.contract import UAContractClient


@assert_lock_file("timer metering job")
def metering_enabled_resources(cfg: config.UAConfig) -> bool:
    # We only run this job if there is no other job running.
    # The reason for that is to avoid potential conflicts with
    # auto-attach, attach and enable operations.

    if not _is_attached(cfg).is_attached:
        return False

    contract = UAContractClient(cfg)
    contract.update_activity_token()

    return True
