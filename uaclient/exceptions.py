import textwrap
from typing import Any, Dict, List, Optional, Tuple

from uaclient import messages
from uaclient.defaults import PRINT_WRAP_WIDTH


class UserFacingError(Exception):
    """
    An exception to be raised when an execution-ending error is encountered.

    :param msg:
        Takes a single parameter, which is the user-facing error message that
        should be emitted before exiting non-zero.
    """

    exit_code = 1

    def __init__(
        self,
        msg: str,
        msg_code: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.msg = msg
        self.msg_code = msg_code
        self.additional_info = additional_info


class APTProcessConflictError(UserFacingError):
    def __init__(self):
        super().__init__(
            msg=messages.APT_PROCESS_CONFLICT.msg,
            msg_code=messages.APT_PROCESS_CONFLICT.name,
        )


class APTInvalidRepoError(UserFacingError):
    def __init__(self, error_msg: str) -> None:
        super().__init__(msg=error_msg)


class APTUpdateProcessConflictError(UserFacingError):
    def __init__(self) -> None:
        super().__init__(
            msg=messages.APT_UPDATE_PROCESS_CONFLICT.msg,
            msg_code=messages.APT_UPDATE_PROCESS_CONFLICT.name,
        )


class APTUpdateInvalidRepoError(UserFacingError):
    def __init__(self, repo_msg: str) -> None:
        msg = messages.APT_UPDATE_INVALID_REPO.format(repo_msg=repo_msg)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class APTInstallProcessConflictError(UserFacingError):
    def __init__(self, header_msg: Optional[str] = None) -> None:
        if header_msg:
            header_msg += ".\n"

        msg = messages.APT_INSTALL_PROCESS_CONFLICT.format(
            header_msg=header_msg
        )

        super().__init__(msg=msg.msg, msg_code=msg.name)


class APTInstallInvalidRepoError(UserFacingError):
    def __init__(
        self, repo_msg: str, header_msg: Optional[str] = None
    ) -> None:
        if header_msg:
            header_msg += ".\n"

        msg = messages.APT_INSTALL_INVALID_REPO.format(
            header_msg=header_msg, repo_msg=repo_msg
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class CannotInstallSnapdError(UserFacingError):
    def __init__(self) -> None:
        msg = messages.CANNOT_INSTALL_SNAPD
        super().__init__(msg=msg.msg, msg_code=msg.name)


class ErrorInstallingLivepatch(UserFacingError):
    def __init__(self, error_msg: str) -> None:
        msg = messages.ERROR_INSTALLING_LIVEPATCH.format(error_msg=error_msg)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class InvalidServiceToDisableError(UserFacingError):
    def __init__(
        self, operation: str, invalid_service: str, service_msg: str
    ) -> None:
        msg = messages.INVALID_SERVICE_OP_FAILURE.format(
            operation=operation,
            invalid_service=invalid_service,
            service_msg=service_msg,
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class ProxyNotWorkingError(UserFacingError):
    def __init__(self, proxy: str):
        super().__init__(
            msg=messages.NOT_SETTING_PROXY_NOT_WORKING.format(proxy=proxy).msg,
            msg_code=messages.NOT_SETTING_PROXY_NOT_WORKING.name,
        )


class ProxyInvalidUrl(UserFacingError):
    def __init__(self, proxy: str):
        super().__init__(
            msg=messages.NOT_SETTING_PROXY_INVALID_URL.format(proxy=proxy).msg,
            msg_code=messages.NOT_SETTING_PROXY_INVALID_URL.name,
        )


class AlreadyAttachedError(UserFacingError):
    """An exception to be raised when a command needs an unattached system."""

    exit_code = 2

    def __init__(self, account_name: str):
        msg = messages.ALREADY_ATTACHED.format(account_name=account_name)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class AttachError(UserFacingError):
    """An exception to be raised when we detect a generic attach error."""

    exit_code = 1

    def __init__(self):
        msg = messages.ATTACH_FAILURE
        super().__init__(msg=msg.msg, msg_code=msg.name)


class AttachInvalidConfigFileError(UserFacingError):
    def __init__(self, config_name: str, error: str) -> None:
        msg = messages.ATTACH_CONFIG_READ_ERROR.format(
            config_name=config_name, error=error
        )

        super().__init__(
            msg=textwrap.fill(msg.msg, width=PRINT_WRAP_WIDTH),
            msg_code=msg.name,
        )


class AttachInvalidTokenError(UserFacingError):
    def __init__(self):
        super().__init__(
            msg=messages.ATTACH_INVALID_TOKEN.msg,
            msg_code=messages.ATTACH_INVALID_TOKEN.name,
        )


class ConnectivityError(UserFacingError):
    def __init__(self):
        super().__init__(
            msg=messages.CONNECTIVITY_ERROR.msg,
            msg_code=messages.CONNECTIVITY_ERROR.name,
        )


class MagicAttachTokenAlreadyActivated(UserFacingError):
    def __init__(self):
        msg = messages.MAGIC_ATTACH_TOKEN_ALREADY_ACTIVATED
        super().__init__(
            msg=msg.msg,
            msg_code=msg.name,
        )


class MagicAttachTokenError(UserFacingError):
    def __init__(self):
        msg = messages.MAGIC_ATTACH_TOKEN_ERROR
        super().__init__(
            msg=msg.msg,
            msg_code=msg.name,
        )


class MagicAttachUnavailable(UserFacingError):
    def __init__(self):
        msg = messages.MAGIC_ATTACH_UNAVAILABLE
        super().__init__(
            msg=msg.msg,
            msg_code=msg.name,
        )


class MagicAttachInvalidParam(UserFacingError):
    def __init__(self, param, value):
        msg = messages.MAGIC_ATTACH_INVALID_PARAM.format(
            param=param, value=value
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class LockHeldError(UserFacingError):
    """An exception for when another pro operation is in progress

    :param lock_request: String of the command requesting the lock
    :param lock_holder: String of the command that currently holds the lock
    :param pid: Integer of the process id of the lock_holder
    """

    def __init__(self, lock_request: str, lock_holder: str, pid: int):
        self.lock_holder = lock_holder
        self.pid = pid
        msg = messages.LOCK_HELD_ERROR.format(
            lock_request=lock_request, lock_holder=lock_holder, pid=pid
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class MissingAptURLDirective(UserFacingError):
    """An exception for when the contract server doesn't include aptURL"""

    def __init__(self, entitlement_name):
        msg = messages.MISSING_APT_URL_DIRECTIVE.format(
            entitlement_name=entitlement_name
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class NonRootUserError(UserFacingError):
    """An exception to be raised when a user needs to be root."""

    def __init__(self) -> None:
        super().__init__(
            msg=messages.NONROOT_USER.msg, msg_code=messages.NONROOT_USER.name
        )


class UnattachedError(UserFacingError):
    """An exception to be raised when a machine needs to be attached."""

    def __init__(
        self, msg: messages.NamedMessage = messages.UNATTACHED
    ) -> None:
        super().__init__(msg=msg.msg, msg_code=msg.name)


class SecurityAPIMetadataError(UserFacingError):
    """An exception raised with Security API metadata returns invalid data."""

    def __init__(self, msg: str, issue_id: str) -> None:
        super().__init__(
            "Error: "
            + msg
            + "\n"
            + messages.SECURITY_ISSUE_NOT_RESOLVED.format(
                issue=issue_id, extra_info=""
            )
        )


class InvalidProImage(UserFacingError):
    def __init__(self, error_msg: str):
        self.contract_server_msg = error_msg
        msg = messages.INVALID_PRO_IMAGE.format(msg=error_msg)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class GCPProAccountError(UserFacingError):
    """An exception raised when GCP Pro service account is not enabled"""

    def __init__(self, msg: str, msg_code: Optional[str], code=None):
        self.code = code
        super().__init__(msg, msg_code)

    def __str__(self):
        return "GCPProServiceAccount Error {code}: {msg}".format(
            code=self.code, msg=self.msg
        )


class CloudFactoryError(UserFacingError):
    pass


class CloudFactoryNoCloudError(CloudFactoryError):
    def __init__(self) -> None:
        msg = messages.UNABLE_TO_DETERMINE_CLOUD_TYPE
        super().__init__(msg=msg.msg, msg_code=msg.name)


class NonAutoAttachImageError(CloudFactoryError):
    """Raised when machine isn't running an auto-attach enabled image"""

    exit_code = 0

    def __init__(self, cloud_type: str) -> None:
        self.cloud_type = cloud_type
        msg = messages.UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
            cloud_type=cloud_type
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class CloudFactoryNonViableCloudError(CloudFactoryError):
    def __init__(self) -> None:
        msg = messages.UNSUPPORTED_AUTO_ATTACH
        super().__init__(msg=msg.msg, msg_code=msg.name)


class EntitlementNotFoundError(UserFacingError):
    def __init__(self, entitlement_name: str):
        msg = messages.ENTITLEMENT_NOT_FOUND.format(name=entitlement_name)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class EntitlementsNotEnabledError(UserFacingError):

    exit_code = 4

    def __init__(
        self,
        failed_services: List[Tuple[str, messages.NamedMessage]],
        msg: messages.NamedMessage = messages.ENTITLEMENTS_NOT_ENABLED_ERROR,
    ):
        info_dicts = [
            {"name": f[0], "code": f[1].name, "title": f[1].msg}
            for f in failed_services
        ]
        super().__init__(
            msg=msg.msg,
            msg_code=msg.name,
            additional_info={"services": info_dicts},
        )


class AttachFailureDefaultServices(EntitlementsNotEnabledError):
    def __init__(
        self, failed_services: List[Tuple[str, messages.NamedMessage]]
    ):
        super().__init__(
            failed_services=failed_services,
            msg=messages.ATTACH_FAILURE_DEFAULT_SERVICES,
        )


class AttachFailureUnknownError(EntitlementsNotEnabledError):
    def __init__(
        self, failed_services: List[Tuple[str, messages.NamedMessage]]
    ):
        super().__init__(
            failed_services=failed_services, msg=messages.UNEXPECTED_ERROR
        )


class UrlError(IOError):
    def __init__(
        self,
        cause: Exception,
        url: str,
    ):
        if getattr(cause, "reason", None):
            cause_error = str(getattr(cause, "reason"))
        else:
            cause_error = str(cause)
        super().__init__(cause_error)
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
            message = messages.SUBP_INVALID_COMMAND.format(cmd=cmd)
        else:
            message = messages.SUBP_COMMAND_FAILED.format(
                cmd=cmd, exit_code=exit_code, stderr=stderr
            )
        super().__init__(message)


class ExternalAPIError(UserFacingError):
    def __init__(self, url: str, code: int, body: str):
        self.url = url
        self.code = code
        self.body = body
        msg = messages.EXTERNAL_API_ERROR.format(url=url, code=code, body=body)
        super().__init__(msg.msg, msg.name)

    def __str__(self):
        return "{}: [{}], {}".format(self.code, self.url, self.body)


class ContractAPIError(ExternalAPIError):
    pass


class SecurityAPIError(ExternalAPIError):
    pass


class InPlaceUpgradeNotSupportedError(Exception):
    pass


class IsProLicensePresentError(Exception):
    pass


class CancelProLicensePolling(IsProLicensePresentError):
    pass


class DelayProLicensePolling(IsProLicensePresentError):
    pass


class InvalidFileFormatError(UserFacingError):
    def __init__(self, file_name: str, file_format: str) -> None:
        msg = messages.INVALID_FILE_FORMAT.format(
            file_name=file_name, file_format=file_format
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class ParsingErrorOnOSReleaseFile(UserFacingError):
    def __init__(self, orig_ver: str, mod_ver: str):
        msg = messages.ERROR_PARSING_VERSION_OS_RELEASE.format(
            orig_ver=orig_ver, mod_ver=mod_ver
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class MissingSeriesOnOSReleaseFile(UserFacingError):
    def __init__(self, version):
        msg = messages.MISSING_SERIES_ON_OS_RELEASE.format(version=version)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class InvalidLockFile(UserFacingError):
    def __init__(self, lock_file_path):
        msg = messages.INVALID_LOCK_FILE.format(lock_file_path=lock_file_path)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class InvalidOptionCombination(UserFacingError):
    def __init__(self, option1: str, option2: str):
        msg = messages.INVALID_OPTION_COMBINATION.format(
            option1=option1, option2=option2
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class CloudMetadataError(UserFacingError):
    def __init__(self, code: int, body: str) -> None:
        msg = messages.CLOUD_METADATA_ERROR.format(code=code, body=body)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class SnapNotInstalledError(UserFacingError):
    def __init__(self, snap: str):
        msg = messages.SNAP_NOT_INSTALLED_ERROR.format(snap=snap)
        super().__init__(msg=msg.msg, msg_code=msg.name)


class UnexpectedSnapdAPIError(UserFacingError):
    def __init__(self, error: Optional[str]):
        msg = messages.UNEXPECTED_SNAPD_API_ERROR.format(
            error=error if error else ""
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class SnapdAPIConnectionRefused(UserFacingError):
    def __init__(self):
        msg = messages.SNAPD_CONNECTION_REFUSED
        super().__init__(msg=msg.msg, msg_code=msg.name)


class SnapdInvalidJson(UserFacingError):
    def __init__(self, url: str, out: str):
        msg = messages.JSON_PARSER_ERROR.format(
            source="SNAPD API {}".format(url),
            out=out,
        )
        super().__init__(msg=msg.msg, msg_code=msg.name)


class PycurlRequiredError(UserFacingError):
    def __init__(self) -> None:
        msg = messages.PYCURL_REQUIRED
        super().__init__(msg=msg.msg, msg_code=msg.name)


class PycurlError(UserFacingError):
    def __init__(self, e) -> None:
        msg = messages.PYCURL_ERROR.format(e=str(e))
        super().__init__(msg=msg.msg, msg_code=msg.name)


class ProxyAuthenticationFailed(UserFacingError):
    def __init__(self) -> None:
        msg = messages.PROXY_AUTH_FAIL
        super().__init__(msg=msg.msg, msg_code=msg.name)


class SecurityIssueNotFound(UserFacingError):
    def __init__(self, issue_id: str):
        msg = messages.SECURITY_FIX_NOT_FOUND_ISSUE.format(issue_id=issue_id)
        super().__init__(msg=msg.msg, msg_code=msg.name)
