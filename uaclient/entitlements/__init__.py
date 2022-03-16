from typing import List, Type  # noqa: F401

from uaclient.config import UAConfig
from uaclient.entitlements import fips
from uaclient.entitlements.base import UAEntitlement  # noqa: F401
from uaclient.entitlements.cc import CommonCriteriaEntitlement
from uaclient.entitlements.cis import CISEntitlement
from uaclient.entitlements.esm import ESMAppsEntitlement, ESMInfraEntitlement
from uaclient.entitlements.livepatch import LivepatchEntitlement
from uaclient.entitlements.realtime import RealtimeKernelEntitlement
from uaclient.entitlements.ros import ROSEntitlement, ROSUpdatesEntitlement
from uaclient.exceptions import EntitlementNotFoundError
from uaclient.util import is_config_value_true

ENTITLEMENT_CLASSES = [
    CommonCriteriaEntitlement,
    CISEntitlement,
    ESMAppsEntitlement,
    ESMInfraEntitlement,
    fips.FIPSEntitlement,
    fips.FIPSUpdatesEntitlement,
    LivepatchEntitlement,
    RealtimeKernelEntitlement,
    ROSEntitlement,
    ROSUpdatesEntitlement,
]  # type: List[Type[UAEntitlement]]


def entitlement_factory(name: str):
    """Returns a UAEntitlement class based on the provided name.

    The return type is Optional[Type[UAEntitlement]].
    It cannot be explicit because of the Python version on Xenial (3.5.2).
    :param name: The name of the entitlement to return
    :param not_found_okay: If True and no entitlement with the given name is
        found, then returns None.
    :raise EntitlementNotFoundError: If not_found_okay is False and no
        entitlement with the given name is found, then raises this error.
    """
    for entitlement in ENTITLEMENT_CLASSES:
        if name in entitlement().valid_names:
            return entitlement
    raise EntitlementNotFoundError()


def valid_services(
    allow_beta: bool = False, all_names: bool = False
) -> List[str]:
    """Return a list of valid (non-beta) services.

    @param allow_beta: if we should allow beta services to be marked as valid
    @param all_names: if we should return all the names for a service instead
        of just the presentation_name
    """
    cfg = UAConfig()
    allow_beta_cfg = is_config_value_true(cfg.cfg, "features.allow_beta")
    allow_beta |= allow_beta_cfg

    entitlements = ENTITLEMENT_CLASSES
    if not allow_beta:
        entitlements = [
            entitlement
            for entitlement in entitlements
            if not entitlement.is_beta
        ]

    if all_names:
        names = []
        for entitlement in entitlements:
            names.extend(entitlement().valid_names)

        return sorted(names)

    return sorted(
        [entitlement().presentation_name for entitlement in entitlements]
    )
