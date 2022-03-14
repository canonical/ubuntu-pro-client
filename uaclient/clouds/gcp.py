import base64
import json
import os
from typing import Any, Dict, List
from urllib.error import HTTPError

from uaclient import util
from uaclient.clouds import AutoAttachCloudInstance

TOKEN_URL = (
    "http://metadata/computeMetadata/v1/instance/service-accounts/"
    "default/identity?audience=contracts.canonical.com&"
    "format=full&licenses=TRUE"
)

DMI_PRODUCT_NAME = "/sys/class/dmi/id/product_name"
GCP_PRODUCT_NAME = "Google Compute Engine"

GCP_LICENSES = {
    "xenial": "8045211386737108299",
    "bionic": "6022427724719891830",
    "focal": "599959289349842382",
    "jammy": "2592866803419978320",
}


class UAAutoAttachGCPInstance(AutoAttachCloudInstance):

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(HTTPError, retry_sleeps=[1, 2, 5])
    def identity_doc(self) -> Dict[str, Any]:
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

    def get_licenses_from_identity(self) -> List[str]:
        """Get a list of licenses from the GCP metadata.

        Instance identity token (jwt) carries a list of licenses
        associated with the instance itself.

        Returns an empty list if licenses are not present in the metadata.
        """
        token = self.identity_doc["identityToken"]
        identity = base64.urlsafe_b64decode(token.split(".")[1] + "===")
        identity_dict = json.loads(identity.decode("utf-8"))
        return (
            identity_dict.get("google", {})
            .get("compute_engine", {})
            .get("license_id", [])
        )
