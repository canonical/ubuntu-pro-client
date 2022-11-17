from uaclient import apt, snap
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue


class PackageManifestResult(DataObject, AdditionalInfo):
    fields = [
        Field("manifest_data", StringDataValue),
    ]

    def __init__(self, manifest_data: str):
        self.manifest_data = manifest_data


# The return class was once called PackageManifestResults
# We are keeping compatibility
PackageManifestResults = PackageManifestResult


def package_manifest() -> PackageManifestResult:
    return _package_manifest(UAConfig())


def _package_manifest(cfg: UAConfig) -> PackageManifestResult:
    """Returns the status of installed packages (apt and snap packages)
    Returns a string in manifest format i.e. package_name\tversion
    """
    manifest = ""
    apt_pkgs = apt.get_installed_packages()
    for apt_pkg in apt_pkgs:
        arch = "" if apt_pkg.arch == "all" else ":" + apt_pkg.arch
        manifest += "{}{}\t{}\n".format(apt_pkg.name, arch, apt_pkg.version)

    pkgs = snap.get_installed_snaps()
    for pkg in pkgs:
        manifest += "snap:{name}\t{tracking}\t{rev}\n".format(
            name=pkg.name,
            tracking=pkg.tracking,
            rev=pkg.rev,
        )

    return PackageManifestResult(manifest_data=manifest)


endpoint = APIEndpoint(
    version="v1",
    name="Packages",
    fn=_package_manifest,
    options_cls=None,
)
