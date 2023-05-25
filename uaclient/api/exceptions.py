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
    def __init__(self):
        super().__init__(
            messages.AUTO_ATTACH_DISABLED_ERROR.msg,
            messages.AUTO_ATTACH_DISABLED_ERROR.name,
        )


class UnattendedUpgradesError(APIError):
    def __init__(self, msg):
        self.msg = msg
        self.msg_code = "unable-to-determine-unattended-upgrade-status"
