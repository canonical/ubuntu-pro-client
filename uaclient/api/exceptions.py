from uaclient import messages
from uaclient.exceptions import (
    AlreadyAttachedError,
    BetaServiceError,
    ContractAPIError,
    EntitlementNotFoundError,
    NonAutoAttachImageError,
    UrlError,
    UserFacingError,
)

__all__ = [
    "AlreadyAttachedError",
    "BetaServiceError",
    "ContractAPIError",
    "EntitlementNotFoundError",
    "NonAutoAttachImageError",
    "UrlError",
    "UserFacingError",
]


class EntitlementNotEnabledError(UserFacingError):
    """An exception raised when enabling of an entitlement fails"""

    pass


class FullAutoAttachFailureError(UserFacingError):
    """An exception raised when auto attach at boot fails"""

    def __init__(self):
        super().__init__(
            msg=messages.FULL_AUTO_ATTACH_ERROR.msg,
            msg_code=messages.FULL_AUTO_ATTACH_ERROR.name,
        )


class IncompatibleEntitlementsDetected(UserFacingError):
    pass
