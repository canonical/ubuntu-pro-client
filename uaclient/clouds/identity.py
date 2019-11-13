import json

from uaclient import exceptions
from uaclient import clouds
from uaclient import status
from uaclient import util

CLOUDINIT_RESULT_FILE = "/var/lib/cloud/data/result.json"


@util.retry(FileNotFoundError, [1, 2])
def get_cloud_type_from_result_file(result_file=CLOUDINIT_RESULT_FILE) -> str:
    result = json.loads((util.load_file(result_file)))
    dsname = result["v1"]["datasource"].split()[0].lower()
    return dsname.replace("datasource", "")


def get_cloud_type() -> str:
    if util.which("cloud-id"):
        # Present in cloud-init on >= Xenial
        out, _err = util.subp(["cloud-id"])
        return out.strip()
    try:
        return get_cloud_type_from_result_file()
    except FileNotFoundError:
        pass
    return ""


def cloud_instance_factory() -> clouds.UAPremiumCloudInstance:
    from uaclient.clouds import aws

    cloud_instance_map = {
        "aws": aws.UAPremiumAWSInstance,
        "ec2": aws.UAPremiumAWSInstance,
    }

    cloud_type = get_cloud_type()
    if not cloud_type:
        raise exceptions.UserFacingError(
            "Unable to determine premium image platform support\n"
            "For more information see: https://ubuntu.com/advantage"
        )
    cls = cloud_instance_map.get(cloud_type)
    if not cls:
        raise exceptions.UserFacingError(status.MESSAGE_UNSUPPORTED_PREMIUM)
    instance = cls()
    if not instance.is_viable:
        raise exceptions.UserFacingError(status.MESSAGE_UNSUPPORTED_PREMIUM)
    return instance
