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
    "UrlError",
    "UserFacingError",
    "EntitlementsNotEnabledError",
]


class AutoAttachDisabledError(UserFacingError):
    _msg = messages.AUTO_ATTACH_DISABLED_ERROR


class UnattendedUpgradesError(APIError):
    _formatted_msg = messages.UNATTENDED_UPGRADES_ERROR
