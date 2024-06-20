from uaclient import messages
from uaclient.api.errors import APIError
from uaclient.exceptions import (
    AlreadyAttachedError,
    ConnectivityError,
    ContractAPIError,
    EntitlementNotDisabledError,
    EntitlementNotEnabledError,
    EntitlementNotFoundError,
    EntitlementsNotEnabledError,
    IncompatibleServiceStopsEnable,
    InvalidProImage,
    LockHeldError,
    MagicAttachTokenAlreadyActivated,
    MagicAttachTokenError,
    MagicAttachUnavailable,
    NonAutoAttachImageError,
    NonRootUserError,
    RequiredServiceStopsEnable,
    UbuntuProError,
    UnattachedError,
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
    "MagicAttachTokenAlreadyActivated",
    "MagicAttachTokenError",
    "MagicAttachUnavailable",
    "NonAutoAttachImageError",
    "NonRootUserError",
    "UbuntuProError",
    "UnattachedError",
    "UrlError",
    "UserFacingError",
    "EntitlementsNotEnabledError",
    "EntitlementNotEnabledError",
    "EntitlementNotDisabledError",
    "IncompatibleServiceStopsEnable",
    "RequiredServiceStopsEnable",
]


class AutoAttachDisabledError(UbuntuProError):
    _msg = messages.E_AUTO_ATTACH_DISABLED_ERROR


class UnattendedUpgradesError(APIError):
    _formatted_msg = messages.E_UNATTENDED_UPGRADES_ERROR


class NotSupported(UbuntuProError):
    _msg = messages.E_NOT_SUPPORTED
