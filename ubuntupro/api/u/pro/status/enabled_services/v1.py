from typing import List, Optional

from ubuntupro.api.api import APIEndpoint
from ubuntupro.api.data_types import AdditionalInfo
from ubuntupro.api.u.pro.status.is_attached.v1 import _is_attached
from ubuntupro.config import UAConfig
from ubuntupro.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)
from ubuntupro.entitlements.entitlement_status import UserFacingStatus


class EnabledService(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("variant_enabled", BoolDataValue),
        Field("variant_name", StringDataValue, False),
    ]

    def __init__(
        self,
        *,
        name: str,
        variant_enabled: bool = False,
        variant_name: Optional[str] = None
    ):
        self.name = name
        self.variant_enabled = variant_enabled
        self.variant_name = variant_name


class EnabledServicesResult(DataObject, AdditionalInfo):
    fields = [
        Field("enabled_services", data_list(EnabledService)),
    ]

    def __init__(self, *, enabled_services: List[EnabledService]):
        self.enabled_services = enabled_services


def enabled_services() -> EnabledServicesResult:
    return _enabled_services(UAConfig())


def _enabled_services(cfg: UAConfig) -> EnabledServicesResult:
    from ubuntupro.entitlements import ENTITLEMENT_CLASSES

    if not _is_attached(cfg).is_attached:
        return EnabledServicesResult(enabled_services=[])

    enabled_services = []  # type: List[EnabledService]
    for ent_cls in ENTITLEMENT_CLASSES:
        ent = ent_cls(cfg)
        if ent.user_facing_status()[0] == UserFacingStatus.ACTIVE:
            enabled_service = EnabledService(name=ent.name)
            for _, variant_cls in ent.variants.items():
                variant = variant_cls(cfg)

                if variant.user_facing_status()[0] == UserFacingStatus.ACTIVE:
                    enabled_service = EnabledService(
                        name=ent.name,
                        variant_enabled=True,
                        variant_name=variant.variant_name,
                    )
                    break

            enabled_services.append(enabled_service)

    return EnabledServicesResult(
        enabled_services=sorted(enabled_services, key=lambda x: x.name)
    )


endpoint = APIEndpoint(
    version="v1",
    name="EnabledServices",
    fn=_enabled_services,
    options_cls=None,
)
