import abc
import json

from uaclient import exceptions
from uaclient import util
from uaclient import clouds

CLOUDINIT_RESULT_FILE = '/var/lib/cloud/data/result.json'


class UAPremiumCloudInstance(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def identity_doc(self) -> str:
        """Return the identity document representing this cloud instance"""
        pass

    @property
    @abc.abstractmethod
    def is_viable(self) -> bool:
        """Return True if the machine is a viable UAPremiumCloudInstance."""
        pass


@util.retry(FileNotFoundError, [1, 2])
def get_cloud_type_from_result_file(result_file=CLOUDINIT_RESULT_FILE) -> str:
    result = json.loads((util.load_file(result_file)))
    dsname = result['v1']['datasource'].split()[0].lower()
    return dsname.replace('datasource', '')


def get_cloud_type() -> str:
    if util.which('cloud-id'):
        # Present in cloud-init on >= Xenial
        out, _err = util.subp(['cloud-id'])
        return out.strip()
    try:
        return get_cloud_type_from_result_file()
    except FileNotFoundError:
        pass
    return ''


def cloud_instance_factory() -> UAPremiumCloudInstance:
    cloud_type = get_cloud_type()
    if not cloud_type:
        raise exceptions.UserFacingError(
            'Could not determine cloud type UA Premium Images.'
            ' Unable to attach')
    cls = clouds.CLOUD_INSTANCE_MAP.get(cloud_type)
    if not cls:
        raise exceptions.UserFacingError(
            "No UAPremiumCloudInstance class available for cloud type '%s'" %
            cloud_type)
    instance = cls()
    if not instance.is_viable:
        raise exceptions.UserFacingError(
            'This vm is not a viable premium image on cloud "%s"' % cloud_type)
    return instance
