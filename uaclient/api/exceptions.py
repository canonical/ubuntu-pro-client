from uaclient import messages
from uaclient.api.errors import APIError
from uaclient.exceptions import (
    AlreadyAttachedError,
    ConnectivityError,
    ContractAPIError,
    DepedentOptionError,
    EntitlementNotDisabledError,
    EntitlementNotEnabledError,
    EntitlementNotFoundError,
    EntitlementsNotEnabledError,
    IncompatibleServiceStopsEnable,
    InvalidOptionCombination,
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
    UnsupportedManifestFile,
    UrlError,
    UserFacingError,
)

__all__ = [
    "AlreadyAttachedError",
    "ConnectivityError",
    "ContractAPIError",
    "EntitlementNotFoundError",
    "InvalidOptionCombination",
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
    "UnsupportedManifestFile",
    "DepedentOptionError",
]


class AutoAttachDisabledError(UbuntuProError):
    _msg = messages.E_AUTO_ATTACH_DISABLED_ERROR


class UnattendedUpgradesError(APIError):
    _formatted_msg = messages.E_UNATTENDED_UPGRADES_ERROR


class NotSupported(UbuntuProError):
    _msg = messages.E_NOT_SUPPORTED
