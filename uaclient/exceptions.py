from typing import List, Optional, Tuple

from uaclient import messages


class UbuntuProError(Exception):
    """
    Base class for all of our custom errors.
    All possible exceptions from our API should extend this class.
    """

    _msg = None  # type: messages.NamedMessage
    _formatted_msg = None  # type: messages.FormattedNamedMessage

    exit_code = 1

    def __init__(self, **kwargs) -> None:
        if self._formatted_msg is not None:
            self.named_msg = self._formatted_msg.format(
                **kwargs
            )  # type: messages.NamedMessage
        else:
            self.named_msg = self._msg

        self.additional_info = kwargs

        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def msg(self):
        return self.named_msg.msg

    @property
    def msg_code(self):
        return self.named_msg.name

    def __str__(self):
        return self.named_msg.msg


# UserFacingError is the old name of our base exception class.
# Other systems may import and rely on this name.
# Leave this here for backwards compatibility.
UserFacingError = UbuntuProError


class APTProcessConflictError(UbuntuProError):
    _msg = messages.APT_PROCESS_CONFLICT


class APTInvalidRepoError(UbuntuProError):
    _formatted_msg = messages.APT_UPDATE_INVALID_URL_CONFIG


class APTUpdateProcessConflictError(UbuntuProError):
    _msg = messages.APT_UPDATE_PROCESS_CONFLICT


class APTUpdateInvalidRepoError(UbuntuProError):
    _formatted_msg = messages.APT_UPDATE_INVALID_REPO


class APTUpdateFailed(UbuntuProError):
    _formatted_msg = messages.APT_UPDATE_FAILED


class APTInstallProcessConflictError(UbuntuProError):
    _msg = messages.APT_INSTALL_PROCESS_CONFLICT


class APTInstallInvalidRepoError(UbuntuProError):
    _formatted_msg = messages.APT_INSTALL_INVALID_REPO


class APTInvalidCredentials(UbuntuProError):
    _formatted_msg = messages.APT_INVALID_CREDENTIALS


class APTTimeout(UbuntuProError):
    _formatted_msg = messages.APT_TIMEOUT


class APTUnexpectedError(UbuntuProError):
    _formatted_msg = messages.APT_UNEXPECTED_ERROR


class APTCommandTimeout(UbuntuProError):
    _formatted_msg = messages.APT_COMMAND_TIMEOUT


class CannotInstallSnapdError(UbuntuProError):
    _msg = messages.CANNOT_INSTALL_SNAPD


class ErrorInstallingLivepatch(UbuntuProError):
    _formatted_msg = messages.ERROR_INSTALLING_LIVEPATCH


class InvalidServiceOpError(UbuntuProError):
    _formatted_msg = messages.INVALID_SERVICE_OP_FAILURE


class ProxyNotWorkingError(UbuntuProError):
    _formatted_msg = messages.NOT_SETTING_PROXY_NOT_WORKING


class ProxyInvalidUrl(UbuntuProError):
    _formatted_msg = messages.NOT_SETTING_PROXY_INVALID_URL


class AlreadyAttachedError(UbuntuProError):
    """An exception to be raised when a command needs an unattached system."""

    exit_code = 2
    _formatted_msg = messages.ALREADY_ATTACHED


class AttachError(UbuntuProError):
    """An exception to be raised when we detect a generic attach error."""

    exit_code = 1
    _msg = messages.ATTACH_FAILURE


class AttachInvalidConfigFileError(UbuntuProError):
    _formatted_msg = messages.ATTACH_CONFIG_READ_ERROR


class AttachInvalidTokenError(UbuntuProError):
    _msg = messages.ATTACH_INVALID_TOKEN


class AttachForbiddenExpired(UbuntuProError):
    _formatted_msg = messages.ATTACH_FORBIDDEN_EXPIRED


class AttachForbiddenNotYet(UbuntuProError):
    _formatted_msg = messages.ATTACH_FORBIDDEN_NOT_YET


class AttachForbiddenNever(UbuntuProError):
    _formatted_msg = messages.ATTACH_FORBIDDEN_NEVER


class AttachExpiredToken(UbuntuProError):
    _msg = messages.ATTACH_EXPIRED_TOKEN


class ConnectivityError(UbuntuProError):
    _msg = messages.CONNECTIVITY_ERROR


class MagicAttachTokenAlreadyActivated(UbuntuProError):
    _msg = messages.MAGIC_ATTACH_TOKEN_ALREADY_ACTIVATED


class MagicAttachTokenError(UbuntuProError):
    _msg = messages.MAGIC_ATTACH_TOKEN_ERROR


class MagicAttachUnavailable(UbuntuProError):
    _msg = messages.MAGIC_ATTACH_UNAVAILABLE


class MagicAttachInvalidParam(UbuntuProError):
    _formatted_msg = messages.MAGIC_ATTACH_INVALID_PARAM


class LockHeldError(UbuntuProError):
    """An exception for when another pro operation is in progress

    :param lock_request: String of the command requesting the lock
    :param lock_holder: String of the command that currently holds the lock
    :param pid: Integer of the process id of the lock_holder
    """

    _formatted_msg = messages.LOCK_HELD_ERROR
    pid = None  # type: int


class MissingAptURLDirective(UbuntuProError):
    """An exception for when the contract server doesn't include aptURL"""

    _formatted_msg = messages.MISSING_APT_URL_DIRECTIVE


class NonRootUserError(UbuntuProError):
    """An exception to be raised when a user needs to be root."""

    _msg = messages.NONROOT_USER


class UnattachedError(UbuntuProError):
    """An exception to be raised when a machine needs to be attached."""

    _msg = messages.UNATTACHED


class UnattachedMixedServicesError(UbuntuProError):
    _formatted_msg = messages.MIXED_SERVICES_FAILURE_UNATTACHED


class UnattachedValidServicesError(UbuntuProError):
    _formatted_msg = messages.VALID_SERVICE_FAILURE_UNATTACHED


class UnattachedInvalidServicesError(UbuntuProError):
    _formatted_msg = messages.INVALID_SERVICE_OP_FAILURE


class SecurityAPIMetadataError(UbuntuProError):
    """An exception raised with Security API metadata returns invalid data."""

    _formatted_msg = messages.SECURITY_API_INVALID_METADATA


class InvalidProImage(UbuntuProError):
    _formatted_msg = messages.INVALID_PRO_IMAGE
    error_msg = None  # type: str


class CloudMetadataError(UbuntuProError):
    _formatted_msg = messages.CLOUD_METADATA_ERROR


class GCPServiceAccountError(CloudMetadataError):
    """An exception raised when GCP service account is not enabled"""

    _formatted_msg = messages.GCP_SERVICE_ACCT_NOT_ENABLED_ERROR


class AWSNoValidIMDS(UbuntuProError):
    _formatted_msg = messages.AWS_NO_VALID_IMDS


class CloudFactoryError(UbuntuProError):
    pass


class CloudFactoryNoCloudError(CloudFactoryError):
    _msg = messages.UNABLE_TO_DETERMINE_CLOUD_TYPE


class CloudFactoryNonViableCloudError(CloudFactoryError):
    _msg = messages.UNSUPPORTED_AUTO_ATTACH


class NonAutoAttachImageError(CloudFactoryError):
    """Raised when machine isn't running an auto-attach enabled image"""

    exit_code = 0
    _formatted_msg = messages.UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE


class EntitlementNotFoundError(UbuntuProError):
    _formatted_msg = messages.ENTITLEMENT_NOT_FOUND


class EntitlementsNotEnabledError(UbuntuProError):

    exit_code = 4
    _msg = messages.ENTITLEMENTS_NOT_ENABLED_ERROR

    def __init__(
        self, failed_services: List[Tuple[str, messages.NamedMessage]]
    ):
        info_dicts = [
            {"name": f[0], "code": f[1].name, "title": f[1].msg}
            for f in failed_services
        ]
        super().__init__(services=info_dicts)


class AttachFailureDefaultServices(EntitlementsNotEnabledError):
    _msg = messages.ATTACH_FAILURE_DEFAULT_SERVICES


class AttachFailureUnknownError(EntitlementsNotEnabledError):
    _msg = messages.ATTACH_FAILURE_UNEXPECTED


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


class ExternalAPIError(UbuntuProError):
    _formatted_msg = messages.EXTERNAL_API_ERROR
    code = None  # type: int
    url = None  # type: str
    body = None  # type: str

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


class InvalidFileFormatError(UbuntuProError):
    _formatted_msg = messages.INVALID_FILE_FORMAT


class ParsingErrorOnOSReleaseFile(UbuntuProError):
    _formatted_msg = messages.ERROR_PARSING_VERSION_OS_RELEASE


class MissingSeriesOnOSReleaseFile(UbuntuProError):
    _formatted_msg = messages.MISSING_SERIES_ON_OS_RELEASE


class InvalidLockFile(UbuntuProError):
    _formatted_msg = messages.INVALID_LOCK_FILE


class InvalidOptionCombination(UbuntuProError):
    _formatted_msg = messages.INVALID_OPTION_COMBINATION


class SnapNotInstalledError(UbuntuProError):
    _formatted_msg = messages.SNAP_NOT_INSTALLED_ERROR


class UnexpectedSnapdAPIError(UbuntuProError):
    _formatted_msg = messages.UNEXPECTED_SNAPD_API_ERROR


class SnapdAPIConnectionRefused(UbuntuProError):
    _msg = messages.SNAPD_CONNECTION_REFUSED


class InvalidJson(UbuntuProError):
    _formatted_msg = messages.JSON_PARSER_ERROR


class PycurlRequiredError(UbuntuProError):
    _msg = messages.PYCURL_REQUIRED


class PycurlError(UbuntuProError):
    _formatted_msg = messages.PYCURL_ERROR


class ProxyAuthenticationFailed(UbuntuProError):
    _msg = messages.PROXY_AUTH_FAIL


class SecurityIssueNotFound(UbuntuProError):
    _formatted_msg = messages.SECURITY_FIX_NOT_FOUND_ISSUE


class InvalidBooleanConfigValue(UbuntuProError):
    _formatted_msg = messages.ERROR_INVALID_BOOLEAN_CONFIG_VALUE


class InvalidPosIntConfigValue(UbuntuProError):
    _formatted_msg = messages.CLI_CONFIG_VALUE_MUST_BE_POS_INT


class InvalidURLConfigValue(UbuntuProError):
    _formatted_msg = messages.CONFIG_INVALID_URL


class InvalidFeatureYamlConfigValue(UbuntuProError):
    _formatted_msg = messages.CONFIG_NO_YAML_FILE


class InvalidProxyCombinationConfig(UbuntuProError):
    _msg = messages.ERROR_INVALID_PROXY_COMBINATION


class GPGKeyNotFound(UbuntuProError):
    _formatted_msg = messages.GPG_KEY_NOT_FOUND


class MissingDistroInfoFile(UbuntuProError):
    _msg = messages.MISSING_DISTRO_INFO_FILE


class MissingSeriesInDistroInfoFile(UbuntuProError):
    _formatted_msg = messages.MISSING_SERIES_IN_DISTRO_INFO_FILE


class RepoNoAptKey(UbuntuProError):
    _formatted_msg = messages.REPO_NO_APT_KEY


class RepoNoSuites(UbuntuProError):
    _formatted_msg = messages.REPO_NO_SUITES


class RepoPinFailNoOrigin(UbuntuProError):
    _formatted_msg = messages.REPO_PIN_FAIL_NO_ORIGIN


class NoHelpContent(UbuntuProError):
    _formatted_msg = messages.CLI_NO_HELP


class InvalidSecurityIssueIdFormat(UbuntuProError):
    _formatted_msg = messages.SECURITY_FIX_CLI_ISSUE_REGEX_FAIL


class InvalidArgChoice(UbuntuProError):
    _formatted_msg = messages.CLI_VALID_CHOICES


class GenericInvalidFormat(UbuntuProError):
    _formatted_msg = messages.CLI_EXPECTED_FORMAT


class RefreshConfigFailure(UbuntuProError):
    _msg = messages.REFRESH_CONFIG_FAILURE


class RefreshContractFailure(UbuntuProError):
    _msg = messages.REFRESH_CONTRACT_FAILURE


class RefreshMessagesFailure(UbuntuProError):
    _msg = messages.REFRESH_MESSAGES_FAILURE


class InvalidContractDeltasServiceType(UbuntuProError):
    _formatted_msg = messages.INVALID_CONTRACT_DELTAS_SERVICE_TYPE


class CLIJSONFormatRequireAssumeYes(UbuntuProError):
    _msg = messages.JSON_FORMAT_REQUIRE_ASSUME_YES


class CLIAttachTokenArgXORConfig(UbuntuProError):
    _msg = messages.ATTACH_TOKEN_ARG_XOR_CONFIG


class CLIAPIOptionsXORData(UbuntuProError):
    _msg = messages.API_ERROR_ARGS_AND_DATA_TOGETHER
