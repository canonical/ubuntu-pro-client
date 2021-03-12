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


class BetaServiceError(UserFacingError):
    """
    An exception to be raised trying to interact with beta service
    without the right parameters.

    :param msg:
        Takes a single parameter, which is the beta service error message that
        should be emitted before exiting non-zero.
    """

    pass


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


class LockHeldError(UserFacingError):
    """An exception for when another ua operation is in progress

    :param lock_request: String of the command requesting the lock
    :param lock_holder: String of the command that currently holds the lock
    :param pid: Integer of the process id of the lock_holder
    """

    def __init__(self, lock_request: str, lock_holder: str, pid: int):
        lock_request = lock_request
        msg = "Unable to perform: {lock_request}.\n".format(
            lock_request=lock_request
        )
        msg += status.MESSAGE_LOCK_HELD.format(
            pid=pid, lock_holder=lock_holder
        )
        super().__init__(msg)


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


class SecurityAPIMetadataError(UserFacingError):
    """An exception raised with Security API metadata returns invalid data."""

    def __init__(self, msg: str, issue_id: str) -> None:
        super().__init__(
            "Error: "
            + msg
            + "\n"
            + status.MESSAGE_SECURITY_ISSUE_NOT_RESOLVED.format(issue=issue_id)
        )
