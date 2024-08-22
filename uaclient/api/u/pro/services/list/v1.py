# Services List
import logging
from typing import List, Optional

from uaclient import exceptions, util
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.contract import get_available_resources
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.entitlements import entitlement_factory
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ContractStatus,
)
from uaclient.files import machine_token

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class ServiceInfo(DataObject, AdditionalInfo):
    fields = [
        Field("name", StringDataValue, doc="Name of the service"),
        Field(
            "description", StringDataValue, doc="Description of the service"
        ),
        Field(
            "available",
            BoolDataValue,
            doc="Service availability for a subscription",
        ),
        Field(
            "entitled",
            BoolDataValue,
            doc="Entitlement of a service for a subscription",
        ),
    ]

    def __init__(
        self,
        *,
        name: str,
        desc: str,
        available: bool,
        entitled: Optional[bool] = None
    ):
        self.name = name
        self.description = desc
        self.available = available
        self.entitled = entitled


class ServiceListResult(DataObject, AdditionalInfo):
    fields = [
        Field("services", data_list(ServiceInfo), doc="List of services"),
    ]

    def __init__(self, *, services: List[ServiceInfo]):
        self.services = services


def list() -> ServiceListResult:
    return _list(UAConfig())


def _list(cfg: UAConfig) -> ServiceListResult:
    if not _is_attached(cfg).is_attached:
        return unattached_services(cfg)
    return attached_services(cfg)


def attached_services(cfg: UAConfig) -> ServiceListResult:
    services_list = []
    machine_token_file = machine_token.get_machine_token_file(cfg)
    resources = machine_token_file.machine_token.get("availableResources")
    if not resources:
        resources = get_available_resources(cfg)
    for resource in resources:
        try:
            ent = entitlement_factory(cfg=cfg, name=resource.get("name", ""))
        except exceptions.EntitlementNotFoundError:
            LOG.debug(
                "Ignoring availability of unknown service %s from contract "
                "server",
                resource.get("name", "without a 'name' key"),
            )
            continue

        services_list.append(_get_service_info(cfg, ent))
    services_list.sort(key=lambda x: x.name)
    return ServiceListResult(services=services_list)


def unattached_services(cfg: UAConfig) -> ServiceListResult:
    services_list = []
    resources = get_available_resources(cfg)
    for resource in resources:
        available = True if resource.get("available") else False
        try:
            ent = entitlement_factory(cfg=cfg, name=resource.get("name", ""))
        except exceptions.EntitlementNotFoundError:
            LOG.debug(
                "Ignoring availability of unknown service %s from contract "
                "server",
                resource.get("name", "without a 'name' key"),
            )
            continue
        service = ServiceInfo(
            name=resource.get("presentedAs", resource["name"]),
            desc=ent.description,
            available=available,
            entitled=None,
        )
        services_list.append(service)
    services_list.sort(key=lambda x: x.name)
    return ServiceListResult(services=services_list)


def _get_service_info(
    cfg: UAConfig,
    ent: UAEntitlement,
) -> ServiceInfo:
    entitled = ent.contract_status() == ContractStatus.ENTITLED
    available = ent.applicability_status()[0] == ApplicabilityStatus.APPLICABLE

    service_info = ServiceInfo(
        name=ent.presentation_name,
        desc=ent.description,
        available=available,
        entitled=entitled,
    )
    return service_info


endpoint = APIEndpoint(
    version="v1",
    name="ServicesList",
    fn=_list,
    options_cls=None,
)

_doc = {
    "introduced_in": "35",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.services.list.v1 import list

result = list()
""",  # noqa: E501
    "result_class": ServiceListResult,
    "exceptions": [
        (
            exceptions.ContractAPIError,
            "If the contract server returns an error",
        )
    ],
    "example_cli": "pro api u.pro.services.list.v1",
    "example_json": """
{
"attributes": {
"services": [
  {
    "available": true,
    "description": "Scalable Android in the cloud",
    "entitled": null,
    "name": "anbox-cloud",
  },
  ...
  {
    "available": true,
    "description": "Ubuntu kernel with PREEMPT_RT patches integrated",
    "entitled": null,
    "name": "realtime-kernel",
  },
  {
    "available": false,
    "description": "Security Updates for the Robot Operating System",
    "entitled": null,
    "name": "ros",
  },
  {
    "available": false,
    "description": "All Updates for the Robot Operating System",
    "entitled": null,
    "name": "ros-updates",
  }
]
},
"meta": {
    "environment_vars": []
},
"type": "ServicesList"
}
""",
}
