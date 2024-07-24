from uaclient import apt, snap
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue


class PackageManifestResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "manifest_data",
            StringDataValue,
            doc=(
                "Manifest of ``apt`` and ``snap`` packages installed on the"
                " system"
            ),
        ),
    ]

    def __init__(self, manifest_data: str):
        self.manifest_data = manifest_data


# The return class was once called PackageManifestResults
# We are keeping compatibility
PackageManifestResults = PackageManifestResult


def package_manifest() -> PackageManifestResult:
    return _package_manifest(UAConfig())


def _package_manifest(cfg: UAConfig) -> PackageManifestResult:
    """
    This endpoint returns the status of installed packages (``apt`` and
    ``snap``), formatted as a manifest file (i.e., ``package_name\\tversion``).
    """
    manifest = ""
    apt_pkgs = apt.get_installed_packages()
    for apt_pkg in apt_pkgs:
        arch = "" if apt_pkg.arch == "all" else ":" + apt_pkg.arch
        manifest += "{}{}\t{}\n".format(apt_pkg.name, arch, apt_pkg.version)

    pkgs = snap.get_installed_snaps()
    for pkg in pkgs:
        manifest += "snap:{name}\t{channel}\t{revision}\n".format(
            name=pkg.name,
            channel=pkg.channel,
            revision=pkg.revision,
        )

    return PackageManifestResult(manifest_data=manifest)


endpoint = APIEndpoint(
    version="v1",
    name="Packages",
    fn=_package_manifest,
    options_cls=None,
)

_doc = {
    "introduced_in": "27.12",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.security.package_manifest.v1 import package_manifest

result = package_manifest()
""",
    "result_class": PackageManifestResult,
    "exceptions": [],
    "example_cli": "pro api u.security.package_manifest.v1",
    "example_json": """
{
    "package_manifest":"package1\\t1.0\\npackage2\\t2.3\\n"
}
""",
}
