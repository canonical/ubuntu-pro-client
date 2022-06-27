from collections import defaultdict
from enum import Enum
from typing import Any, DefaultDict, Dict, List, Tuple  # noqa: F401

from apt import Cache  # type: ignore
from apt import package as apt_package

from uaclient.config import UAConfig
from uaclient.status import status
from uaclient.util import get_platform_info

series = get_platform_info()["series"]

ESM_SERVICES = ("esm-infra", "esm-apps")


ORIGIN_INFORMATION_TO_SERVICE = {
    ("Ubuntu", "{}-security".format(series)): "standard-security",
    ("UbuntuESMApps", "{}-apps-security".format(series)): "esm-apps",
    ("UbuntuESM", "{}-infra-security".format(series)): "esm-infra",
}


class UpdateStatus(Enum):
    "Represents the availability of a security package."
    AVAILABLE = "upgrade_available"
    UNATTACHED = "pending_attach"
    NOT_ENABLED = "pending_enable"
    UNAVAILABLE = "upgrade_unavailable"


def get_origin_for_package(package: apt_package.Package) -> str:
    """
    Returns the origin for a package installed in the system.

    Technically speaking, packages don't have origins - their versions do.
    We check the available versions (installed, candidate) to determine the
    most reasonable origin for the package.
    """
    available_origins = package.installed.origins

    # If the installed version for a package has a single origin, it means that
    # only the local dpkg reference is there. Then, we check if there is a
    # candidate version. No candidate means we don't know anything about the
    # package. Otherwise we check for the origins of the candidate version.
    if len(available_origins) == 1:
        if package.installed == package.candidate:
            return "unknown"
        available_origins = package.candidate.origins

    for origin in available_origins:
        service = ORIGIN_INFORMATION_TO_SERVICE.get(
            (origin.origin, origin.archive), ""
        )
        if service in ESM_SERVICES:
            return service
        if origin.origin == "Ubuntu":
            return origin.component

    return "third-party"


def get_service_name(origins: List[apt_package.Origin]) -> Tuple[str, str]:
    """
    Translates the archive name in the version origin to an Ubuntu Pro service
    name.
    """
    for origin in origins:
        service = ORIGIN_INFORMATION_TO_SERVICE.get(
            (origin.origin, origin.archive)
        )
        if service:
            return service, origin.site
    return ("", "")


def get_update_status(service_name: str, ua_info: Dict[str, Any]) -> str:
    """Defines the update status for a package based on the service name.

    For ESM-[Infra|Apps] packages, first checks if Pro is attached. If this is
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


def filter_security_updates(
    packages: List[apt_package.Package],
) -> List[apt_package.Version]:
    """Filters a list of packages looking for available security updates.

    Checks if the package has a greater version available, and if the origin of
    this version matches any of the series' security repositories.
    """
    return [
        version
        for package in packages
        for version in package.versions
        if version > package.installed
        and any(
            (origin.origin, origin.archive) in ORIGIN_INFORMATION_TO_SERVICE
            for origin in version.origins
        )
    ]


def get_ua_info(cfg: UAConfig) -> Dict[str, Any]:
    """Returns the Pro information based on the config object."""
    ua_info = {
        "attached": False,
        "enabled_services": [],
        "entitled_services": [],
    }  # type: Dict[str, Any]

    status_dict = status(cfg=cfg, show_beta=True)
    if status_dict["attached"]:
        ua_info["attached"] = True
        for service in status_dict["services"]:
            if service["name"] in ESM_SERVICES:
                if service["entitled"] == "yes":
                    ua_info["entitled_services"].append(service["name"])
                if service["status"] == "enabled":
                    ua_info["enabled_services"].append(service["name"])

    return ua_info


def get_installed_packages():
    cache = Cache()
    return [package for package in cache if package.is_installed]
