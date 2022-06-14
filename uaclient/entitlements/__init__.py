import enum
from typing import Dict, List, Type  # noqa: F401

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

ENTITLEMENT_CLS_BY_NAME = {
    str(ent_cls.name): ent_cls for ent_cls in ENTITLEMENT_CLASSES
}  # type: Dict[str, Type[UAEntitlement]]


def entitlement_factory(cfg: UAConfig, name: str):
    """Returns a UAEntitlement class based on the provided name.

    The return type is Optional[Type[UAEntitlement]].
    It cannot be explicit because of the Python version on Xenial (3.5.2).
    :param cfg: UAConfig instance
    :param name: The name of the entitlement to return
    :param not_found_okay: If True and no entitlement with the given name is
        found, then returns None.
    :raise EntitlementNotFoundError: If not_found_okay is False and no
        entitlement with the given name is found, then raises this error.
    """
    for entitlement in ENTITLEMENT_CLASSES:
        if name in entitlement(cfg=cfg).valid_names:
            return entitlement
    raise EntitlementNotFoundError()


def valid_services(
    cfg: UAConfig, allow_beta: bool = False, all_names: bool = False
) -> List[str]:
    """Return a list of valid (non-beta) services.

    :param cfg: UAConfig instance
    :param allow_beta: if we should allow beta services to be marked as valid
    :param all_names: if we should return all the names for a service instead
        of just the presentation_name
    """
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
            names.extend(entitlement(cfg=cfg).valid_names)

        return sorted(names)

    return sorted(
        [
            entitlement(cfg=cfg).presentation_name
            for entitlement in entitlements
        ]
    )


@enum.unique
class SortOrder(enum.Enum):
    REQUIRED_SERVICES = object()
    DEPENDENT_SERVICES = object()


def entitlements_disable_order() -> List[str]:
    """
    Return the entitlements disable order based on dependent services logic.
    """
    return _sort_entitlements(key=SortOrder.DEPENDENT_SERVICES)


def entitlements_enable_order() -> List[str]:
    """
    Return the entitlements enable order based on required services logic.
    """
    return _sort_entitlements(key=SortOrder.REQUIRED_SERVICES)


def _visit_ent(
    ent_cls: Type[UAEntitlement],
    key: SortOrder,
    visited: Dict[str, bool],
    order: List[str],
):
    if ent_cls.name in visited:
        return

    if key == SortOrder.REQUIRED_SERVICES:
        cls_list = ent_cls._required_services
    else:
        cls_list = ent_cls._dependent_services

    for ent_name in cls_list:
        req_cls = ENTITLEMENT_CLS_BY_NAME.get(ent_name)

        if req_cls and req_cls.name not in visited:
            _visit_ent(req_cls, key, visited, order)

    order.append(str(ent_cls.name))
    visited[str(ent_cls.name)] = True


def _sort_entitlements(key: SortOrder) -> List[str]:
    order = []  # type: List[str]
    visited = {}  # type: Dict[str, bool]

    for ent_cls in ENTITLEMENT_CLASSES:
        _visit_ent(ent_cls, key, visited, order)

    return order
