import json
import logging
import re
import textwrap
from collections import defaultdict
from enum import Enum
from functools import lru_cache
from random import choice
from typing import Any, DefaultDict, Dict, List, Tuple  # noqa: F401

import apt  # type: ignore

from uaclient import messages
from uaclient.config import UAConfig
from uaclient.defaults import ESM_APT_ROOTDIR
from uaclient.entitlements import ESMAppsEntitlement, ESMInfraEntitlement
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
)
from uaclient.entitlements.livepatch import LIVEPATCH_CMD
from uaclient.exceptions import ProcessExecutionError
from uaclient.status import status
from uaclient.system import (
    REBOOT_PKGS_FILE_PATH,
    get_distro_info,
    get_kernel_info,
    get_platform_info,
    is_current_series_lts,
    is_supported,
    load_file,
    should_reboot,
    subp,
    which,
)

ESM_SERVICES = ("esm-infra", "esm-apps")


class UpdateStatus(Enum):
    "Represents the availability of a security package."
    AVAILABLE = "upgrade_available"
    UNATTACHED = "pending_attach"
    NOT_ENABLED = "pending_enable"
    UNAVAILABLE = "upgrade_unavailable"


class RebootStatus(Enum):
    REBOOT_REQUIRED = "yes"
    REBOOT_NOT_REQUIRED = "no"
    REBOOT_REQUIRED_LIVEPATCH_APPLIED = "yes-kernel-livepatches-applied"


@lru_cache(maxsize=None)
def get_origin_information_to_service_map():
    series = get_platform_info()["series"]
    return {
        ("Ubuntu", "{}-security".format(series)): "standard-security",
        ("UbuntuESMApps", "{}-apps-security".format(series)): "esm-apps",
        ("UbuntuESM", "{}-infra-security".format(series)): "esm-infra",
        ("UbuntuESMApps", "{}-apps-updates".format(series)): "esm-apps",
        ("UbuntuESM", "{}-infra-updates".format(series)): "esm-infra",
    }


@lru_cache(maxsize=None)
def get_esm_cache():
    try:
        # If the rootdir folder doesn't contain any apt source info, the
        # cache will be empty
        cache = apt.Cache(rootdir=ESM_APT_ROOTDIR)
    except Exception:
        cache = {}

    return cache


def get_installed_packages_by_origin() -> DefaultDict[
    "str", List[apt.package.Package]
]:
    result = defaultdict(list)

    cache = apt.Cache()
    installed_packages = [package for package in cache if package.is_installed]
    result["all"] = installed_packages

    for package in installed_packages:
        result[get_origin_for_package(package)].append(package)

    return result


def get_origin_for_package(package: apt.package.Package) -> str:
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
        if package.candidate is None or package.installed == package.candidate:
            return "unknown"
        available_origins = package.candidate.origins

    for origin in available_origins:
        service = get_origin_information_to_service_map().get(
            (origin.origin, origin.archive), ""
        )
        if service in ESM_SERVICES:
            return service
        if origin.origin == "Ubuntu":
            return origin.component

    return "third-party"


def get_update_status(service_name: str, ua_info: Dict[str, Any]) -> str:
    """Defines the update status for a package based on the service name.

    For ESM-[Infra|Apps] packages, first checks if Pro is attached. If this is
    the case, also check for availability of the service.
    """
    if service_name in ("standard-security", "standard-updates") or (
        ua_info["attached"] and service_name in ua_info["enabled_services"]
    ):
        return UpdateStatus.AVAILABLE.value
    if not ua_info["attached"]:
        return UpdateStatus.UNATTACHED.value
    if service_name in ua_info["entitled_services"]:
        return UpdateStatus.NOT_ENABLED.value
    return UpdateStatus.UNAVAILABLE.value


def filter_security_updates(
    packages: List[apt.package.Package],
) -> DefaultDict[str, List[Tuple[apt.package.Version, str]]]:
    """Filters a list of packages looking for available updates.

    All versions greater than the installed one are reported, based on where
    it is provided, including ESM pockets, excluding backports.
    """
    result = defaultdict(list)

    # This esm_cache will only be usefull for the situation where
    # the user does not have the esm (infra or apps) services enabled,
    # but has be advertised about esm packages. Since those
    # sources live in a private folder, we need a different apt cache
    # to access them.
    esm_cache = get_esm_cache()

    for package in packages:
        if package.is_installed:
            for version in package.versions:
                if version > package.installed:
                    counted_as_security = False
                    for origin in version.origins:
                        service = get_origin_information_to_service_map().get(
                            (origin.origin, origin.archive)
                        )
                        if service:
                            result[service].append((version, origin.site))
                            counted_as_security = True
                            break  # No need to loop through all the origins
                    # Also no need to report backports at least for now...
                    expected_origin = version.origins[0]
                    if (
                        not counted_as_security
                        and "backports" not in expected_origin.archive
                    ):
                        result["standard-updates"].append(
                            (version, expected_origin.site)
                        )

            # This loop should be only used if the user does not have esm
            # (infra or apps) enabled, and it is shorter than the previous one
            if package.name in esm_cache:
                esm_package = esm_cache[package.name]
                for version in esm_package.versions:
                    if version > package.installed:
                        for origin in version.origins:
                            service = (
                                get_origin_information_to_service_map().get(
                                    (origin.origin, origin.archive)
                                )
                            )
                            if service:
                                result[service].append((version, origin.site))
                                break

    return result


def get_ua_info(cfg: UAConfig) -> Dict[str, Any]:
    """Returns the Pro information based on the config object."""
    ua_info = {
        "attached": False,
        "enabled_services": [],
        "entitled_services": [],
    }  # type: Dict[str, Any]

    status_dict = status(cfg=cfg, show_all=True)
    if status_dict["attached"]:
        ua_info["attached"] = True
        for service in status_dict["services"]:
            if service["name"] in ESM_SERVICES:
                if service["entitled"] == "yes":
                    ua_info["entitled_services"].append(service["name"])
                if service["status"] == "enabled":
                    ua_info["enabled_services"].append(service["name"])

    return ua_info


# Yeah Any is bad, but so is python<3.8 without TypedDict
def get_livepatch_fixed_cves() -> List[Dict[str, Any]]:
    try:
        out, _err = subp([LIVEPATCH_CMD, "status", "--format", "json"])
    except ProcessExecutionError:
        return []

    try:
        livepatch_output = json.loads(out)
    except json.JSONDecodeError:
        msg = "Could not parse Livepatch Status JSON: {}".format(out)
        logging.debug(msg)
        return []

    status_list = livepatch_output.get("Status")
    if status_list:
        # Livepatch guarantees this list has only one element
        lp_kernel_version = status_list[0].get("Kernel")
        our_kernel_version = get_kernel_info().proc_version_signature_version
        if (
            our_kernel_version is not None
            and our_kernel_version == lp_kernel_version
        ):
            livepatch_status = status_list[0].get("Livepatch", {})
            if livepatch_status.get("State", "") == "applied":
                fixes = livepatch_status.get("Fixes", [])
                return [
                    {
                        "name": fix.get("Name", ""),
                        "patched": fix.get("Patched", ""),
                    }
                    for fix in fixes
                ]

    return []


def get_reboot_status():
    if not should_reboot():
        return RebootStatus.REBOOT_NOT_REQUIRED

    try:
        pkg_list_str = load_file(REBOOT_PKGS_FILE_PATH)
    except FileNotFoundError:
        # If we cannot load that file, we cannot evaluate if we have
        # kernel related packages that require a reboot. Therefore, we
        # will just say that a reboot is required
        return RebootStatus.REBOOT_REQUIRED

    pkg_list = pkg_list_str.split()
    num_pkgs = len(pkg_list)

    kernel_regex = "^(linux-image|linux-base).*"
    num_kernel_pkgs = 0

    for pkg in pkg_list:
        if re.match(kernel_regex, pkg):
            num_kernel_pkgs += 1

    # We will only check the Livepatch state if all the
    # packages that require a reboot are kernel related
    if num_kernel_pkgs != num_pkgs:
        return RebootStatus.REBOOT_REQUIRED

    if not which("canonical-livepatch"):
        return RebootStatus.REBOOT_REQUIRED

    try:
        livepatch_status, _ = subp(
            [LIVEPATCH_CMD, "status", "--format", "json"]
        )
    except ProcessExecutionError:
        # If we can't query the Livepatch status, then return a
        # normal reboot state
        logging.debug("Could not query Livepatch Status")
        return RebootStatus.REBOOT_REQUIRED

    try:
        livepatch_status_dict = json.loads(livepatch_status)
    except json.JSONDecodeError:
        # If we cannot parse the json file, we will return a
        # normal reboot state
        msg = "Could not parse Livepatch Status JSON: {}".format(
            livepatch_status
        )
        logging.debug(msg)
        return RebootStatus.REBOOT_REQUIRED

    patch_statuses = livepatch_status_dict.get("Status", [{}])

    kernel_info = get_kernel_info()
    kernel_name = kernel_info.proc_version_signature_version

    patch_state = ""
    for patch_status in patch_statuses:
        livepatch_kernel = patch_status.get("Kernel")
        if livepatch_kernel and livepatch_kernel == kernel_name:
            patch_state = patch_status.get("Livepatch", {}).get("State", "")

    if patch_state == "applied":
        return RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED

    # Any other Livepatch status will not be considered here to modify the
    # reboot state
    return RebootStatus.REBOOT_REQUIRED


def create_updates_list(
    security_upgradable_versions: DefaultDict[
        str, List[Tuple[apt.package.Version, str]]
    ],
    ua_info: Dict[str, Any],
) -> List[Dict[str, Any]]:
    updates = []
    for service, version_list in security_upgradable_versions.items():
        status = get_update_status(service, ua_info)
        for version, origin in version_list:
            updates.append(
                {
                    "package": version.package.name,
                    "version": version.version,
                    "service_name": service,
                    "status": status,
                    "origin": origin,
                    "download_size": version.size,
                }
            )

    return updates


def security_status_dict(cfg: UAConfig) -> Dict[str, Any]:
    """Returns the status of security updates on a system.

    The returned dict has a 'packages' key with a list of all installed
    packages which can receive security updates, with or without ESM,
    reflecting the availability of the update based on the Pro status.

    There is also a summary with the Ubuntu Pro information and the package
    counts.
    """
    ua_info = get_ua_info(cfg)

    summary = {"ua": ua_info}  # type: Dict[str, Any]
    packages_by_origin = get_installed_packages_by_origin()

    installed_packages = packages_by_origin["all"]
    summary["num_installed_packages"] = len(installed_packages)

    security_upgradable_versions = filter_security_updates(installed_packages)
    # This version of security-status only cares about security updates
    security_upgradable_versions["standard-updates"] = []

    updates = create_updates_list(security_upgradable_versions, ua_info)

    summary["num_main_packages"] = len(packages_by_origin["main"])
    summary["num_restricted_packages"] = len(packages_by_origin["restricted"])
    summary["num_universe_packages"] = len(packages_by_origin["universe"])
    summary["num_multiverse_packages"] = len(packages_by_origin["multiverse"])
    summary["num_third_party_packages"] = len(
        packages_by_origin["third-party"]
    )
    summary["num_unknown_packages"] = len(packages_by_origin["unknown"])
    summary["num_esm_infra_packages"] = len(packages_by_origin["esm-infra"])
    summary["num_esm_apps_packages"] = len(packages_by_origin["esm-apps"])

    summary["num_esm_infra_updates"] = len(
        security_upgradable_versions["esm-infra"]
    )
    summary["num_esm_apps_updates"] = len(
        security_upgradable_versions["esm-apps"]
    )
    summary["num_standard_security_updates"] = len(
        security_upgradable_versions["standard-security"]
    )
    summary["reboot_required"] = get_reboot_status().value

    return {
        "_schema_version": "0.1",
        "summary": summary,
        "packages": updates,
        "livepatch": {"fixed_cves": get_livepatch_fixed_cves()},
    }


def _print_package_summary(
    package_lists: DefaultDict[str, List[apt.package.Package]],
    show_items: str = "all",
    always_show: bool = False,
) -> None:
    total_packages = len(package_lists["all"])
    print(messages.SS_SUMMARY_TOTAL.format(count=total_packages))

    offset = " " * (len(str(total_packages)) + 1)

    if show_items in ("all", "esm-infra"):
        packages_mr = (
            len(package_lists["main"])
            + len(package_lists["restricted"])
            + len(package_lists["esm-infra"])
        )
        print(
            messages.SS_SUMMARY_ARCHIVE.format(
                offset=offset,
                count=packages_mr,
                plural="s",
                repository="Main/Restricted",
            )
        )

    if show_items in ("all", "esm-apps"):
        packages_um = (
            len(package_lists["universe"])
            + len(package_lists["multiverse"])
            + len(package_lists["esm-apps"])
        )
        if packages_um or always_show:
            print(
                messages.SS_SUMMARY_ARCHIVE.format(
                    offset=offset,
                    count=packages_um,
                    plural="s" if packages_um > 1 else "",
                    repository="Universe/Multiverse",
                )
            )

    if show_items in ("all", "third-party"):
        packages_thirdparty = len(package_lists["third-party"])
        if packages_thirdparty or always_show:
            msg = messages.SS_SUMMARY_THIRD_PARTY_SN
            if packages_thirdparty > 1:
                msg = messages.SS_SUMMARY_THIRD_PARTY_PL
            print(msg.format(offset=offset, count=packages_thirdparty))

    if show_items in ("all", "unknown"):
        packages_unknown = len(package_lists["unknown"])
        if packages_unknown or always_show:
            print(
                messages.SS_SUMMARY_UNAVAILABLE.format(
                    offset=offset,
                    count=packages_unknown,
                    plural="s" if packages_unknown > 1 else "",
                )
            )

    print("")


def _print_interim_release_support():
    series = get_platform_info()["series"]
    eol_date = get_distro_info(series).eol
    date = "{}/{}".format(str(eol_date.month), str(eol_date.year))
    print(messages.SS_INTERIM_SUPPORT.format(date=date))
    print("")


def _print_lts_support():
    series = get_platform_info()["series"]
    if is_supported(series):
        eol_date = get_distro_info(series).eol
        print(messages.SS_LTS_SUPPORT.format(date=str(eol_date.year)))
    else:
        print(messages.SS_NO_SECURITY_COVERAGE)


def _print_service_support(
    service: str,
    repository: str,
    service_status: ApplicationStatus,
    service_applicability: ApplicabilityStatus,
    installed_updates: int,
    available_updates: int,
    is_attached: bool,
):
    series = get_platform_info()["series"]
    eol_date_esm = get_distro_info(series).eol_esm
    if service_status == ApplicationStatus.ENABLED:
        message = messages.SS_SERVICE_ENABLED.format(
            repository=repository,
            service=service,
            year=str(eol_date_esm.year),
        )
        if installed_updates:
            message += messages.SS_SERVICE_ENABLED_COUNTS.format(
                updates=installed_updates,
                plural="" if installed_updates == 1 else "s",
            )
        print(message)
    else:
        message = messages.SS_SERVICE_ADVERTISE.format(
            service=service,
            repository=repository,
            year=str(eol_date_esm.year),
        )
        if available_updates:
            message += messages.SS_SERVICE_ADVERTISE_COUNTS.format(
                updates=available_updates,
                plural="s" if available_updates > 1 else "",
            )
        else:
            message += "."
        print(message)
        if (
            is_attached
            and service_applicability == ApplicabilityStatus.APPLICABLE
        ):
            print(messages.SS_SERVICE_COMMAND.format(service=service))

    print("")


def _print_package_list(
    package_list: List[apt.package.Package],
    reference_list: List[apt.package.Package] = [],
):
    package_string = ""

    package_names = [package.name for package in package_list]
    reference_names = [package.name for package in reference_list]

    for package_name in package_names:
        if package_name in reference_names:
            package_string += (
                "{bold}{package_name}{end_bold}".format(
                    bold=messages.TxtColor.BOLD,
                    package_name=package_name,
                    end_bold=messages.TxtColor.ENDC,
                )
                + " "
            )
        else:
            package_string += package_name + " "
    print(
        "\n".join(
            textwrap.wrap(
                package_string,
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    )
    print("")
    hint_package_list = reference_names if reference_names else package_names
    print(messages.SS_POLICY_HINT.format(package=choice(hint_package_list)))


def security_status(cfg: UAConfig):
    esm_infra_status = ESMInfraEntitlement(cfg).application_status()[0]
    esm_infra_applicability = ESMInfraEntitlement(cfg).applicability_status()[
        0
    ]
    esm_apps_status = ESMAppsEntitlement(cfg).application_status()[0]
    esm_apps_applicability = ESMAppsEntitlement(cfg).applicability_status()[0]

    series = get_platform_info()["series"]
    is_lts = is_current_series_lts()
    is_attached = get_ua_info(cfg)["attached"]

    packages_by_origin = get_installed_packages_by_origin()
    security_upgradable_versions_infra = filter_security_updates(
        packages_by_origin["main"]
        + packages_by_origin["restricted"]
        + packages_by_origin["esm-infra"],
    )["esm-infra"]

    security_upgradable_versions_apps = filter_security_updates(
        packages_by_origin["universe"]
        + packages_by_origin["multiverse"]
        + packages_by_origin["esm-apps"],
    )["esm-apps"]

    _print_package_summary(packages_by_origin)

    print(messages.SS_HELP_CALL)
    print("")

    if not is_lts:
        if is_supported(series):
            _print_interim_release_support()
        print(messages.SS_NO_INTERIM_PRO_SUPPORT)
        return

    if esm_infra_status == ApplicationStatus.DISABLED:
        _print_lts_support()

    not_attached = ""
    if not is_attached:
        not_attached = " NOT"
    print(messages.SS_IS_ATTACHED.format(not_attached=not_attached))
    print("")

    _print_service_support(
        service="esm-infra",
        repository="Main/Restricted",
        service_status=esm_infra_status,
        service_applicability=esm_infra_applicability,
        installed_updates=len(packages_by_origin["esm-infra"]),
        available_updates=len(security_upgradable_versions_infra),
        is_attached=is_attached,
    )

    if (
        packages_by_origin["universe"]
        or packages_by_origin["multiverse"]
        or packages_by_origin["esm-apps"]
    ):
        _print_service_support(
            service="esm-apps",
            repository="Universe/Multiverse",
            service_status=esm_apps_status,
            service_applicability=esm_apps_applicability,
            installed_updates=len(packages_by_origin["esm-apps"]),
            available_updates=len(security_upgradable_versions_apps),
            is_attached=is_attached,
        )

    if not is_attached:
        print(messages.SS_LEARN_MORE)


def list_third_party_packages():
    packages_by_origin = get_installed_packages_by_origin()
    third_party_packages = packages_by_origin["third-party"]

    _print_package_summary(
        packages_by_origin, show_items="third-party", always_show=True
    )

    if third_party_packages:
        print(messages.SS_THIRD_PARTY)

        print("")
        print("Packages:")
        _print_package_list(third_party_packages)
    else:
        print(messages.SS_NO_THIRD_PARTY)


def list_unavailable_packages():
    packages_by_origin = get_installed_packages_by_origin()
    unknown_packages = packages_by_origin["unknown"]

    _print_package_summary(
        packages_by_origin, show_items="unknown", always_show=True
    )

    if unknown_packages:
        print(messages.SS_UNAVAILABLE)
        print("")

        print("Packages:")
        _print_package_list(unknown_packages)

    else:
        print(messages.SS_NO_UNAVAILABLE)


def list_esm_infra_packages(cfg):
    packages_by_origin = get_installed_packages_by_origin()
    infra_packages = packages_by_origin["esm-infra"]
    mr_packages = packages_by_origin["main"] + packages_by_origin["restricted"]

    all_infra_packages = infra_packages + mr_packages

    infra_updates = set()
    security_upgradable_versions = filter_security_updates(all_infra_packages)[
        "esm-infra"
    ]
    for update, _ in security_upgradable_versions:
        infra_updates.add(update.package)

    series = get_platform_info()["series"]
    is_lts = is_current_series_lts()

    esm_infra_status = ESMInfraEntitlement(cfg).application_status()[0]
    esm_infra_applicability = ESMInfraEntitlement(cfg).applicability_status()[
        0
    ]

    _print_package_summary(
        packages_by_origin, show_items="esm-infra", always_show=True
    )

    if not is_lts:
        if is_supported(series):
            _print_interim_release_support()
        print(messages.SS_NO_INTERIM_PRO_SUPPORT)
        return

    if esm_infra_status == ApplicationStatus.DISABLED:
        _print_lts_support()
        print("")

    _print_service_support(
        service="esm-infra",
        repository="Main/Restricted",
        service_status=esm_infra_status,
        service_applicability=esm_infra_applicability,
        installed_updates=len(infra_packages),
        available_updates=len(infra_updates),
        is_attached=False,  # don't care about the `enable` message
    )
    print(messages.SS_SERVICE_HELP.format(service="esm-infra"))
    print("")

    if not is_supported(series):
        print(messages.SS_BOLD_PACKAGES.format(service="esm-infra"))
        print("Packages:")
        _print_package_list(all_infra_packages, list(infra_updates))


def list_esm_apps_packages(cfg):
    packages_by_origin = get_installed_packages_by_origin()
    apps_packages = packages_by_origin["esm-apps"]
    um_packages = (
        packages_by_origin["universe"] + packages_by_origin["multiverse"]
    )

    all_apps_packages = apps_packages + um_packages

    apps_updates = set()
    security_upgradable_versions = filter_security_updates(all_apps_packages)[
        "esm-apps"
    ]
    for update, _ in security_upgradable_versions:
        apps_updates.add(update.package)

    is_lts = is_current_series_lts()

    esm_apps_status = ESMAppsEntitlement(cfg).application_status()[0]
    esm_apps_applicability = ESMAppsEntitlement(cfg).applicability_status()[0]

    _print_package_summary(
        packages_by_origin, show_items="esm-apps", always_show=True
    )

    if not is_lts:
        print(messages.SS_NO_INTERIM_PRO_SUPPORT)
        return

    _print_service_support(
        service="esm-apps",
        repository="Universe/Multiverse",
        service_status=esm_apps_status,
        service_applicability=esm_apps_applicability,
        installed_updates=len(apps_packages),
        available_updates=len(apps_updates),
        is_attached=False,  # don't care about the `enable` message
    )
    print(messages.SS_SERVICE_HELP.format(service="esm-apps"))
    print("")

    if all_apps_packages:
        print(messages.SS_BOLD_PACKAGES.format(service="esm-apps"))
        print("Packages:")
        _print_package_list(all_apps_packages, list(apps_updates))
