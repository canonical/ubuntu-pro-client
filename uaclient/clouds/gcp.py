import os

from urllib.error import HTTPError

try:
    from typing import Any, Dict  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

from uaclient.clouds import AutoAttachCloudInstance
from uaclient import util


TOKEN_URL = (
    "http://metadata/computeMetadata/v1/instance/service-accounts/"
    "default/identity?audience=contracts.canonical.com&"
    "format=full&licenses=TRUE"
)

DMI_PRODUCT_NAME = "/sys/class/dmi/id/product_name"
GCP_PRODUCT_NAME = "Google Compute Engine"


class UAAutoAttachGCPInstance(AutoAttachCloudInstance):

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(HTTPError, retry_sleeps=[1, 2, 5])
    def identity_doc(self) -> "Dict[str, Any]":
        url_response, _headers = util.readurl(
            TOKEN_URL, headers={"Metadata-Flavor": "Google"}
        )
        return {"identityToken": url_response}

    @property
    def cloud_type(self) -> str:
        return "gcp"

    @property
    def is_viable(self) -> bool:
        """This machine is a viable GCPInstance"""
        if os.path.exists(DMI_PRODUCT_NAME):
            product_name = util.load_file(DMI_PRODUCT_NAME)
            if GCP_PRODUCT_NAME == product_name.strip():
                return True

        return False
