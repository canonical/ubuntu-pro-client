from uaclient import messages
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.errors import APIError
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.version import get_version


class VersionError(APIError):
    _formatted_msg = messages.E_API_VERSION_ERROR


class VersionResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "installed_version",
            StringDataValue,
            doc="The current installed version",
        ),
    ]

    def __init__(self, *, installed_version: str):
        self.installed_version = installed_version


def version() -> VersionResult:
    return _version(UAConfig())


def _version(cfg: UAConfig) -> VersionResult:
    """
    This endpoint shows the installed Pro Client version.
    """
    try:
        version = get_version()
    except Exception as e:
        raise VersionError(error_msg=str(e))
    return VersionResult(installed_version=version)


endpoint = APIEndpoint(
    version="v1",
    name="Version",
    fn=_version,
    options_cls=None,
)

_doc = {
    "introduced_in": "27.11",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.version.v1 import version

result = version()
""",
    "result_class": VersionResult,
    "exceptions": [
        (VersionError, "Raised if the Client cannot determine the version.")
    ],
    "example_cli": "pro api u.pro.version.v1",
    "example_json": """
{
    "installed_version": "32.3~24.04"
}
""",
}
