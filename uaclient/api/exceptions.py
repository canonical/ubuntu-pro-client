from uaclient import messages
from uaclient.api.errors import APIError
from uaclient.exceptions import (
    AlreadyAttachedError,
    ConnectivityError,
    ContractAPIError,
    EntitlementNotFoundError,
    EntitlementsNotEnabledError,
    InvalidProImage,
    LockHeldError,
    NonAutoAttachImageError,
    UbuntuProError,
    UrlError,
    UserFacingError,
)

__all__ = [
    "AlreadyAttachedError",
    "ConnectivityError",
    "ContractAPIError",
    "EntitlementNotFoundError",
    "InvalidProImage",
    "LockHeldError",
    "NonAutoAttachImageError",
    "UbuntuProError",
    "UrlError",
    "UserFacingError",
    "EntitlementsNotEnabledError",
]


class AutoAttachDisabledError(UbuntuProError):
    _msg = messages.E_AUTO_ATTACH_DISABLED_ERROR


class UnattendedUpgradesError(APIError):
    _formatted_msg = messages.E_UNATTENDED_UPGRADES_ERROR
