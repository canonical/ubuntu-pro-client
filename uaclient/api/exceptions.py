from uaclient.exceptions import (
    AlreadyAttachedError,
    BetaServiceError,
    ConnectivityError,
    ContractAPIError,
    EntitlementNotFoundError,
    InvalidProImage,
    LockHeldError,
    NonAutoAttachImageError,
    UrlError,
    UserFacingError,
)

__all__ = [
    "AlreadyAttachedError",
    "BetaServiceError",
    "ConnectivityError",
    "ContractAPIError",
    "EntitlementNotFoundError",
    "InvalidProImage",
    "LockHeldError",
    "NonAutoAttachImageError",
    "UrlError",
    "UserFacingError",
]


class EntitlementNotEnabledError(UserFacingError):
    """An exception raised when enabling of an entitlement fails"""

    pass


class IncompatibleEntitlementsDetected(UserFacingError):
    pass
