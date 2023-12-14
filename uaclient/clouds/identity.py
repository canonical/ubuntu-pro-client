import logging
from enum import Enum
from functools import lru_cache
from typing import Dict, Optional, Tuple, Type  # noqa: F401

from uaclient import clouds, exceptions, messages, system, util
from uaclient.config import apply_config_settings_override

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

CLOUD_TYPE_TO_TITLE = {
    "aws": "AWS",
    "aws-china": "AWS China",
    "aws-gov": "AWS Gov",
    "azure": "Azure",
    "gce": "GCP",
}

PRO_CLOUD_URLS = {
    "aws": messages.urls.PRO_ON_AWS_HOME_PAGE,
    "azure": messages.urls.PRO_ON_AZURE_HOME_PAGE,
    "gce": messages.urls.PRO_ON_GCP_HOME_PAGE,
}


class NoCloudTypeReason(Enum):
    NO_CLOUD_DETECTED = 0
    CLOUD_ID_ERROR = 1


def get_instance_id() -> Optional[str]:
    """Query cloud instance-id from cmdline."""
    try:
        # Present in cloud-init on >= Xenial
        out, _err = system.subp(["cloud-init", "query", "instance_id"])
        return out.strip()
    except exceptions.ProcessExecutionError:
        pass
    LOG.warning("Unable to determine current instance-id")
    return None


@lru_cache(maxsize=None)
@apply_config_settings_override("cloud_type")
def get_cloud_type() -> Tuple[Optional[str], Optional[NoCloudTypeReason]]:
    if system.which("cloud-id"):
        # Present in cloud-init on >= Xenial
        try:
            out, _err = system.subp(["cloud-id"])
            return (out.strip(), None)
        except exceptions.ProcessExecutionError as exc:
            LOG.debug("error running cloud-id: %s", str(exc))
            return (None, NoCloudTypeReason.CLOUD_ID_ERROR)
    # If no cloud-id command, assume not on cloud
    return (None, NoCloudTypeReason.NO_CLOUD_DETECTED)


def cloud_instance_factory(
    cloud_override: Optional[str] = None,
) -> clouds.AutoAttachCloudInstance:
    """
    :raises CloudFactoryError: if no cloud instance object can be constructed
    :raises CloudFactoryNoCloudError: if no cloud instance object can be
        constructed because we are not on a cloud
    :raises CloudFactoryUnsupportedCloudError: if no cloud instance object can
        be constructed because we don't have a class for the cloud we're on
    :raises CloudFactoryNonViableCloudError: if no cloud instance object can be
        constructed because we explicitly do not support the cloud we're on
    """
    from uaclient.clouds import aws, azure, gcp

    cloud_instance_map = {
        "aws": aws.UAAutoAttachAWSInstance,
        "aws-china": aws.UAAutoAttachAWSInstance,
        "aws-gov": aws.UAAutoAttachAWSInstance,
        "azure": azure.UAAutoAttachAzureInstance,
        "gce": gcp.UAAutoAttachGCPInstance,
    }  # type: Dict[str, Type[clouds.AutoAttachCloudInstance]]

    if cloud_override is not None:
        cloud_type = cloud_override
    else:
        cloud_type, _ = get_cloud_type()

    if not cloud_type:
        raise exceptions.CloudFactoryNoCloudError()
    cls = cloud_instance_map.get(cloud_type)
    if not cls:
        raise exceptions.NonAutoAttachImageError(cloud_type=cloud_type)
    instance = cls()
    if not instance.is_viable:
        raise exceptions.CloudFactoryNonViableCloudError()
    return instance
