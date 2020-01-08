import os

from urllib.error import HTTPError

from uaclient.clouds import AutoAttachCloudInstance
from uaclient import util


IMDS_BASE_URL = "http://169.254.169.254/metadata/"
IMDS_URLS = {
    "pkcs7": IMDS_BASE_URL + "attested/document?api-version=2019-06-04",
    "compute": IMDS_BASE_URL + "instance/compute?api-version=2019-06-04",
}

SYS_HYPERVISOR_PRODUCT_UUID = "/sys/hypervisor/uuid"
DMI_CHASSIS_ASSET_TAG = "/sys/class/dmi/id/chassis_asset_tag"
AZURE_CHASSIS_ASSET_TAG = "7783-7084-3265-9085-8269-3286-77"


class UAAutoAttachAzureInstance(AutoAttachCloudInstance):

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(HTTPError, retry_sleeps=[1, 2, 5])
    def identity_doc(self):
        response = {}
        for key, url in sorted(IMDS_URLS.items()):
            url_response, _headers = util.readurl(
                url, headers={"Metadata": True}
            )
            if key == "pkcs7":
                response[key] = url_response["signature"]
            else:
                response[key] = url_response
        return response

    @property
    def cloud_type(self):
        return "azure"

    @property
    def is_viable(self):
        """This machine is a viable AzureInstance"""
        try:
            chassis_asset_tag = util.load_file(DMI_CHASSIS_ASSET_TAG)
            if AZURE_CHASSIS_ASSET_TAG == chassis_asset_tag.strip():
                return True
        except FileNotFoundError:
            # SYS_HYPERVISOR_PRODUCT_UUID isn't present on all EC2 instance
            # types, fall through
            pass
        if os.path.exists("/var/lib/cloud/seed/azure/ovf-env.xml"):
            return True
        return False
