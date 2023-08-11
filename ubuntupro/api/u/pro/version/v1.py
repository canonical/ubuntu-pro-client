from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.errors import APIError
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue
from uaclient.version import get_version


class VersionError(APIError):
    pass


class VersionResult(DataObject, AdditionalInfo):
    fields = [
        Field("installed_version", StringDataValue),
    ]

    def __init__(self, *, installed_version: str):
        self.installed_version = installed_version


def version() -> VersionResult:
    return _version(UAConfig())


def _version(cfg: UAConfig) -> VersionResult:
    try:
        version = get_version()
    except Exception as e:
        raise VersionError(msg=str(e), msg_code="unable-to-determine-version")
    return VersionResult(installed_version=version)


endpoint = APIEndpoint(
    version="v1",
    name="Version",
    fn=_version,
    options_cls=None,
)
