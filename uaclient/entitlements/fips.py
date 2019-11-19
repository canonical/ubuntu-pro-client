from uaclient.entitlements import repo
from uaclient import apt, status, util

try:
    from typing import Dict, List, Set, Tuple  # noqa
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class FIPSCommonEntitlement(repo.RepoEntitlement):

    repo_pin_priority = 1001
    fips_required_packages = frozenset({"fips-initramfs", "linux-fips"})
    fips_packages = {
        "libssl1.0.0": {"libssl1.0.0-hmac"},
        "openssh-client": {"openssh-client-hmac"},
        "openssh-server": {"openssh-server-hmac"},
        "openssl": set(),
        "strongswan": {"strongswan-hmac"},
    }  # type: Dict[str, Set[str]]

    @property
    def packages(self) -> "List[str]":
        packages = list(self.fips_required_packages)
        installed_packages = apt.get_installed_packages()
        for pkg_name, extra_pkgs in self.fips_packages.items():
            if pkg_name in installed_packages:
                packages.append(pkg_name)
                packages.extend(extra_pkgs)
        return packages

    def application_status(self) -> "Tuple[status.ApplicationStatus, str]":
        super_status, super_msg = super().application_status()
        if super_status != status.ApplicationStatus.ENABLED:
            return super_status, super_msg
        running_kernel = util.get_platform_info()["kernel"]
        if running_kernel.endswith("-fips"):
            return super_status, super_msg
        return (
            status.ApplicationStatus.ENABLED,
            "Reboot to FIPS kernel required",
        )

    def disable(self, silent: bool = False) -> bool:
        """FIPS cannot be disabled, so simply display a message to the user"""
        if not silent:
            print("Warning: no option to disable {}".format(self.title))
        return False

    def _cleanup(self) -> None:
        """FIPS can't be cleaned up automatically, so don't do anything"""
        pass


class FIPSEntitlement(FIPSCommonEntitlement):

    help_doc_url = "https://ubuntu.com/fips"
    name = "fips"
    title = "FIPS"
    description = "NIST-certified FIPS modules"
    messaging = {
        "post_enable": ["A reboot is required to complete the install"]
    }
    origin = "UbuntuFIPS"
    repo_key_file = "ubuntu-fips-keyring.gpg"
    static_affordances = (
        ("Cannot install FIPS on a container", util.is_container, False),
    )


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = "fips-updates"
    title = "FIPS Updates"
    messaging = {
        "post_enable": [
            "FIPS Updates configured and pending, please reboot to make"
            " active."
        ]
    }
    origin = "UbuntuFIPSUpdates"
    description = "Uncertified security updates to FIPS modules"
    repo_key_file = "ubuntu-fips-updates-keyring.gpg"
    static_affordances = (
        (
            "Cannot install FIPS Updates on a container",
            util.is_container,
            False,
        ),
    )
