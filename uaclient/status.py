import enum
import sys

try:
    from typing import Any, Dict, List, Optional, Tuple, Union  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class TxtColor:
    OKGREEN = "\033[92m"
    DISABLEGREY = "\033[37m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


OKGREEN_CHECK = TxtColor.OKGREEN + "✔" + TxtColor.ENDC
FAIL_X = TxtColor.FAIL + "✘" + TxtColor.ENDC


@enum.unique
class ApplicationStatus(enum.Enum):
    """
    An enum to represent the current application status of an entitlement
    """

    ENABLED = object()
    DISABLED = object()


@enum.unique
class ContractStatus(enum.Enum):
    """
    An enum to represent whether a user is entitled to an entitlement

    (The value of each member is the string that will be used in status
    output.)
    """

    ENTITLED = "yes"
    UNENTITLED = "no"


@enum.unique
class ApplicabilityStatus(enum.Enum):
    """
    An enum to represent whether an entitlement could apply to this machine
    """

    APPLICABLE = object()
    INAPPLICABLE = object()


@enum.unique
class UserFacingAvailability(enum.Enum):
    """
    An enum representing whether a service could be available for a machine.

    'Availability' means whether a service is available to machines with this
    architecture, series and kernel. Whether a contract is entitled to use
    the specific service is determined by the contract level.

    This enum should only be used in display code, it should not be used in
    business logic.
    """

    AVAILABLE = "yes"
    UNAVAILABLE = "no"


@enum.unique
class UserFacingConfigStatus(enum.Enum):
    """
    An enum representing the user-visible config status of UA system.

    This enum will be used in display code and will be written to status.json
    """

    INACTIVE = "inactive"  # No UA config commands/daemons
    ACTIVE = "active"  # UA command is running
    REBOOTREQUIRED = "reboot-required"  # System Reboot required


@enum.unique
class UserFacingStatus(enum.Enum):
    """
    An enum representing the states we will display in status output.

    This enum should only be used in display code, it should not be used in
    business logic.
    """

    ACTIVE = "enabled"
    INACTIVE = "disabled"
    INAPPLICABLE = "n/a"
    UNAVAILABLE = "—"


ESSENTIAL = "essential"
STANDARD = "standard"
ADVANCED = "advanced"

# Colorized status output for terminal
STATUS_COLOR = {
    UserFacingStatus.ACTIVE.value: (
        TxtColor.OKGREEN + UserFacingStatus.ACTIVE.value + TxtColor.ENDC
    ),
    UserFacingStatus.INACTIVE.value: (
        TxtColor.FAIL + UserFacingStatus.INACTIVE.value + TxtColor.ENDC
    ),
    UserFacingStatus.INAPPLICABLE.value: (
        TxtColor.DISABLEGREY
        + UserFacingStatus.INAPPLICABLE.value
        + TxtColor.ENDC
    ),  # noqa: E501
    UserFacingStatus.UNAVAILABLE.value: (
        TxtColor.DISABLEGREY
        + UserFacingStatus.UNAVAILABLE.value
        + TxtColor.ENDC
    ),
    ContractStatus.ENTITLED.value: (
        TxtColor.OKGREEN + ContractStatus.ENTITLED.value + TxtColor.ENDC
    ),
    ContractStatus.UNENTITLED.value: (
        TxtColor.DISABLEGREY + ContractStatus.UNENTITLED.value + TxtColor.ENDC
    ),  # noqa: E501
    ESSENTIAL: TxtColor.OKGREEN + ESSENTIAL + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN + STANDARD + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN + ADVANCED + TxtColor.ENDC,
}

MESSAGE_SECURITY_FIX_RELEASE_STREAM = "A fix is available in {fix_stream}."
MESSAGE_SECURITY_UPDATE_NOT_INSTALLED = "The update is not yet installed."
MESSAGE_SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION = """\
The update is not installed because this system is not attached to a
subscription that covers these packages.
"""
MESSAGE_SECURITY_UPDATE_INSTALLED = "The update is already installed."
MESSAGE_SECURITY_ISSUE_RESOLVED = OKGREEN_CHECK + " {issue} is resolved."
MESSAGE_SECURITY_ISSUE_UNAFFECTED = (
    OKGREEN_CHECK + " {issue} does not affect your system."
)
MESSAGE_SECURITY_AFFECTED_PKGS = (
    "{count} affected package{plural_str} installed"
)
MESSAGE_USN_FIXED = "{issue} is addressed."
MESSAGE_CVE_FIXED = "{issue} is resolved."
MESSAGE_SECURITY_URL = (
    "{issue}: {title}\nhttps://ubuntu.com/security/{url_path}"
)
MESSAGE_APT_INSTALL_FAILED = "APT install failed."
MESSAGE_APT_UPDATE_FAILED = "APT update failed."
MESSAGE_APT_UPDATE_INVALID_URL_CONFIG = (
    "APT update failed to read APT config for the following URL{}:\n{}"
)
MESSAGE_APT_POLICY_FAILED = "Failure checking APT policy."
MESSAGE_APT_UPDATING_LISTS = "Updating package lists"
MESSAGE_CONNECTIVITY_ERROR = """\
Failed to connect to authentication server
Check your Internet connection and try again"""
LOG_CONNECTIVITY_ERROR_TMPL = MESSAGE_CONNECTIVITY_ERROR + ". {error}"
LOG_CONNECTIVITY_ERROR_WITH_URL_TMPL = (
    MESSAGE_CONNECTIVITY_ERROR + ". Failed to access URL: {url}. {error}"
)
MESSAGE_NONROOT_USER = "This command must be run as root (try using sudo)"
MESSAGE_ALREADY_DISABLED_TMPL = """\
{title} is not currently enabled\nSee: sudo ua status"""
MESSAGE_ENABLED_FAILED_TMPL = "Could not enable {title}."
MESSAGE_DISABLE_FAILED_TMPL = "Could not disable {title}."
MESSAGE_ENABLED_TMPL = "{title} enabled"
MESSAGE_ALREADY_ATTACHED = """\
This machine is already attached to '{account_name}'
To use a different subscription first run: sudo ua detach"""
MESSAGE_ALREADY_ENABLED_TMPL = """\
{title} is already enabled.\nSee: sudo ua status"""
MESSAGE_INAPPLICABLE_ARCH_TMPL = """\
{title} is not available for platform {arch}.
Supported platforms are: {supported_arches}"""
MESSAGE_INAPPLICABLE_SERIES_TMPL = """\
{title} is not available for Ubuntu {series}."""
MESSAGE_INAPPLICABLE_KERNEL_TMPL = """\
{title} is not available for kernel {kernel}.
Supported flavors are: {supported_kernels}"""
MESSAGE_INAPPLICABLE_KERNEL_VER_TMPL = """\
{title} is not available for kernel {kernel}.
Minimum kernel version required: {min_kernel}"""
MESSAGE_UNENTITLED_TMPL = """\
This subscription is not entitled to {title}.
For more information see: https://ubuntu.com/advantage"""
MESSAGE_UNABLE_TO_DETERMINE_CLOUD_TYPE = """\
Unable to determine auto-attach platform support
For more information see: https://ubuntu.com/advantage"""
MESSAGE_UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE = """\
Auto-attach image support is not available on {cloud_type}
See: https://ubuntu.com/advantage"""
MESSAGE_UNSUPPORTED_AUTO_ATTACH = """\
Auto-attach image support is not available on this image
See: https://ubuntu.com/advantage"""
MESSAGE_UNATTACHED = """\
This machine is not attached to a UA subscription.
See https://ubuntu.com/advantage"""
MESSAGE_MISSING_APT_URL_DIRECTIVE = """\
Ubuntu Advantage server provided no aptURL directive for {entitlement_name}"""
MESSAGE_NO_ACTIVE_OPERATIONS = """No Ubuntu Advantage operations are running"""
MESSAGE_LOCK_HELD = """Operation in progress: {lock_holder} (pid:{pid})"""
PROMPT_YES_NO = """Are you sure? (y/N) """
MESSAGE_LIVEPATCH_LTS_REBOOT_REQUIRED = (
    "Livepatch support requires a system reboot across LTS upgrade."
)
MESSAGE_FIPS_REBOOT_REQUIRED = (
    "FIPS support requires system reboot to complete configuration."
)
MESSAGE_FIPS_DISABLE_REBOOT_REQUIRED = (
    "Disabling FIPS requires system reboot to complete operation."
)
NOTICE_FIPS_MANUAL_DISABLE_URL = """\
FIPS kernel is running in a disabled state.
  To manually remove fips kernel: https://discourse.ubuntu.com/t/20738
"""
PROMPT_FIPS_PRE_ENABLE = (
    """\
Installation of additional packages are required to make this system FIPS
compliant.
"""
    + PROMPT_YES_NO
)
PROMPT_FIPS_UPDATES_PRE_ENABLE = (
    """\
This system will NOT be considered FIPS certified, but will include security
and bug fixes to the FIPS packages.
"""
    + PROMPT_YES_NO
)
PROMPT_FIPS_PRE_DISABLE = (
    """\
This will disable access to certified FIPS packages.
"""
    + PROMPT_YES_NO
)

STATUS_UNATTACHED_TMPL = "{name: <14}{available: <11}{description}"

STATUS_HEADER = "SERVICE       ENTITLED  STATUS    DESCRIPTION"
# The widths listed below for entitled and status are actually 9 characters
# less than reality because we colorize the values in entitled and status
# columns. Colorizing has an opening and closing set of unprintable characters
# that factor into formats len() calculations
STATUS_TMPL = "{name: <14}{entitled: <19}{status: <19}{description}"

MESSAGE_ATTACH_EXPIRED_TOKEN = """\
Expired token or contract. To obtain a new token visit: \
https://ubuntu.com/advantage"""
MESSAGE_ATTACH_INVALID_TOKEN = """\
Invalid token. See https://ubuntu.com/advantage"""
MESSAGE_ATTACH_REQUIRES_TOKEN = """\
Attach requires a token: sudo ua attach <TOKEN>
To obtain a token please visit: https://ubuntu.com/advantage"""
MESSAGE_ATTACH_FAILURE = """\
Failed to attach machine. See https://ubuntu.com/advantage"""
MESSAGE_ATTACH_FAILURE_DEFAULT_SERVICES = """\
Failed to enable default services, check: sudo ua status"""
MESSAGE_ATTACH_SUCCESS_TMPL = """\
This machine is now attached to '{contract_name}'
"""

MESSAGE_INVALID_SERVICE_OP_FAILURE_TMPL = """\
Cannot {operation} unknown service '{name}'.
{service_msg}"""
MESSAGE_UNEXPECTED_ERROR = """\
Unexpected error(s) occurred.
For more details, see the log: /var/log/ubuntu-advantage.log
To file a bug run: ubuntu-bug ubuntu-advantage-tools"""
MESSAGE_ENABLE_FAILURE_UNATTACHED_TMPL = """\
To use '{name}' you need an Ubuntu Advantage subscription
Personal and community subscriptions are available at no charge
See https://ubuntu.com/advantage"""
MESSAGE_ENABLE_BY_DEFAULT_TMPL = "Enabling default service {name}"
MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL = """\
A reboot is required to complete {operation}"""
MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL = """\
Service {name} is recommended by default. Run: sudo ua enable {name}"""
MESSAGE_DETACH_SUCCESS = "This machine is now detached"
MESSAGE_DETACH_AUTOMATION_FAILURE = "Unable to automatically detach machine"

MESSAGE_REFRESH_ENABLE = "One moment, checking your subscription first"
MESSAGE_REFRESH_SUCCESS = "Successfully refreshed your subscription"
MESSAGE_REFRESH_FAILURE = "Unable to refresh your subscription"

MESSAGE_INCOMPATIBLE_SERVICE = """\
{service_being_enabled} cannot be enabled with {incompatible_service}.
Disable {incompatible_service} and proceed to enable {service_being_enabled}? \
(y/N)"""

MESSAGE_INCOMPATIBLE_SERVICE_STOPS_ENABLE = """\
Cannot enable {service_being_enabled} when {incompatible_service} is enabled
"""

MESSAGE_FIPS_BLOCK_ON_CLOUD = """\
Ubuntu {series} does not provide {cloud} optimized FIPS kernel
For help see: https://ubuntu.com/advantage"""
ERROR_INVALID_CONFIG_VALUE = """\
Invalid value for {path_to_value} in /etc/ubuntu-advantage/uaclient.conf. \
Expected {expected_value}, found {value}."""
INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY = """\
Failed to find the machine token overlay file: {file_path}"""
ERROR_JSON_DECODING_IN_FILE = """\
Found error: {error} when reading json file: {file_path}"""

MESSAGE_SECURITY_APT_NON_ROOT = """\
Package fixes cannot be installed.
To install them, run this command as root (try using sudo)
"""


def colorize(string: str) -> str:
    """Return colorized string if using a tty, else original string."""
    return STATUS_COLOR.get(string, string) if sys.stdout.isatty() else string


def get_section_column_content(
    column_data: "List[Tuple[str, str]]", header: "Optional[str]" = None
) -> "List[str]":
    """Return a list of content lines to print to console for a section

    Content lines will be center-aligned based on max value length of first
    column.
    """
    content = [""]
    if header:
        content.append(header)
    template_length = max([len(pair[0]) for pair in column_data])
    if template_length > 0:
        template = "{{:>{}}}: {{}}".format(template_length)
        content.extend([template.format(*pair) for pair in column_data])
    else:
        # Then we have an empty "label" column and only descriptions
        content.extend([pair[1] for pair in column_data])
    return content


def format_tabular(status: "Dict[str, Any]") -> str:
    """Format status dict for tabular output."""
    if not status["attached"]:
        content = [
            STATUS_UNATTACHED_TMPL.format(
                name="SERVICE",
                available="AVAILABLE",
                description="DESCRIPTION",
            )
        ]
        for service in status["services"]:
            content.append(STATUS_UNATTACHED_TMPL.format(**service))
        content.extend(["", MESSAGE_UNATTACHED])
        return "\n".join(content)

    content = [STATUS_HEADER]
    for service_status in status["services"]:
        entitled = service_status["entitled"]
        descr_override = service_status.get("description_override")
        description = (
            descr_override if descr_override else service_status["description"]
        )
        fmt_args = {
            "name": service_status["name"],
            "entitled": colorize(entitled),
            "status": colorize(service_status["status"]),
            "description": description,
        }
        content.append(STATUS_TMPL.format(**fmt_args))
    tech_support_level = status["techSupportLevel"]

    if status.get("notices"):
        content.extend(
            get_section_column_content(
                status.get("notices") or [], header="NOTICES"
            )
        )
    content.append("\nEnable services with: ua enable <service>")
    pairs = [
        ("Account", status["account"]),
        ("Subscription", status["subscription"]),
    ]
    if status["origin"] != "free":
        pairs.append(("Valid until", str(status["expires"])))
        pairs.append(("Technical support level", colorize(tech_support_level)))
    content.extend(get_section_column_content(column_data=pairs))
    return "\n".join(content)
