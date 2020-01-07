from urllib.error import HTTPError

from uaclient.clouds import AutoAttachCloudInstance
from uaclient import util


IMDS_URL = "http://169.254.169.254/latest/dynamic/instance-identity/pkcs7"
SYS_HYPERVISOR_PRODUCT_UUID = "/sys/hypervisor/uuid"
DMI_PRODUCT_SERIAL = "/sys/class/dmi/id/product_serial"
DMI_PRODUCT_UUID = "/sys/class/dmi/id/product_uuid"


class UAAutoAttachAWSInstance(AutoAttachCloudInstance):

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(HTTPError, retry_sleeps=[1, 2, 5])
    def identity_doc(self):
        response, _headers = util.readurl(IMDS_URL)
        return response

    @property
    def cloud_type(self):
        return "aws"

    @property
    def is_viable(self):
        """This machine is a viable AWSInstance"""
        try:
            hypervisor_uuid = util.load_file(SYS_HYPERVISOR_PRODUCT_UUID)
            if "ec2" == hypervisor_uuid[0:3]:
                return True
        except FileNotFoundError:
            # SYS_HYPERVISOR_PRODUCT_UUID isn't present on all EC2 instance
            # types, fall through
            pass
        # Both DMI product_uuid and product_serial start with 'ec2'
        dmi_uuid = util.load_file(DMI_PRODUCT_UUID).lower()
        dmi_serial = util.load_file(DMI_PRODUCT_SERIAL).lower()
        if "ec2" == dmi_uuid[0:3] == dmi_serial[0:3]:
            return True
        return False
