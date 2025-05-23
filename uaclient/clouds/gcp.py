import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional  # noqa: F401

from uaclient import exceptions, http, secret_manager, system, util
from uaclient.clouds import PublicCloudAutoAttachInstance

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

TOKEN_URL = (
    "http://metadata/computeMetadata/v1/instance/service-accounts/"
    "default/identity?audience=contracts.canonical.com&"
    "format=full&licenses=TRUE"
)
LICENSES_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/licenses/"
    "?recursive=true"
)
WAIT_FOR_CHANGE = "&wait_for_change=true"
LAST_ETAG = "&last_etag={etag}"

DMI_PRODUCT_NAME = "/sys/class/dmi/id/product_name"
GCP_PRODUCT_NAME = "Google Compute Engine"

GCP_LICENSES = {  # Base [0], Minimal [1]
    "xenial": ["8045211386737108299"],
    "bionic": ["6022427724719891830", "7427070211152946628"],
    "focal": ["599959289349842382", "7818678586103571931"],
    "jammy": ["2592866803419978320", "160084055690847662"],
    "noble": ["2176054482269786025", "4168323874790319525"],
}


class GCPAutoAttachInstance(PublicCloudAutoAttachInstance):
    def __init__(self):
        # store ETAG
        # https://cloud.google.com/compute/docs/metadata/querying-metadata#etags  # noqa
        self.etag = None  # type: Optional[str]

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(exceptions.CloudMetadataError, retry_sleeps=[0.5, 1, 1])
    def identity_doc(self) -> Dict[str, Any]:
        response = http.readurl(
            TOKEN_URL, headers={"Metadata-Flavor": "Google"}, timeout=1
        )
        if response.code == 200:
            secret_manager.secrets.add_secret(response.body)
            return {"identityToken": response.body}

        error_desc = response.json_dict.get("error_description")
        if error_desc and "service account" in error_desc.lower():
            raise exceptions.GCPServiceAccountError(
                status_code=response.code, error_msg=error_desc
            )
        raise exceptions.CloudMetadataError(
            code=response.code, body=response.body
        )

    @property
    def cloud_type(self) -> str:
        return "gcp"

    @property
    def is_viable(self) -> bool:
        """This machine is a viable GCPInstance"""
        if os.path.exists(DMI_PRODUCT_NAME):
            product_name = system.load_file(DMI_PRODUCT_NAME)
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

    def should_poll_for_pro_license(self) -> bool:
        series = system.get_release_info().series
        if series not in GCP_LICENSES:
            LOG.info("This series isn't supported for GCP auto-attach.")
            return False
        return True

    def is_pro_license_present(self, *, wait_for_change: bool) -> bool:
        url = LICENSES_URL

        if wait_for_change:
            url += WAIT_FOR_CHANGE
            if self.etag:
                url += LAST_ETAG.format(etag=self.etag)

        response = http.readurl(url, headers={"Metadata-Flavor": "Google"})
        if response.code == 200:
            license_ids = [license["id"] for license in response.json_list]
            self.etag = response.headers.get("etag")
            series = system.get_release_info().series
            for lic in GCP_LICENSES.get(series, []):
                if lic in license_ids:
                    return True
            return False

        LOG.error(response.body)
        if response.code == 400:
            raise exceptions.CancelProLicensePolling()
        else:
            raise exceptions.DelayProLicensePolling()
