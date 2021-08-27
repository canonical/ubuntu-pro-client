import logging
from enum import Enum
from typing import Dict, Optional, Tuple, Type  # noqa F401

from uaclient import clouds, exceptions, status, util
from uaclient.config import apply_config_settings_override

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


class NoCloudTypeReason(Enum):
    NO_CLOUD_DETECTED = 0
    CLOUD_ID_ERROR = 1


def get_instance_id() -> "Optional[str]":
    """Query cloud instance-id from cmdline."""
    try:
        # Present in cloud-init on >= Xenial
        out, _err = util.subp(["cloud-init", "query", "instance_id"])
        return out.strip()
    except util.ProcessExecutionError:
        pass
    logging.warning("Unable to determine current instance-id")
    return None


@apply_config_settings_override("cloud_type")
def get_cloud_type() -> "Tuple[Optional[str], Optional[NoCloudTypeReason]]":
    if util.which("cloud-id"):
        # Present in cloud-init on >= Xenial
        try:
            out, _err = util.subp(["cloud-id"])
            return (out.strip(), None)
        except util.ProcessExecutionError:
            return (None, NoCloudTypeReason.CLOUD_ID_ERROR)
    # If no cloud-id command, assume not on cloud
    return (None, NoCloudTypeReason.NO_CLOUD_DETECTED)


def cloud_instance_factory() -> clouds.AutoAttachCloudInstance:
    from uaclient.clouds import aws, azure, gcp

    cloud_instance_map = {
        "aws": aws.UAAutoAttachAWSInstance,
        "aws-china": aws.UAAutoAttachAWSInstance,
        "aws-gov": aws.UAAutoAttachAWSInstance,
        "azure": azure.UAAutoAttachAzureInstance,
        "gce": gcp.UAAutoAttachGCPInstance,
    }  # type: Dict[str, Type[clouds.AutoAttachCloudInstance]]

    cloud_type, _ = get_cloud_type()
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
