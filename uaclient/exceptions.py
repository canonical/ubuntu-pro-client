from uaclient import status


class UserFacingError(Exception):
    """
    An exception to be raised when an execution-ending error is encountered.

    :param msg:
        Takes a single parameter, which is the user-facing error message that
        should be emitted before exiting non-zero.
    """

    exit_code = 1

    def __init__(self, msg: str) -> None:
        self.msg = msg


class NonAutoAttachImageError(UserFacingError):
    """Raised when machine isn't running an auto-attach enabled image"""

    exit_code = 0


class AlreadyAttachedError(UserFacingError):
    """An exception to be raised when a command needs an unattached system."""

    exit_code = 0

    def __init__(self, cfg):
        super().__init__(
            status.MESSAGE_ALREADY_ATTACHED.format(
                account_name=cfg.accounts[0]["name"]
            )
        )


class MissingAptURLDirective(UserFacingError):
    """An exception for when the contract server doesn't include aptURL"""

    def __init__(self, entitlement_name):
        super().__init__(
            status.MESSAGE_MISSING_APT_URL_DIRECTIVE.format(
                entitlement_name=entitlement_name
            )
        )


class NonRootUserError(UserFacingError):
    """An exception to be raised when a user needs to be root."""

    def __init__(self) -> None:
        super().__init__(status.MESSAGE_NONROOT_USER)


class UnattachedError(UserFacingError):
    """An exception to be raised when a machine needs to be attached."""

    def __init__(self, msg: str = status.MESSAGE_UNATTACHED) -> None:
        super().__init__(msg)
