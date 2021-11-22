import logging
import os
import time
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError

from uaclient import actions, config, lock, util
from uaclient.clouds import AutoAttachCloudInstance

LOG = logging.getLogger("ua.clouds.gcp")

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
LAST_ETAG = "&last_etag={}"

DMI_PRODUCT_NAME = "/sys/class/dmi/id/product_name"
GCP_PRODUCT_NAME = "Google Compute Engine"

GCP_LICENSES = {
    "xenial": "8045211386737108299",
    "bionic": "6022427724719891830",
    "focal": "599959289349842382",
}


class UAAutoAttachGCPInstance(AutoAttachCloudInstance):
    def __init__(self, cfg: config.UAConfig):
        super().__init__(cfg)
        # store ETAG
        # https://cloud.google.com/compute/docs/metadata/querying-metadata#etags  # noqa
        self.etag = None  # type: Optional[str]

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

    def is_license_present(self) -> bool:
        """
        Checks list of licenses from the GCP metadata.
        """
        series = util.get_platform_info()["series"]
        if series not in GCP_LICENSES:
            return False

        licenses, headers = util.readurl(
            LICENSES_URL, headers={"Metadata-Flavor": "Google"}
        )
        license_ids = [license["id"] for license in licenses]
        self.etag = headers.get("ETag", None)

        return GCP_LICENSES[series] in license_ids

    def should_poll_for_license(self) -> bool:
        series = util.get_platform_info()["series"]
        if series not in GCP_LICENSES:
            LOG.info("This series isn't supported for GCP auto-attach.")
            return False

        return True

    def get_polling_fn(self) -> Optional[Callable]:
        def gcp_polling_fn():
            LOG.debug("gcp_polling_fn started")
            done = False
            while not done:
                license_ids = []
                try:
                    # TODO: should we have a timeout? configurable? default?
                    # https://cloud.google.com/compute/docs/metadata/querying-metadata#settingtimeouts  # noqa
                    url = LICENSES_URL + WAIT_FOR_CHANGE
                    if self.etag:
                        url += LAST_ETAG.format(self.etag)
                    licenses, headers = util.readurl(
                        url, headers={"Metadata-Flavor": "Google"}
                    )
                    license_ids = [
                        license.get("id", "") for license in licenses
                    ]
                    self.etag = headers.get("ETag", None)
                except HTTPError as e:
                    LOG.error(e)
                    if e.code == 400:
                        LOG.debug("Got 400 from metadata. Cancelling polling")
                        done = True
                    else:
                        LOG.debug("waiting 10 minutes before trying again")
                        time.sleep(600)
                except Exception as e:
                    LOG.exception(e)
                    LOG.debug("waiting 10 minutes before trying again")
                    time.sleep(600)

                if license_ids:
                    series = util.get_platform_info()["series"]
                    if GCP_LICENSES[series] in license_ids:
                        LOG.info("pro license found. auto-attaching")
                        try:
                            with lock.SpinLock(
                                cfg=self.cfg,
                                lock_holder="ua.clouds.gcp.gcp_polling_fn",
                            ):
                                actions.auto_attach(self.cfg, self)
                        except Exception as e:
                            lock.clear_lock_file_if_present()
                            # TODO: should we retry here?
                            LOG.exception(e)
                        done = True

            LOG.debug("gcp_polling_fn completed")

        return gcp_polling_fn
