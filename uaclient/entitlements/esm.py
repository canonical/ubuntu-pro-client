from uaclient.entitlements import repo
from uaclient import util

try:
    from typing import Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class ESMBaseEntitlement(repo.RepoEntitlement):
    help_doc_url = "https://ubuntu.com/security/esm"


class ESMAppsEntitlement(ESMBaseEntitlement):
    origin = "UbuntuESMApps"
    name = "esm-apps"
    title = "ESM Apps"
    description = "UA Apps: Extended Security Maintenance (ESM)"
    repo_key_file = "ubuntu-advantage-esm-apps.gpg"

    @property
    def repo_pin_priority(self) -> "Optional[str]":
        """Only Xenial esm-apps should perform repo pinning"""
        if "xenial" == util.get_platform_info()["series"]:
            return "never"
        return None  # No pinning on >= trusty

    @property
    def disable_apt_auth_only(self) -> bool:
        """Only xenial esm-apps should remove apt auth files upon disable"""
        return bool("xenial" == util.get_platform_info()["series"])


class ESMInfraEntitlement(ESMBaseEntitlement):
    name = "esm-infra"
    origin = "UbuntuESM"
    title = "ESM Infra"
    description = "UA Infra: Extended Security Maintenance (ESM)"
    repo_key_file = "ubuntu-advantage-esm-infra-trusty.gpg"

    @property
    def repo_pin_priority(self) -> "Optional[str]":
        """Xenial and Trusty esm-infra should perform repo pinning"""
        if util.get_platform_info()["series"] in ("trusty", "xenial"):
            return "never"
        return None  # No pinning on >= bionic

    @property
    def disable_apt_auth_only(self) -> bool:
        """Only trusty esm-infra should remove apt auth files upon disable"""
        return bool(util.get_platform_info()["series"] in ("trusty", "xenial"))
