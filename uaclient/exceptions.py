from typing import Dict, Optional
from urllib import error

from uaclient import messages


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


class AlreadyAttachedOnPROError(UserFacingError):
    """Raised when a PRO machine retries attaching with the same instance-id"""

    exit_code = 0

    def __init__(self, instance_id: str):
        super().__init__(
            messages.ALREADY_ATTACHED_ON_PRO.format(instance_id=instance_id)
        )


class AlreadyAttachedError(UserFacingError):
    """An exception to be raised when a command needs an unattached system."""

    exit_code = 2

    def __init__(self, cfg):
        super().__init__(
            messages.ALREADY_ATTACHED.format(
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
        super().__init__(
            messages.LOCK_HELD_ERROR.format(
                lock_request=lock_request, lock_holder=lock_holder, pid=pid
            )
        )


class MissingAptURLDirective(UserFacingError):
    """An exception for when the contract server doesn't include aptURL"""

    def __init__(self, entitlement_name):
        super().__init__(
            messages.MISSING_APT_URL_DIRECTIVE.format(
                entitlement_name=entitlement_name
            )
        )


class NonRootUserError(UserFacingError):
    """An exception to be raised when a user needs to be root."""

    def __init__(self) -> None:
        super().__init__(messages.NONROOT_USER)


class UnattachedError(UserFacingError):
    """An exception to be raised when a machine needs to be attached."""

    def __init__(self, msg: str = messages.UNATTACHED) -> None:
        super().__init__(msg)


class SecurityAPIMetadataError(UserFacingError):
    """An exception raised with Security API metadata returns invalid data."""

    def __init__(self, msg: str, issue_id: str) -> None:
        super().__init__(
            "Error: "
            + msg
            + "\n"
            + messages.SECURITY_ISSUE_NOT_RESOLVED.format(issue=issue_id)
        )


class CloudFactoryError(Exception):
    def __init__(self, cloud_type: Optional[str]) -> None:
        self.cloud_type = cloud_type


class CloudFactoryNoCloudError(CloudFactoryError):
    pass


class CloudFactoryUnsupportedCloudError(CloudFactoryError):
    pass


class CloudFactoryNonViableCloudError(CloudFactoryError):
    pass


class EntitlementNotFoundError(Exception):
    pass


class UrlError(IOError):
    def __init__(
        self,
        cause: error.URLError,
        code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
    ):
        if getattr(cause, "reason", None):
            cause_error = str(cause.reason)
        else:
            cause_error = str(cause)
        super().__init__(cause_error)
        self.code = code
        self.headers = headers
        if self.headers is None:
            self.headers = {}
        self.url = url


class ProcessExecutionError(IOError):
    def __init__(
        self,
        cmd: str,
        exit_code: Optional[int] = None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        if not exit_code:
            message_tmpl = "Invalid command specified '{cmd}'."
        else:
            message_tmpl = (
                "Failed running command '{cmd}' [exit({exit_code})]."
                " Message: {stderr}"
            )
        super().__init__(
            message_tmpl.format(cmd=cmd, stderr=stderr, exit_code=exit_code)
        )


class ContractAPIError(UrlError):
    def __init__(self, e, error_response):
        super().__init__(e, e.code, e.headers, e.url)
        if "error_list" in error_response:
            self.api_errors = error_response["error_list"]
        else:
            self.api_errors = [error_response]
        for api_error in self.api_errors:
            api_error["code"] = api_error.get("title", api_error.get("code"))

    def __contains__(self, error_code):
        for api_error in self.api_errors:
            if error_code == api_error.get("code"):
                return True
            if api_error.get("message", "").startswith(error_code):
                return True
        return False

    def __get__(self, error_code, default=None):
        for api_error in self.api_errors:
            if api_error["code"] == error_code:
                return api_error["detail"]
        return default

    def __str__(self):
        prefix = super().__str__()
        details = []
        for err in self.api_errors:
            if not err.get("extra"):
                details.append(err.get("detail", err.get("message", "")))
            else:
                for extra in err["extra"].values():
                    if isinstance(extra, list):
                        details.extend(extra)
                    else:
                        details.append(extra)
        return prefix + ": [" + self.url + "]" + ", ".join(details)


class SecurityAPIError(UrlError):
    def __init__(self, e, error_response):
        super().__init__(e, e.code, e.headers, e.url)
        self.message = error_response.get("message", "")

    def __contains__(self, error_code):
        return bool(error_code in self.message)

    def __get__(self, error_str, default=None):
        if error_str in self.message:
            return self.message
        return default

    def __str__(self):
        prefix = super().__str__()
        details = [self.message]
        if details:
            return prefix + ": [" + self.url + "] " + ", ".join(details)
        return prefix + ": [" + self.url + "]"
