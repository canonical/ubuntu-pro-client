from collections import namedtuple
from enum import Enum
from typing import Any, Dict, List

from apt import Cache  # type: ignore
from apt import package as apt_package

from uaclient.config import UAConfig
from uaclient.entitlements import ENTITLEMENT_CLASS_BY_NAME
from uaclient.status import ApplicationStatus, ContractStatus
from uaclient.util import get_platform_info

ESM_SERVICES = ("esm-infra", "esm-apps")
SECURITY_REPO_TEMPLATES = (
    "{}-security",
    "{}-apps-security",
    "{}-infra-security",
)

ESM_INFRA_ORIGIN = "UbuntuESM"
ESM_APPS_ORIGIN = "UbuntuESMApps"


class UpdateStatus(Enum):
    "Represents the availability of a security package."
    AVAILABLE = "upgrade_available"
    UNATTACHED = "pending_attach"
    NOT_ENABLED = "pending_enable"
    UNAVAILABLE = "upgrade_unavailable"


ServiceStatus = namedtuple("ServiceStatus", ["is_entitled", "is_enabled"])


def get_service_name(origins: List[apt_package.Origin]) -> str:
    "Translates the archive name in the version origin to a UA service name."
    for origin in origins:
        if (
            "infra-security" in origin.archive
            and origin.origin == ESM_INFRA_ORIGIN
        ):
            return "esm-infra"
        if (
            "apps-security" in origin.archive
            and origin.origin == ESM_APPS_ORIGIN
        ):
            return "esm-apps"
    return "standard-security"


def get_update_status(service_name: str, ua_info: Dict[str, Any]) -> str:
    """Defines the update status for a package based on the service name.

    For ESM-[Infra|Apps] packages, first checks if UA is attached. If this is
    the case, also check for availability of the service.
    """
    if service_name == "standard-security" or (
        ua_info["attached"] and service_name in ua_info["enabled_services"]
    ):
        return UpdateStatus.AVAILABLE.value
    if not ua_info["attached"]:
        return UpdateStatus.UNATTACHED.value
    if service_name in ua_info["entitled_services"]:
        return UpdateStatus.NOT_ENABLED.value
    return UpdateStatus.UNAVAILABLE.value


def get_service_status(cfg: UAConfig, service_name: str) -> ServiceStatus:
    """Returns the UA status for a specific service.

    Checks if the service is entitled and enabled.
    """
    entitlement = ENTITLEMENT_CLASS_BY_NAME[service_name](cfg)
    return ServiceStatus(
        entitlement.contract_status() == ContractStatus.ENTITLED,
        entitlement.application_status()[0] == ApplicationStatus.ENABLED,
    )


def filter_security_updates(
    packages: List[apt_package.Package]
) -> List[apt_package.Package]:
    """Filters a list of packages looking for available security updates.

    Checks if the package has a greater version available, and if the origin of
    this version matches any of the series' security repositories.
    """
    series = get_platform_info()["series"]
    security_repos = [
        template.format(series) for template in SECURITY_REPO_TEMPLATES
    ]

    return [
        package
        for package in packages
        if max(package.versions) > package.installed
        and any(
            origin.archive in security_repos
            for origin in max(package.versions).origins
        )
    ]


def get_ua_info(cfg: UAConfig) -> Dict[str, Any]:
    """Returns the UA information based on the config object."""
    ua_info = {
        "attached": False,
        "enabled_services": [],
        "entitled_services": [],
    }  # type: Dict[str, Any]

    if cfg.is_attached:
        ua_info["attached"] = True
        for service in ESM_SERVICES:
            status = get_service_status(cfg, service)
            if status.is_entitled:
                ua_info["entitled_services"].append(service)
            if status.is_enabled:
                ua_info["enabled_services"].append(service)

    return ua_info


def security_status(cfg: UAConfig) -> Dict[str, Any]:
    """Returns the status of security updates on a system.

    The returned dict has a 'packages' key with a list of all installed
    packages which can receive security updates, with or without ESM,
    reflecting the availability of the update based on the UA status.

    There is also a summary with the UA information and the package counts.
    """
    ua_info = get_ua_info(cfg)

    summary = {"ua": ua_info}  # type: Dict[str, Any]
    packages = []
    cache = Cache()

    installed_packages = [package for package in cache if package.is_installed]
    summary["num_installed_packages"] = len(installed_packages)

    security_upgradable_packages = filter_security_updates(installed_packages)

    package_count = {"esm-infra": 0, "esm-apps": 0, "standard-security": 0}

    for package in security_upgradable_packages:
        candidate = max(package.versions)
        version = candidate.version
        service_name = get_service_name(candidate.origins)
        status = get_update_status(service_name, ua_info)
        package_count[service_name] += 1
        packages.append(
            {
                "package": package.name,
                "version": version,
                "service_name": service_name,
                "status": status,
            }
        )

    summary["num_esm_infra_updates"] = package_count["esm-infra"]
    summary["num_esm_apps_updates"] = package_count["esm-apps"]
    summary["num_standard_security_updates"] = package_count[
        "standard-security"
    ]

    return {"summary": summary, "packages": packages}
