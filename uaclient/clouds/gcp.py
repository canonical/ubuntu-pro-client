import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional  # noqa: F401
from urllib.error import HTTPError

from uaclient import exceptions, messages, system, util
from uaclient.clouds import AutoAttachCloudInstance

LOG = logging.getLogger("pro.clouds.gcp")

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

GCP_LICENSES = {
    "xenial": "8045211386737108299",
    "bionic": "6022427724719891830",
    "focal": "599959289349842382",
    "jammy": "2592866803419978320",
}


class UAAutoAttachGCPInstance(AutoAttachCloudInstance):
    def __init__(self):
        # store ETAG
        # https://cloud.google.com/compute/docs/metadata/querying-metadata#etags  # noqa
        self.etag = None  # type: Optional[str]

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(exceptions.GCPProAccountError, retry_sleeps=[0.5, 1, 1])
    def identity_doc(self) -> Dict[str, Any]:
        try:
            headers = {"Metadata-Flavor": "Google"}
            url_response, _headers = util.readurl(
                TOKEN_URL, headers=headers, timeout=1
            )
        except HTTPError as e:
            body = getattr(e, "body", None)
            error_desc = None
            if body:
                try:
                    error_details = json.loads(
                        body, cls=util.DatetimeAwareJSONDecoder
                    )
                except ValueError:
                    error_details = None
                if error_details:
                    error_desc = error_details.get("error_description", None)
            msg = error_desc if error_desc else e.reason
            msg_code = None
            if error_desc and "service account" in error_desc.lower():
                msg = messages.GCP_SERVICE_ACCT_NOT_ENABLED_ERROR.msg.format(
                    error_msg=msg
                )
                msg_code = messages.GCP_SERVICE_ACCT_NOT_ENABLED_ERROR.name
            raise exceptions.GCPProAccountError(
                msg=msg, msg_code=msg_code, code=getattr(e, "code", 0)
            )
        return {"identityToken": url_response}

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
        series = system.get_platform_info()["series"]
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

        try:
            licenses, headers = util.readurl(
                url, headers={"Metadata-Flavor": "Google"}
            )
        except HTTPError as e:
            LOG.error(e)
            if e.code == 400:
                raise exceptions.CancelProLicensePolling()
            else:
                raise exceptions.DelayProLicensePolling()
        license_ids = [license["id"] for license in licenses]
        self.etag = headers.get("ETag", None)

        series = system.get_platform_info()["series"]
        return GCP_LICENSES.get(series) in license_ids
