import json
import logging
import os

from uaclient import exceptions
from uaclient import clouds
from uaclient import status
from uaclient import util
from uaclient.config import apply_config_settings_override

try:
    from typing import Dict, Optional, Type  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

# Needed for Trusty-only
CLOUDINIT_RESULT_FILE = "/var/lib/cloud/data/result.json"
CLOUDINIT_INSTANCE_ID_FILE = "/var/lib/cloud/data/instance-id"


# Mapping of datasource names to cloud-id responses. Trusty compat with Xenial+
DATASOURCE_TO_CLOUD_ID = {"azurenet": "azure", "ec2": "aws", "gce": "gcp"}

CLOUD_TYPE_TO_TITLE = {
    "aws": "AWS",
    "aws-china": "AWS China",
    "aws-gov": "AWS Gov",
    "azure": "Azure",
    "gcp": "GCP",
}

PRO_CLOUDS = ["aws", "azure", "gcp"]


def get_instance_id(
    _iid_file: str = CLOUDINIT_INSTANCE_ID_FILE
) -> "Optional[str]":
    """Query cloud instance-id from cmdline or CLOUDINIT_INSTANCE_ID_FILE"""
    if "trusty" != util.get_platform_info()["series"]:
        # Present in cloud-init on >= Xenial
        out, _err = util.subp(["cloud-init", "query", "instance_id"])
        return out.strip()
    if os.path.exists(_iid_file):
        return util.load_file(_iid_file)
    logging.warning(
        "Unable to determine current instance-id from %s", _iid_file
    )
    return None


def get_cloud_type_from_result_file(
    result_file: str = CLOUDINIT_RESULT_FILE
) -> str:
    result = json.loads(util.load_file(result_file))
    dsname = result["v1"]["datasource"].split()[0].lower()
    dsname = dsname.replace("datasource", "")
    return DATASOURCE_TO_CLOUD_ID.get(dsname, dsname)


@apply_config_settings_override("cloud_type")
def get_cloud_type() -> "Optional[str]":
    if util.which("cloud-id"):
        # Present in cloud-init on >= Xenial
        out, _err = util.subp(["cloud-id"])
        return out.strip()
    try:
        return get_cloud_type_from_result_file()
    except FileNotFoundError:
        pass
    return None


def cloud_instance_factory() -> clouds.AutoAttachCloudInstance:
    from uaclient.clouds import aws
    from uaclient.clouds import azure
    from uaclient.clouds import gcp

    cloud_instance_map = {
        "aws": aws.UAAutoAttachAWSInstance,
        "aws-china": aws.UAAutoAttachAWSInstance,
        "aws-gov": aws.UAAutoAttachAWSInstance,
        "azure": azure.UAAutoAttachAzureInstance,
        "gce": gcp.UAAutoAttachGCPInstance,
    }  # type: Dict[str, Type[clouds.AutoAttachCloudInstance]]

    cloud_type = get_cloud_type()
    if not cloud_type:
        raise exceptions.UserFacingError(
            status.MESSAGE_UNABLE_TO_DETERMINE_CLOUD_TYPE
        )
    cls = cloud_instance_map.get(cloud_type)
    if not cls:
        raise exceptions.NonAutoAttachImageError(
            status.MESSAGE_UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
                cloud_type=cloud_type
            )
        )
    instance = cls()
    if not instance.is_viable:
        raise exceptions.UserFacingError(
            status.MESSAGE_UNSUPPORTED_AUTO_ATTACH
        )
    return instance
