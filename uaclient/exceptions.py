from uaclient import status


class UserFacingError(Exception):
    """
    An exception to be raised when an execution-ending error is encountered.

    :param msg:
        Takes a single parameter, which is the user-facing error message that
        should be emitted before exiting non-zero.
    """

    def __init__(self, msg: str) -> None:
        self.msg = msg


class NonRootUserError(UserFacingError):
    """An exception to be raised when a user needs to be root."""

    def __init__(self) -> None:
        super().__init__(status.MESSAGE_NONROOT_USER)


class UnattachedError(UserFacingError):
    """An exception to be raised when a machine needs to be attached."""

    def __init__(self) -> None:
        super().__init__(status.MESSAGE_UNATTACHED)
