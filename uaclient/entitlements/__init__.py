from typing import Dict, List, Type, cast  # noqa: F401

from uaclient.config import UAConfig
from uaclient.entitlements import fips
from uaclient.entitlements.base import UAEntitlement  # noqa: F401
from uaclient.entitlements.cc import CommonCriteriaEntitlement
from uaclient.entitlements.cis import CISEntitlement
from uaclient.entitlements.esm import ESMAppsEntitlement, ESMInfraEntitlement
from uaclient.entitlements.livepatch import LivepatchEntitlement
from uaclient.entitlements.ros import ROSEntitlement, ROSUpdatesEntitlement
from uaclient.util import is_config_value_true

ENTITLEMENT_CLASSES = [
    CommonCriteriaEntitlement,
    CISEntitlement,
    ESMAppsEntitlement,
    ESMInfraEntitlement,
    fips.FIPSEntitlement,
    fips.FIPSUpdatesEntitlement,
    LivepatchEntitlement,
    ROSEntitlement,
    ROSUpdatesEntitlement,
]  # type: List[Type[UAEntitlement]]


ENTITLEMENT_CLASS_BY_NAME = dict(
    (cast(str, cls.name), cls) for cls in ENTITLEMENT_CLASSES
)  # type: Dict[str, Type[UAEntitlement]]


def valid_services(allow_beta: bool = False) -> List[str]:
    """Return a list of valid (non-beta) services.

    @param allow_beta: if we should allow beta services to be marked as valid
    """
    cfg = UAConfig()
    allow_beta_cfg = is_config_value_true(cfg.cfg, "features.allow_beta")
    allow_beta |= allow_beta_cfg

    if allow_beta:
        return sorted(ENTITLEMENT_CLASS_BY_NAME.keys())

    return sorted(
        [
            ent_name
            for ent_name, ent_cls in ENTITLEMENT_CLASS_BY_NAME.items()
            if not ent_cls.is_beta
        ]
    )
