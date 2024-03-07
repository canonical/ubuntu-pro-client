import logging
from typing import List

from uaclient import entitlements, util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class Reason(DataObject):
    fields = [
        Field("code", StringDataValue),
        Field("title", StringDataValue),
    ]

    def __init__(self, *, code: str, title: str):
        self.code = code
        self.title = title


class ServiceWithReason(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("reason", Reason),
    ]

    def __init__(self, *, name: str, reason: Reason):
        self.name = name
        self.reason = reason


class ServiceWithDependencies(DataObject):
    fields = [
        Field("name", StringDataValue),
        Field("incompatible_with", data_list(ServiceWithReason)),
        Field("depends_on", data_list(ServiceWithReason)),
    ]

    def __init__(
        self,
        *,
        name: str,
        incompatible_with: List[ServiceWithReason],
        depends_on: List[ServiceWithReason]
    ):
        self.name = name
        self.incompatible_with = incompatible_with
        self.depends_on = depends_on


class DependenciesResult(DataObject, AdditionalInfo):
    fields = [
        Field("services", data_list(ServiceWithDependencies)),
    ]

    def __init__(self, *, services: List[ServiceWithDependencies]):
        self.services = services


def dependencies() -> DependenciesResult:
    return _dependencies(UAConfig())


def _dependencies(cfg: UAConfig) -> DependenciesResult:
    services = []
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = entitlements.entitlement_factory(cfg, name=ent_cls.name)
        incompatible_with = []
        depends_on = []
        for ent_with_reason in ent.incompatible_services:
            incompatible_with.append(
                ServiceWithReason(
                    name=ent_with_reason.entitlement.name,
                    reason=Reason(
                        code=ent_with_reason.named_msg.name,
                        title=ent_with_reason.named_msg.msg,
                    ),
                )
            )
        for ent_with_reason in ent.required_services:
            depends_on.append(
                ServiceWithReason(
                    name=ent_with_reason.entitlement.name,
                    reason=Reason(
                        code=ent_with_reason.named_msg.name,
                        title=ent_with_reason.named_msg.msg,
                    ),
                )
            )
        services.append(
            ServiceWithDependencies(
                name=ent_cls.name,
                incompatible_with=incompatible_with,
                depends_on=depends_on,
            )
        )
    return DependenciesResult(services=services)


endpoint = APIEndpoint(
    version="v1",
    name="ServiceDependencies",
    fn=_dependencies,
    options_cls=None,
)
