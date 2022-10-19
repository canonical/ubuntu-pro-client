from typing import List, Tuple

from uaclient import messages
from uaclient.exceptions import (
    AlreadyAttachedError,
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
    "ConnectivityError",
    "ContractAPIError",
    "EntitlementNotFoundError",
    "InvalidProImage",
    "LockHeldError",
    "NonAutoAttachImageError",
    "UrlError",
    "UserFacingError",
]


class EntitlementsNotEnabledError(UserFacingError):
    def __init__(
        self, failed_services: List[Tuple[str, messages.NamedMessage]]
    ):
        info_dicts = [
            {"name": f[0], "code": f[1].name, "title": f[1].msg}
            for f in failed_services
        ]
        super().__init__(
            messages.ENTITLEMENTS_NOT_ENABLED_ERROR.msg,
            messages.ENTITLEMENTS_NOT_ENABLED_ERROR.name,
            additional_info={"services": info_dicts},
        )


class AutoAttachDisabledError(UserFacingError):
    def __init__(self):
        super().__init__(
            messages.AUTO_ATTACH_DISABLED_ERROR.msg,
            messages.AUTO_ATTACH_DISABLED_ERROR.name,
        )
