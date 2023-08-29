import logging
import os
from typing import Any, Dict

from uaclient import exceptions, http, system, util
from uaclient.clouds import AutoAttachCloudInstance

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

IMDS_BASE_URL = "http://169.254.169.254/metadata/"

API_VERSION = "2020-09-01"  # Needed to get subscription ID in attested data
IMDS_URLS = {
    "pkcs7": IMDS_BASE_URL + "attested/document?api-version=" + API_VERSION,
    "compute": IMDS_BASE_URL + "instance/compute?api-version=" + API_VERSION,
}

DMI_CHASSIS_ASSET_TAG = "/sys/class/dmi/id/chassis_asset_tag"
AZURE_OVF_ENV_FILE = "/var/lib/cloud/seed/azure/ovf-env.xml"
AZURE_CHASSIS_ASSET_TAG = "7783-7084-3265-9085-8269-3286-77"
AZURE_PRO_LICENSE_TYPE = "UBUNTU_PRO"


class UAAutoAttachAzureInstance(AutoAttachCloudInstance):
    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(exceptions.CloudMetadataError, retry_sleeps=[1, 1, 1])
    def identity_doc(self) -> Dict[str, Any]:
        responses = {}
        for key, url in sorted(IMDS_URLS.items()):
            response = http.readurl(
                url, headers={"Metadata": "true"}, timeout=1
            )
            if response.code != 200:
                raise exceptions.CloudMetadataError(
                    code=response.code, body=response.body
                )
            if key == "pkcs7":
                responses[key] = response.json_dict["signature"]
            else:
                responses[key] = response.json_dict
        return responses

    @property
    def cloud_type(self) -> str:
        return "azure"

    @property
    def is_viable(self) -> bool:
        """This machine is a viable AzureInstance"""
        if os.path.exists(DMI_CHASSIS_ASSET_TAG):
            chassis_asset_tag = system.load_file(DMI_CHASSIS_ASSET_TAG)
            if AZURE_CHASSIS_ASSET_TAG == chassis_asset_tag.strip():
                return True
        return os.path.exists(AZURE_OVF_ENV_FILE)

    def should_poll_for_pro_license(self) -> bool:
        # Azure will make sure it is on all supported versions
        return True

    def is_pro_license_present(self, *, wait_for_change: bool) -> bool:
        if wait_for_change:
            raise exceptions.CancelProLicensePolling()

        url = IMDS_URLS.get("compute", "")
        try:
            response = http.readurl(url, headers={"Metadata": "true"})
        except OSError as e:
            LOG.error(e)
            raise exceptions.CancelProLicensePolling()

        if response.code != 200:
            LOG.error(response.body)
            raise exceptions.CancelProLicensePolling()

        return response.json_dict.get("licenseType") == AZURE_PRO_LICENSE_TYPE
