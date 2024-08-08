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
        Field(
            "code",
            StringDataValue,
            doc="Short string that represents the reason",
        ),
        Field(
            "title",
            StringDataValue,
            doc="Longer string describing the reason - possibly translated",
        ),
    ]

    def __init__(self, *, code: str, title: str):
        self.code = code
        self.title = title


class ServiceWithReason(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            doc="Name of the Pro service this item corresponds to",
        ),
        Field(
            "reason",
            Reason,
            doc="Reason that this service is in the list it is in",
        ),
    ]

    def __init__(self, *, name: str, reason: Reason):
        self.name = name
        self.reason = reason


class ServiceWithDependencies(DataObject):
    fields = [
        Field(
            "name",
            StringDataValue,
            doc="Name of the Pro service this item corresponds to",
        ),
        Field(
            "incompatible_with",
            data_list(ServiceWithReason),
            doc=(
                "List of Pro services this service is incompatible with. That"
                " means they cannot be enabled at the same time."
            ),
        ),
        Field(
            "depends_on",
            data_list(ServiceWithReason),
            doc=(
                "List of Pro services this service depends on. The services"
                " in this list must be enabled for this service to be enabled."
            ),
        ),
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
        Field(
            "services",
            data_list(ServiceWithDependencies),
            doc="Each Pro service gets an item in this list",
        ),
    ]

    def __init__(self, *, services: List[ServiceWithDependencies]):
        self.services = services


def dependencies() -> DependenciesResult:
    return _dependencies(UAConfig())


def _dependencies(cfg: UAConfig) -> DependenciesResult:
    """
    This endpoint will return a full list of all service dependencies,
    regardless of the current system state. That means it will always return
    the same thing until new services are added, or until we add/remove
    dependencies between services.
    """
    services = []
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls(cfg)
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

_doc = {
    "introduced_in": "32",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.services.dependencies.v1 import dependencies
result = dependencies()
""",
    "result_class": DependenciesResult,
    "example_cli": "pro api u.pro.services.dependencies.v1",
    "example_json": """
{
    "services": [
        {
            "name": "one",
            "depends_on": [
                {
                    "name": "zero",
                    "reason": {
                        "code": "one-and-zero",
                        "title": "Service One requires service Zero."
                    }
                },
                ...
            ],
            "incompatible_with": [
                {
                    "name": "two",
                    "reason": {
                        "code": "one-and-two",
                        "title": "Services One and Two are not compatible."
                    }
                },
                ...
            ]
        },
        ...
    ]
}
""",
}
