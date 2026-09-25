from enum import Enum
from typing import Optional

from pycloudlib.cloud import ImageType  # type: ignore


class MachineType(Enum):
    """Supported machine backends and cloud image types."""

    AWS_GENERIC = ("aws.generic", "aws", ImageType.GENERIC)
    AWS_PRO = ("aws.pro", "aws", ImageType.PRO)
    AWS_PRO_FIPS = ("aws.pro-fips", "aws", ImageType.PRO_FIPS)
    AZURE_GENERIC = ("azure.generic", "azure", ImageType.GENERIC)
    AZURE_PRO = ("azure.pro", "azure", ImageType.PRO)
    AZURE_PRO_FIPS = ("azure.pro-fips", "azure", ImageType.PRO_FIPS)
    GCP_GENERIC = ("gcp.generic", "gcp", ImageType.GENERIC)
    GCP_PRO = ("gcp.pro", "gcp", ImageType.PRO)
    GCP_PRO_FIPS = ("gcp.pro-fips", "gcp", ImageType.PRO_FIPS)
    LXD_CONTAINER = ("lxd-container", "lxd-container", None)
    LXD_VM = ("lxd-vm", "lxd-vm", None)
    WSL = ("wsl", "wsl", None)

    def __new__(cls, value, cloud_name, image_type):
        member = object.__new__(cls)
        member._value_ = value
        return member

    def __init__(self, value, cloud_name, image_type):
        self.cloud_name = cloud_name  # type: str
        self.image_type = image_type  # type: Optional[ImageType]

    @classmethod
    def from_string(cls, value: str) -> "MachineType":
        try:
            return cls(value)  # type: ignore
        except ValueError:
            raise ValueError("Unsupported machine type: {}".format(value))

    @property
    def uses_pro_image(self) -> bool:
        return self.image_type in (
            ImageType.PRO,
            ImageType.PRO_FIPS,
        )
