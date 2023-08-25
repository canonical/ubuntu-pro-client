from typing import Dict, Optional  # noqa: F401

from uaclient.messages import urls


class NamedMessage:
    def __init__(
        self,
        name: str,
        msg: str,
        additional_info: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.msg = msg
        # we should use this field whenever we want to provide
        # extra information to the message. This is specially
        # useful if the message represents an error.
        self.additional_info = additional_info

    def __eq__(self, other):
        return (
            self.msg == other.msg
            and self.name == other.name
            and self.additional_info == other.additional_info
        )

    def __repr__(self):
        return "NamedMessage({}, {}, {})".format(
            self.name.__repr__(),
            self.msg.__repr__(),
            self.additional_info.__repr__(),
        )


class FormattedNamedMessage(NamedMessage):
    def __init__(self, name: str, msg: str):
        self.name = name
        self.tmpl_msg = msg

    def format(self, **msg_params):
        return NamedMessage(
            name=self.name, msg=self.tmpl_msg.format(**msg_params)
        )

    def __repr__(self):
        return "FormattedNamedMessage({}, {})".format(
            self.name.__repr__(),
            self.tmpl_msg.__repr__(),
        )


class TxtColor:
    OKGREEN = "\033[92m"
    DISABLEGREY = "\033[37m"
    INFOBLUE = "\033[94m"
    WARNINGYELLOW = "\033[93m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


OKGREEN_CHECK = TxtColor.OKGREEN + "✔" + TxtColor.ENDC
FAIL_X = TxtColor.FAIL + "✘" + TxtColor.ENDC
BLUE_INFO = TxtColor.INFOBLUE + "[info]" + TxtColor.ENDC

ERROR_INVALID_CONFIG_VALUE = """\
Invalid value for {path_to_value} in /etc/ubuntu-advantage/uaclient.conf. \
Expected {expected_value}, found {value}."""

SECURITY_FIX_ATTACH_PROMPT = """\
Choose: [S]ubscribe at {url} [A]ttach existing token [C]ancel""".format(
    url=urls.PRO_SUBSCRIBE
)
SECURITY_FIX_ENABLE_PROMPT = """\
Choose: [E]nable {} [C]ancel"""
SECURITY_FIX_RENEW_PROMPT = """\
Choose: [R]enew your subscription (at {url}) [C]ancel""".format(
    url=urls.PRO_DASHBOARD
)
SECURITY_FIX_RELEASE_STREAM = "A fix is available in {fix_stream}."
SECURITY_UPDATE_NOT_INSTALLED = "The update is not yet installed."
SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION = """\
The update is not installed because this system is not attached to a
subscription.
"""
SECURITY_UPDATE_NOT_INSTALLED_EXPIRED = """\
The update is not installed because this system is attached to an
expired subscription.
"""
SECURITY_SERVICE_DISABLED = """\
The update is not installed because this system does not have
{service} enabled.
"""
SECURITY_UPDATE_INSTALLED = "The update is already installed."
SECURITY_USE_PRO_TMPL = """\
For easiest security on {title}, use Ubuntu Pro instances.
Learn more at {cloud_specific_url}"""

SECURITY_ISSUE_RESOLVED = OKGREEN_CHECK + " {issue}{extra_info} is resolved."
SECURITY_ISSUE_NOT_RESOLVED = FAIL_X + " {issue}{extra_info} is not resolved."
SECURITY_ISSUE_UNAFFECTED = (
    OKGREEN_CHECK + " {issue}{extra_info} does not affect your system."
)
SECURITY_PKG_STILL_AFFECTED = FormattedNamedMessage(
    "security-pkg-still-affected",
    "{num_pkgs} package{s} {verb} still affected: {pkgs}",
)
SECURITY_AFFECTED_PKGS = (
    "{count} affected source package{plural_str} installed"
)
CVE_FIXED = "{issue} is resolved."
CVE_FIXED_BY_LIVEPATCH = (
    OKGREEN_CHECK
    + " {issue} is resolved by livepatch patch version: {version}."
)
SECURITY_DRY_RUN_UA_SERVICE_NOT_ENABLED = """\
{bold}Ubuntu Pro service: {{service}} is not enabled.
To proceed with the fix, a prompt would ask permission to automatically enable
this service.
{{{{ pro enable {{service}} }}}}{end_bold}""".format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)
SECURITY_DRY_RUN_UA_NOT_ATTACHED = """\
{bold}The machine is not attached to an Ubuntu Pro subscription.
To proceed with the fix, a prompt would ask for a valid Ubuntu Pro token.
{{ pro attach TOKEN }}{end_bold}""".format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)
SECURITY_DRY_RUN_UA_EXPIRED_SUBSCRIPTION = """\
{bold}The machine has an expired subscription.
To proceed with the fix, a prompt would ask for a new Ubuntu Pro
token to renew the subscription.
{{ pro detach --assume-yes }}
{{ pro attach NEW_TOKEN }}{end_bold}""".format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)
SECURITY_DRY_RUN_WARNING = """\
{bold}WARNING: The option --dry-run is being used.
No packages will be installed when running this command.{end_bold}""".format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)
SECURITY_UA_SERVICE_NOT_ENABLED = """\
Error: Ubuntu Pro service: {service} is not enabled.
Without it, we cannot fix the system."""
SECURITY_UA_SERVICE_NOT_ENTITLED = """\
Error: The current Ubuntu Pro subscription is not entitled to: {service}.
Without it, we cannot fix the system."""
SECURITY_UA_SERVICE_REQUIRED = """\
{service} is required for upgrade."""
SECURITY_UA_SERVICE_WITH_EXPIRED_SUB = """\
{service} is required for upgrade, but current subscription is expired."""
SECURITY_UA_SERVICE_NOT_ENABLED_SHORT = """\
{service} is required for upgrade, but it is not enabled."""
SECURITY_UA_APT_FAILURE = """\
APT failed to install the package.
"""
SECURITY_CVE_STATUS_NEEDED = """\
Sorry, no fix is available yet."""
SECURITY_CVE_STATUS_TRIAGE = """\
Ubuntu security engineers are investigating this issue."""
SECURITY_CVE_STATUS_PENDING = """\
A fix is coming soon. Try again tomorrow."""
SECURITY_CVE_STATUS_IGNORED = """\
Sorry, no fix is available."""
SECURITY_CVE_STATUS_DNE = """\
Source package does not exist on this release."""
SECURITY_CVE_STATUS_NOT_AFFECTED = """\
Source package is not affected on this release."""
SECURITY_CVE_STATUS_UNKNOWN = """\
UNKNOWN: {status}"""

SECURITY_FIXING_REQUESTED_USN = """\
Fixing requested {issue_id}"""
SECURITY_FIXING_RELATED_USNS = """\
Fixing related USNs:"""
SECURITY_RELATED_USNS = """\
Found related USNs:\n- {related_usns}"""
SECURITY_USN_SUMMARY = """\
Summary:"""
SECURITY_RELATED_USN_ERROR = """\
Even though a related USN failed to be fixed, note
that {{issue_id}} was fixed. Related USNs do not
affect the original USN. Learn more about the related
USNs, please refer to this page:

{url}
""".format(
    url=urls.PRO_CLIENT_DOCS_RELATED_USNS
)
SECURITY_FIX_CLI_ISSUE_REGEX_FAIL = (
    'Error: issue "{}" is not recognized.\n'
    'Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"'
)

APT_UPDATING_LISTS = "Updating package lists"
DISABLE_FAILED_TMPL = "Could not disable {title}."
ACCESS_ENABLED_TMPL = "{title} access enabled"
ENABLED_TMPL = "{title} enabled"
UNABLE_TO_DETERMINE_CLOUD_TYPE = """\
Unable to determine cloud platform."""
UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE = """\
Auto-attach image support is not available on {{cloud_type}}
See: {url}""".format(
    url=urls.PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES
)
UNSUPPORTED_AUTO_ATTACH = """\
Auto-attach image support is not available on this image
See: {url}""".format(
    url=urls.PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES
)

CLI_MAGIC_ATTACH_INIT = "Initiating attach operation..."
CLI_MAGIC_ATTACH_FAILED = "Failed to perform attach..."
CLI_MAGIC_ATTACH_SIGN_IN = """\
Please sign in to your Ubuntu Pro account at this link:
{url}
And provide the following code: {bold}{{user_code}}{end_bold}""".format(
    url=urls.PRO_ATTACH,
    bold=TxtColor.BOLD,
    end_bold=TxtColor.ENDC,
)
CLI_MAGIC_ATTACH_PROCESSING = "Attaching the machine..."

NO_ACTIVE_OPERATIONS = """No Ubuntu Pro operations are running"""
REBOOT_SCRIPT_FAILED = (
    "Failed running reboot_cmds script. See: /var/log/ubuntu-advantage.log"
)
LIVEPATCH_LTS_REBOOT_REQUIRED = (
    "Livepatch support requires a system reboot across LTS upgrade."
)
FIPS_REBOOT_REQUIRED_MSG = "Reboot to FIPS kernel required"
SNAPD_DOES_NOT_HAVE_WAIT_CMD = (
    "snapd does not have wait command.\n"
    "Enabling Livepatch can fail under this scenario\n"
    "Please, upgrade snapd if Livepatch enable fails and try again."
)
FIPS_INSTALL_OUT_OF_DATE = (
    "This FIPS install is out of date, run: sudo pro enable fips"
)
FIPS_DISABLE_REBOOT_REQUIRED = (
    "Disabling FIPS requires system reboot to complete operation."
)
FIPS_PACKAGE_NOT_AVAILABLE = "{service} {pkg} package could not be installed"
FIPS_RUN_APT_UPGRADE = """\
Please run `apt upgrade` to ensure all FIPS packages are updated to the correct
version.
"""
ATTACH_SUCCESS_TMPL = """\
This machine is now attached to '{contract_name}'
"""
ATTACH_SUCCESS_NO_CONTRACT_NAME = """\
This machine is now successfully attached'
"""

ENABLE_BY_DEFAULT_TMPL = "Enabling default service {name}"
ENABLE_REBOOT_REQUIRED_TMPL = """\
A reboot is required to complete {operation}."""
ENABLE_BY_DEFAULT_MANUAL_TMPL = """\
Service {name} is recommended by default. Run: sudo pro enable {name}"""
DETACH_SUCCESS = "This machine is now detached."

REFRESH_CONTRACT_ENABLE = "One moment, checking your subscription first"
REFRESH_CONTRACT_SUCCESS = "Successfully refreshed your subscription."
REFRESH_CONTRACT_FAILURE = "Unable to refresh your subscription"
REFRESH_CONFIG_SUCCESS = "Successfully processed your pro configuration."
REFRESH_CONFIG_FAILURE = "Unable to process uaclient.conf"
REFRESH_MESSAGES_SUCCESS = (
    "Successfully updated Ubuntu Pro related APT and MOTD messages."
)
REFRESH_MESSAGES_FAILURE = (
    "Unable to update Ubuntu Pro related APT and MOTD messages."
)

INCOMPATIBLE_SERVICE = """\
{service_being_enabled} cannot be enabled with {incompatible_service}.
Disable {incompatible_service} and proceed to enable {service_being_enabled}? \
(y/N) """
DISABLING_INCOMPATIBLE_SERVICE = "Disabling incompatible service: {}"

REQUIRED_SERVICE = """\
{service_being_enabled} cannot be enabled with {required_service} disabled.
Enable {required_service} and proceed to enable {service_being_enabled}? \
(y/N) """
ENABLING_REQUIRED_SERVICE = "Enabling required service: {}"

DEPENDENT_SERVICE = """\
{dependent_service} depends on {service_being_disabled}.
Disable {dependent_service} and proceed to disable {service_being_disabled}? \
(y/N) """

DISABLING_DEPENDENT_SERVICE = """\
Disabling dependent service: {required_service}"""

SECURITY_APT_NON_ROOT = """\
Package fixes cannot be installed.
To install them, run this command as root (try using sudo)"""

# BEGIN MOTD and APT command messaging

CONTRACT_EXPIRES_SOON_MOTD = """\
CAUTION: Your Ubuntu Pro subscription will expire in {{remaining_days}} days.
Renew your subscription at {url} to ensure
continued security coverage for your applications.

""".format(
    url=urls.PRO_DASHBOARD
)

CONTRACT_EXPIRED_GRACE_PERIOD_MOTD = """\
CAUTION: Your Ubuntu Pro subscription expired on {{expired_date}}.
Renew your subscription at {url} to ensure
continued security coverage for your applications.
Your grace period will expire in {{remaining_days}} days.

""".format(
    url=urls.PRO_DASHBOARD
)

CONTRACT_EXPIRED_MOTD_PKGS = """\
*Your Ubuntu Pro subscription has EXPIRED*
{{pkg_num}} additional security update(s) require Ubuntu Pro with '{{service}}' enabled.
Renew your service at {url}

""".format(  # noqa: E501
    url=urls.PRO_DASHBOARD
)  # noqa: E501

CONTRACT_EXPIRED_MOTD_NO_PKGS = """\
*Your Ubuntu Pro subscription has EXPIRED*
Renew your service at {url}

""".format(
    url=urls.PRO_DASHBOARD
)

CONTRACT_EXPIRES_SOON_APT_NEWS = """\
CAUTION: Your Ubuntu Pro subscription will expire in {{remaining_days}} days.
Renew your subscription at {url} to ensure
continued security coverage for your applications.""".format(
    url=urls.PRO_DASHBOARD
)
CONTRACT_EXPIRED_GRACE_PERIOD_APT_NEWS = """\
CAUTION: Your Ubuntu Pro subscription expired on {{expired_date}}.
Renew your subscription at {url} to ensure
continued security coverage for your applications.
Your grace period will expire in {{remaining_days}} days.""".format(
    url=urls.PRO_DASHBOARD
)
CONTRACT_EXPIRED_APT_NEWS = """\
*Your Ubuntu Pro subscription has EXPIRED*
Renew your service at {url}""".format(
    url=urls.PRO_DASHBOARD
)

# END MOTD and APT command messaging

APT_PROXY_CONFIG_HEADER = """\
/*
 * Autogenerated by ubuntu-advantage-tools
 * Do not edit this file directly
 *
 * To change what ubuntu-advantage-tools sets, use the `pro config set`
 * or the `pro config unset` commands to set/unset either:
 *      global_apt_http_proxy and global_apt_https_proxy
 * for a global apt proxy
 * or
 *      ua_apt_http_proxy and ua_apt_https_proxy
 * for an apt proxy that only applies to Ubuntu Pro related repos.
 */
"""

SETTING_SERVICE_PROXY = "Setting {service} proxy"

PROXY_DETECTED_BUT_NOT_CONFIGURED = """\
No proxy set in config; however, proxy is configured for: {{services}}.
See {url} for more information on pro proxy configuration.
""".format(
    url=urls.PRO_CLIENT_DOCS_PROXY_CONFIG
)

FIPS_BLOCK_ON_CLOUD = FormattedNamedMessage(
    "cloud-non-optimized-fips-kernel",
    """\
Ubuntu {{series}} does not provide {{cloud}} optimized FIPS kernel
For help see: {url}""".format(
        url=urls.PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES
    ),
)
UNATTACHED = NamedMessage(
    "unattached",
    """\
This machine is not attached to an Ubuntu Pro subscription.
See {url}""".format(
        url=urls.PRO_HOME_PAGE
    ),
)

VALID_SERVICE_FAILURE_UNATTACHED = FormattedNamedMessage(
    "valid-service-failure-unattached",
    """\
To use '{{valid_service}}' you need an Ubuntu Pro subscription
Personal and community subscriptions are available at no charge
See {url}""".format(
        url=urls.PRO_HOME_PAGE
    ),
)

INVALID_SERVICE_OP_FAILURE = FormattedNamedMessage(
    "invalid-service-or-failure",
    """\
Cannot {operation} unknown service '{invalid_service}'.
{service_msg}""",
)

MIXED_SERVICES_FAILURE_UNATTACHED = FormattedNamedMessage(
    "mixed-services-failure-unattached",
    INVALID_SERVICE_OP_FAILURE.tmpl_msg
    + "\n"
    + VALID_SERVICE_FAILURE_UNATTACHED.tmpl_msg,
)

FAILED_DISABLING_DEPENDENT_SERVICE = FormattedNamedMessage(
    "failed-disabling-dependent-service",
    """\
Cannot disable dependent service: {required_service}{error}""",
)

DEPENDENT_SERVICE_STOPS_DISABLE = FormattedNamedMessage(
    "depedent-service-stops-disable",
    """\
Cannot disable {service_being_disabled} when {dependent_service} is enabled.
""",
)

ERROR_ENABLING_REQUIRED_SERVICE = FormattedNamedMessage(
    "error-enabling-required-service",
    "Cannot enable required service: {service}{error}",
)

REQUIRED_SERVICE_STOPS_ENABLE = FormattedNamedMessage(
    "required-service-stops-enable",
    """\
Cannot enable {service_being_enabled} when {required_service} is disabled.
""",
)

INCOMPATIBLE_SERVICE_STOPS_ENABLE = FormattedNamedMessage(
    "incompatible-service-stops-enable",
    """\
Cannot enable {service_being_enabled} when \
{incompatible_service} is enabled.""",
)

SERVICE_NOT_CONFIGURED = FormattedNamedMessage(
    "service-not-configured", "{title} is not configured"
)

SERVICE_IS_ACTIVE = FormattedNamedMessage(
    "service-is-active", "{title} is active"
)

NO_APT_URL_FOR_SERVICE = FormattedNamedMessage(
    "no-apt-url-for-service", "{title} does not have an aptURL directive"
)

ALREADY_DISABLED = FormattedNamedMessage(
    "service-already-disabled",
    """\
{title} is not currently enabled\nSee: sudo pro status""",
)

ALREADY_ENABLED = FormattedNamedMessage(
    "service-already-enabled",
    """\
{title} is already enabled.\nSee: sudo pro status""",
)

ENABLED_FAILED = FormattedNamedMessage(
    "enable-failed", "Could not enable {title}."
)

UNENTITLED = FormattedNamedMessage(
    "subscription-not-entitled-to-service",
    """\
This subscription is not entitled to {{title}}
View your subscription at: {url}""".format(
        url=urls.PRO_DASHBOARD
    ),
)

SERVICE_NOT_ENTITLED = FormattedNamedMessage(
    "service-not-entitled", "{title} is not entitled"
)

INAPPLICABLE_KERNEL_VER = FormattedNamedMessage(
    "inapplicable-kernel-version",
    """\
{title} is not available for kernel {kernel}.
Minimum kernel version required: {min_kernel}.""",
)

INAPPLICABLE_KERNEL = FormattedNamedMessage(
    "inapplicable-kernel",
    """\
{title} is not available for kernel {kernel}.
Supported flavors are: {supported_kernels}.""",
)

INAPPLICABLE_SERIES = FormattedNamedMessage(
    "inapplicable-series",
    """\
{title} is not available for Ubuntu {series}.""",
)

INAPPLICABLE_ARCH = FormattedNamedMessage(
    "inapplicable-arch",
    """\
{title} is not available for platform {arch}.
Supported platforms are: {supported_arches}.""",
)

INAPPLICABLE_VENDOR_NAME = FormattedNamedMessage(
    "inapplicable-vendor-name",
    """\
{title} is not available for CPU vendor {vendor}.
Supported CPU vendors are: {supported_vendors}.""",
)

NO_ENTITLEMENT_AFFORDANCES_CHECKED = NamedMessage(
    "no-entitlement-affordances-checked", "no entitlement affordances checked"
)

NOT_SETTING_PROXY_INVALID_URL = FormattedNamedMessage(
    "proxy-invalid-url", '"{proxy}" is not a valid url. Not setting as proxy.'
)

NOT_SETTING_PROXY_NOT_WORKING = FormattedNamedMessage(
    "proxy-not-working", '"{proxy}" is not working. Not setting as proxy.'
)

ATTACH_INVALID_TOKEN = NamedMessage(
    "attach-invalid-token",
    "Invalid token. See {url}".format(url=urls.PRO_DASHBOARD),
)

MAGIC_ATTACH_TOKEN_ALREADY_ACTIVATED = NamedMessage(
    "magic-attach-token-already-activated",
    "The magic attach token is already activated.",
)

MAGIC_ATTACH_TOKEN_ERROR = NamedMessage(
    "magic-attach-token-error",
    "The magic attach token is invalid, has expired or never existed",
)

MAGIC_ATTACH_UNAVAILABLE = NamedMessage(
    "magic-attach-service-unavailable",
    "Service unavailable, please try again later.",
)

MAGIC_ATTACH_INVALID_PARAM = FormattedNamedMessage(
    "magic-attach-invalid-param",
    "This attach flow does not support {param} with value: {value}",
)

APT_UPDATE_INVALID_REPO = FormattedNamedMessage(
    "apt-update-invalid-repo", "APT update failed.\n{repo_msg}"
)

APT_UPDATE_INVALID_URL_CONFIG = FormattedNamedMessage(
    "apt-update-invalid-url-config",
    (
        "APT update failed to read APT config for the following "
        "URL{plural}:\n{failed_repos}."
    ),
)

APT_PROCESS_CONFLICT = NamedMessage(
    "apt-process-conflict", "Another process is running APT."
)

APT_UPDATE_PROCESS_CONFLICT = NamedMessage(
    "apt-update-failed-process-conflict",
    "APT update failed. " + APT_PROCESS_CONFLICT.msg,
)

APT_UPDATE_FAILED = NamedMessage("apt-update-failed", "APT Update failed")

APT_INSTALL_PROCESS_CONFLICT = FormattedNamedMessage(
    "apt-install-failed-process-conflict",
    "{header_msg}APT install failed. " + APT_PROCESS_CONFLICT.msg,
)

APT_INSTALL_INVALID_REPO = FormattedNamedMessage(
    "apt-install-invalid-repo", "{header_msg}APT install failed.{repo_msg}"
)

CANNOT_INSTALL_SNAPD = NamedMessage(
    "cannot-install-snapd", "Failed to install snapd on the system"
)

SSL_VERIFICATION_ERROR_CA_CERTIFICATES = FormattedNamedMessage(
    "ssl-verification-error-ca-certificate",
    """\
Failed to access URL: {url}
Cannot verify certificate of server
Please install "ca-certificates" and try again.""",
)

SSL_VERIFICATION_ERROR_OPENSSL_CONFIG = FormattedNamedMessage(
    "ssl-verification-error-openssl-config",
    """\
Failed to access URL: {url}
Cannot verify certificate of server
Please check your openssl configuration.""",
)

MISSING_APT_URL_DIRECTIVE = FormattedNamedMessage(
    "missing-apt-url-directive",
    """\
Ubuntu Pro server provided no aptURL directive for {entitlement_name}""",
)

ALREADY_ATTACHED = FormattedNamedMessage(
    name="already-attached",
    msg=(
        "This machine is already attached to '{account_name}'\n"
        "To use a different subscription first run: sudo pro detach."
    ),
)

CONNECTIVITY_ERROR = NamedMessage(
    "connectivity-error",
    """\
Failed to connect to authentication server
Check your Internet connection and try again.""",
)

NONROOT_USER = NamedMessage(
    "nonroot-user", "This command must be run as root (try using sudo)."
)

ERROR_INSTALLING_LIVEPATCH = FormattedNamedMessage(
    "error-installing-livepatch",
    "Unable to install Livepatch client: {error_msg}",
)

APT_POLICY_FAILED = NamedMessage(
    "apt-policy-failed", "Failure checking APT policy."
)

ATTACH_FORBIDDEN_EXPIRED = FormattedNamedMessage(
    "attach-forbidden-expired",
    """\
Contract \"{contract_id}\" expired on {date}""",
)

ATTACH_FORBIDDEN_NOT_YET = FormattedNamedMessage(
    "attach-forbidden-not-yet",
    """\
Contract \"{contract_id}\" is not effective until {date}""",
)
ATTACH_FORBIDDEN_NEVER = FormattedNamedMessage(
    "attach-forbidden-never",
    """\
Contract \"{contract_id}\" has never been effective""",
)

ATTACH_FORBIDDEN = FormattedNamedMessage(
    "attach-forbidden",
    """\
Attach denied:
{{reason}}
Visit {url} to manage contract tokens.""".format(
        url=urls.PRO_DASHBOARD
    ),
)

ATTACH_EXPIRED_TOKEN = NamedMessage(
    "attach-experied-token",
    """\
Expired token or contract. To obtain a new token visit: {url}""".format(
        url=urls.PRO_DASHBOARD
    ),
)

ATTACH_TOKEN_ARG_XOR_CONFIG = NamedMessage(
    "attach-token-xor-config",
    """\
Do not pass the TOKEN arg if you are using --attach-config.
Include the token in the attach-config file instead.
    """,
)

ATTACH_FAILURE = NamedMessage(
    "attach-failure",
    "Failed to attach machine. See {url}".format(url=urls.PRO_DASHBOARD),
)

ATTACH_FAILURE_DEFAULT_SERVICES = NamedMessage(
    "attach-failure-default-service",
    """\
Failed to enable default services, check: sudo pro status""",
)

INVALID_CONTRACT_DELTAS_SERVICE_TYPE = FormattedNamedMessage(
    "invalid-contract-deltas-service-type",
    "Could not determine contract delta service type {orig} {new}",
)

LOCK_HELD = FormattedNamedMessage(
    "lock-held", """Operation in progress: {lock_holder} (pid:{pid})"""
)

LOCK_HELD_ERROR = FormattedNamedMessage(
    "lock-held-error",
    """\
Unable to perform: {lock_request}.
"""
    + LOCK_HELD.tmpl_msg,
)

UNEXPECTED_ERROR = NamedMessage(
    "unexpected-error",
    """\
Unexpected error(s) occurred.
For more details, see the log: /var/log/ubuntu-advantage.log
To file a bug run: ubuntu-bug ubuntu-advantage-tools""",
)

ATTACH_CONFIG_READ_ERROR = FormattedNamedMessage(
    "attach-config-read-error", "Error while reading {config_name}: {error}"
)

JSON_FORMAT_REQUIRE_ASSUME_YES = NamedMessage(
    "json-format-require-assume-yes",
    """\
json formatted response requires --assume-yes flag.""",
)

LIVEPATCH_NOT_ENABLED = NamedMessage(
    "livepatch-not-enabled", "canonical-livepatch snap is not installed."
)

SERVICE_ERROR_INSTALL_ON_CONTAINER = FormattedNamedMessage(
    "service-error-install-on-container",
    "Cannot install {title} on a container.",
)

LIVEPATCH_ERROR_WHEN_FIPS_ENABLED = NamedMessage(
    "livepatch-error-when-fips-enabled",
    "Cannot enable Livepatch when FIPS is enabled.",
)

FIPS_REBOOT_REQUIRED = NamedMessage(
    "fips-reboot-required", "Reboot to FIPS kernel required"
)

FIPS_SYSTEM_REBOOT_REQUIRED = NamedMessage(
    "fips-system-reboot-required",
    "FIPS support requires system reboot to complete configuration.",
)

FIPS_ERROR_WHEN_FIPS_UPDATES_ENABLED = FormattedNamedMessage(
    "fips-enable-when-fips-updates-enabled",
    "Cannot enable {fips} when {fips_updates} is enabled.",
)

FIPS_PROC_FILE_ERROR = FormattedNamedMessage(
    "fips-proc-file-error", "{file_name} is not set to 1"
)

FIPS_ERROR_WHEN_FIPS_UPDATES_ONCE_ENABLED = FormattedNamedMessage(
    "fips-enable-when-fips-updates-once-enabled",
    "Cannot enable {fips} because {fips_updates} was once enabled.",
)

FIPS_UPDATES_INVALIDATES_FIPS = NamedMessage(
    "fips-updates-invalidates-fips",
    "FIPS cannot be enabled if FIPS Updates has ever been enabled because"
    " FIPS Updates installs security patches that aren't officially"
    " certified.",
)
FIPS_INVALIDATES_FIPS_UPDATES = NamedMessage(
    "fips-invalidates-fips-updates",
    "FIPS Updates cannot be enabled if FIPS is enabled."
    " FIPS Updates installs security patches that aren't officially"
    " certified.",
)
LIVEPATCH_INVALIDATES_FIPS = NamedMessage(
    "livepatch-invalidates-fips",
    "Livepatch cannot be enabled while running the official FIPS"
    " certified kernel. If you would like a FIPS compliant kernel"
    " with additional bug fixes and security updates, you can use"
    " the FIPS Updates service with Livepatch.",
)
REALTIME_FIPS_INCOMPATIBLE = NamedMessage(
    "realtime-fips-incompatible",
    "Realtime and FIPS require different kernels, so you cannot enable"
    " both at the same time.",
)
REALTIME_FIPS_UPDATES_INCOMPATIBLE = NamedMessage(
    "realtime-fips-updates-incompatible",
    "Realtime and FIPS Updates require different kernels, so you cannot enable"
    " both at the same time.",
)
REALTIME_LIVEPATCH_INCOMPATIBLE = NamedMessage(
    "realtime-livepatch-incompatible",
    "Livepatch is not currently supported for the Real-time kernel.",
)
REALTIME_VARIANT_INCOMPATIBLE = FormattedNamedMessage(
    "realtime-variant-incompatible",
    "{service} cannot be enabled together with {variant}",
)
REALTIME_PROMPT = """\
The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated.

{bold}\
This will change your kernel. To revert to your original kernel, you will need
to make the change manually.\
{end_bold}

Do you want to continue? [ default = Yes ]: (Y/n) """.format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)
REALTIME_PRE_DISABLE_PROMPT = """\
This will remove the boot order preference for the Real-time kernel and
disable updates to the Real-time kernel.

This will NOT fully remove the kernel from your system.

After this operation is complete you must:
  - Ensure a different kernel is installed and configured to boot
  - Reboot into that kernel
  - Fully remove the realtime kernel packages from your system
      - This might look something like `apt remove linux*realtime`,
        but you must ensure this is correct before running it.

Are you sure? (y/N) """

REALTIME_ERROR_INSTALL_ON_CONTAINER = NamedMessage(
    "realtime-error-install-on-container",
    "Cannot install Real-time kernel on a container.",
)

GCP_SERVICE_ACCT_NOT_ENABLED_ERROR = NamedMessage(
    "gcp-pro-service-account-not-enabled",
    """\
Failed to attach machine
{{error_msg}}
For more information, see {url}""".format(
        url=urls.GCP_SERVICE_ACCOUNT_DOCS
    ),
)

SETTING_SERVICE_PROXY_SCOPE = "Setting {scope} APT proxy"
WARNING_APT_PROXY_SETUP = """\
Warning: apt_{protocol_type}_proxy has been renamed to global_apt_{protocol_type}_proxy."""  # noqa: E501
WARNING_APT_PROXY_OVERWRITE = """\
Warning: Setting the {current_proxy} proxy will overwrite the {previous_proxy}
proxy previously set via `pro config`.
"""
WARNING_DEPRECATED_APT_HTTP = """\
Using deprecated "apt_http_proxy" config field.
Please migrate to using "global_apt_http_proxy"
"""
WARNING_DEPRECATED_APT_HTTPS = """\
Using deprecated "apt_https_proxy" config field.
Please migrate to using "global_apt_https_proxy"
"""

ERROR_PROXY_CONFIGURATION = """\
Error: Setting global apt proxy and pro scoped apt proxy
at the same time is unsupported.
Cancelling config process operation.
"""

NOTICE_FIPS_MANUAL_DISABLE_URL = """\
FIPS kernel is running in a disabled state.
  To manually remove fips kernel: {url}
""".format(
    url=urls.PRO_CLIENT_DOCS_REMOVE_FIPS
)
NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD = """\
Warning: FIPS kernel is not optimized for your specific cloud.
To fix it, run the following commands:

    1. sudo pro disable fips
    2. sudo apt-get remove ubuntu-fips
    3. sudo pro enable fips --assume-yes
    4. sudo reboot
"""

PROMPT_YES_NO = """Are you sure? (y/N) """
PROMPT_FIPS_PRE_ENABLE = (
    """\
This will install the FIPS packages. The Livepatch service will be unavailable.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)
PROMPT_FIPS_UPDATES_PRE_ENABLE = (
    """\
This will install the FIPS packages including security updates.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)
PROMPT_FIPS_CONTAINER_PRE_ENABLE = (
    """\
Warning: Enabling {title} in a container.
         This will install the FIPS packages but not the kernel.
         This container must run on a host with {title} enabled to be
         compliant.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)

PROMPT_FIPS_PRE_DISABLE = (
    """\
This will disable the FIPS entitlement but the FIPS packages will remain installed.
"""  # noqa
    + PROMPT_YES_NO
)

PROMPT_ENTER_TOKEN = """\
Enter your token (from {url}) to attach this system:""".format(
    url=urls.PRO_DASHBOARD
)
PROMPT_EXPIRED_ENTER_TOKEN = """\
Enter your new token to renew Ubuntu Pro subscription on this system:"""

NOTICE_REFRESH_CONTRACT_WARNING = """\
A change has been detected in your contract.
Please run `sudo pro refresh`."""

API_BAD_ARGS_FORMAT = FormattedNamedMessage(
    name="api-args-wrong-format", msg="'{arg}' is not formatted as 'key=value'"
)
API_INVALID_ENDPOINT = FormattedNamedMessage(
    name="api-invalid-endpoint", msg="'{endpoint}' is not a valid endpoint"
)
API_UNKNOWN_ARG = FormattedNamedMessage(
    name="api-unknown-argument", msg="Ignoring unknown argument '{arg}'"
)
API_MISSING_ARG = FormattedNamedMessage(
    name="api-missing-argument",
    msg="Missing argument '{arg}' for endpoint {endpoint}",
)
API_NO_ARG_FOR_ENDPOINT = FormattedNamedMessage(
    name="api-no-argument-for-endpoint", msg="{endpoint} accepts no arguments"
)

INVALID_FILE_FORMAT = FormattedNamedMessage(
    name="invalid-file-format", msg="{file_name} is not valid {file_format}"
)

WARN_NEW_VERSION_AVAILABLE = FormattedNamedMessage(
    name="new-version-available",
    msg="A new version of the client is available: {version}. \
Please upgrade to the latest version to get the new features \
and bug fixes.",
)
WARN_NEW_VERSION_AVAILABLE_CLI = (
    "\n"
    + BLUE_INFO
    + """\
 A new version is available: {version}
Please run:
    sudo apt-get install ubuntu-advantage-tools
to get the latest version with new features and bug fixes."""
)

INVALID_PRO_IMAGE = FormattedNamedMessage(
    name="invalid-pro-image", msg="Error on Pro Image:\n{msg}"
)

ENABLE_ACCESS_ONLY_NOT_SUPPORTED = FormattedNamedMessage(
    name="enable-access-only-not-supported",
    msg="{title} does not support being enabled with --access-only",
)

MISSING_DISTRO_INFO_FILE = "Can't load the distro-info database."
MISSING_SERIES_IN_DISTRO_INFO_FILE = (
    "Can't find series {} in the distro-info database."
)

# Security Status output

SS_SUMMARY_TOTAL = "{count} packages installed:"
SS_SUMMARY_ARCHIVE = (
    "{offset}{count} package{plural} from Ubuntu {repository} repository"
)
SS_SUMMARY_THIRD_PARTY_SN = "{offset}{count} package from a third party"
SS_SUMMARY_THIRD_PARTY_PL = "{offset}{count} packages from third parties"
SS_SUMMARY_UNAVAILABLE = (
    "{offset}{count} package{plural} no longer available for download"
)

SS_HELP_CALL = """\
To get more information about the packages, run
    pro security-status --help
for a list of available options."""

SS_UPDATE_CALL = """\
 Make sure to run
    sudo apt-get update
to get the latest package information from apt."""
SS_UPDATE_DAYS = (
    "The system apt information was updated {days} day(s) ago."
    + SS_UPDATE_CALL
)
SS_UPDATE_UNKNOWN = "The system apt cache may be outdated." + SS_UPDATE_CALL

SS_INTERIM_SUPPORT = "Main/Restricted packages receive updates until {date}."
SS_LTS_SUPPORT = """\
This machine is receiving security patching for Ubuntu Main/Restricted
repository until {date}."""

SS_IS_ATTACHED = (
    "This machine is{not_attached} attached to an Ubuntu Pro subscription."
)

SS_THIRD_PARTY = """\
Packages from third parties are not provided by the official Ubuntu
archive, for example packages from Personal Package Archives in Launchpad."""
SS_UNAVAILABLE = """\
Packages that are not available for download may be left over from a
previous release of Ubuntu, may have been installed directly from a
.deb file, or are from a source which has been disabled."""

SS_NO_SECURITY_COVERAGE = """\
This machine is NOT receiving security patches because the LTS period has ended
and esm-infra is not enabled."""

SS_SERVICE_ADVERTISE = """\
Ubuntu Pro with '{service}' enabled provides security updates for
{repository} packages until {year}."""
SS_SERVICE_ADVERTISE_COUNTS = (
    " There {verb} {updates} pending security update{plural}."
)

SS_SERVICE_ENABLED = """\
{repository} packages are receiving security updates from
Ubuntu Pro with '{service}' enabled until {year}."""
SS_SERVICE_ENABLED_COUNTS = """\
 You have received {updates} security
update{plural}."""

SS_SERVICE_COMMAND = "Enable {service} with: pro enable {service}"
SS_LEARN_MORE = """\
Try Ubuntu Pro with a free personal subscription on up to 5 machines.
Learn more at {url}
""".format(
    url=urls.PRO_HOME_PAGE
)

SS_SHOW_HINT = """\
For example, run:
    apt-cache show {package}
to learn more about that package."""

SS_NO_THIRD_PARTY = "You have no packages installed from a third party."
SS_NO_UNAVAILABLE = (
    "You have no packages installed that are no longer available."
)
SS_NO_INTERIM_PRO_SUPPORT = "Ubuntu Pro is not available for non-LTS releases."

SS_SERVICE_HELP = "Run 'pro help {service}' to learn more"

SS_UPDATES_AVAILABLE = "Installed packages with an available {service} update:"
SS_UPDATES_INSTALLED = "Installed packages with an {service} update applied:"
SS_OTHER_PACKAGES = "{prefix} packages covered by {service}:"
SS_PACKAGES_HEADER = "Packages:"

ENTITLEMENT_NOT_FOUND = FormattedNamedMessage(
    "entitlement-not-found",
    'could not find entitlement named "{name}"',
)

ENTITLEMENTS_NOT_ENABLED_ERROR = NamedMessage(
    "entitlements-not-enabled",
    "failed to enable some services",
)

AUTO_ATTACH_DISABLED_ERROR = NamedMessage(
    "auto-attach-disabled",
    "features.disable_auto_attach set in config",
)

AUTO_ATTACH_RUNNING = (
    "Currently attempting to automatically attach this machine to "
    "Ubuntu Pro services"
)

# prefix used for removing notices
AUTO_ATTACH_RETRY_NOTICE_PREFIX = """\
Failed to automatically attach to Ubuntu Pro services"""
AUTO_ATTACH_RETRY_NOTICE = (
    AUTO_ATTACH_RETRY_NOTICE_PREFIX
    + """\
 {num_attempts} time(s).
The failure was due to: {reason}.
The next attempt is scheduled for {next_run_datestring}.
You can try manually with `sudo pro auto-attach`."""
)

AUTO_ATTACH_RETRY_TOTAL_FAILURE_NOTICE = (
    AUTO_ATTACH_RETRY_NOTICE_PREFIX
    + """\
 {num_attempts} times.
The most recent failure was due to: {reason}.
Try re-launching the instance or report this issue by running `ubuntu-bug ubuntu-advantage-tools`
You can try manually with `sudo pro auto-attach`."""  # noqa: E501
)

RETRY_ERROR_DETAIL_INVALID_PRO_IMAGE = (
    'Canonical servers did not recognize this machine as Ubuntu Pro: "{}"'
)
RETRY_ERROR_DETAIL_NON_AUTO_ATTACH_IMAGE = (
    "Canonical servers did not recognize this image as Ubuntu Pro"
)
RETRY_ERROR_DETAIL_LOCK_HELD = "the pro lock was held by pid {pid}"
RETRY_ERROR_DETAIL_CONTRACT_API_ERROR = 'an error from Canonical servers: "{}"'
RETRY_ERROR_DETAIL_CONNECTIVITY_ERROR = "a connectivity error"
RETRY_ERROR_DETAIL_URL_ERROR_URL = "an error while reaching {url}"
RETRY_ERROR_DETAIL_UNKNOWN = "an unknown error"

INCORRECT_TYPE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-type",
    "Expected value with type {expected_type} but got type: {got_type}",
)
INCORRECT_LIST_ELEMENT_TYPE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-list-element-type",
    "Got value with incorrect type at index {index}: {nested_msg}",
)
INCORRECT_FIELD_TYPE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-field-type",
    'Got value with incorrect type for field "{key}": {nested_msg}',
)
INCORRECT_ENUM_VALUE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-enum-value",
    "Value provided was not found in {enum_class}'s allowed: value: {values}",
)

LIVEPATCH_KERNEL_UPGRADE_REQUIRED = NamedMessage(
    name="livepatch-kernel-upgrade-required",
    msg="""\
The running kernel has reached the end of its active livepatch window.
Please upgrade the kernel with apt and reboot for continued livepatch support.""",  # noqa: E501
)
LIVEPATCH_KERNEL_EOL = FormattedNamedMessage(
    name="livepatch-kernel-eol",
    msg="""\
The current kernel ({{version}}, {{arch}}) has reached the end of its livepatch support.
Supported kernels are listed here: {url}
Either switch to a supported kernel or `pro disable livepatch` to dismiss this warning.""".format(  # noqa: E501
        url=urls.LIVEPATCH_SUPPORTED_KERNELS
    ),  # noqa: E501
)
LIVEPATCH_KERNEL_NOT_SUPPORTED = FormattedNamedMessage(
    name="livepatch-kernel-not-supported",
    msg="""\
The current kernel ({{version}}, {{arch}}) is not supported by livepatch.
Supported kernels are listed here: {url}
Either switch to a supported kernel or `pro disable livepatch` to dismiss this warning.""".format(  # noqa: E501
        url=urls.LIVEPATCH_SUPPORTED_KERNELS
    ),  # noqa: E501
)
LIVEPATCH_KERNEL_NOT_SUPPORTED_DESCRIPTION = "Current kernel is not supported"
LIVEPATCH_KERNEL_NOT_SUPPORTED_UNATTACHED = (
    "Supported livepatch kernels are listed here: {url}".format(
        url=urls.LIVEPATCH_SUPPORTED_KERNELS
    )
)
LIVEPATCH_UNABLE_TO_CONFIGURE = "Unable to configure livepatch: {}"
LIVEPATCH_UNABLE_TO_ENABLE = "Unable to enable Livepatch: "
LIVEPATCH_DISABLE_REATTACH = (
    "Disabling Livepatch prior to re-attach with new token"
)

ERROR_PARSING_VERSION_OS_RELEASE = FormattedNamedMessage(
    "error-parsing-version-os-release",
    """\
Could not parse /etc/os-release VERSION: {orig_ver} (modified to {mod_ver})""",
)

MISSING_SERIES_ON_OS_RELEASE = FormattedNamedMessage(
    "missing-series-on-os-release",
    """\
Could not extract series information from /etc/os-release.
The VERSION filed does not have version information: {version}
and the VERSION_CODENAME information is not present""",
)

INVALID_LOCK_FILE = FormattedNamedMessage(
    "invalid-lock-file",
    """\
There is a corrupted lock file in the system. To continue, please remove it
from the system by running:

$ sudo rm {lock_file_path}""",
)

MISSING_YAML_MODULE = NamedMessage(
    "missing-yaml-module",
    """\
Couldn't import the YAML module.
Make sure the 'python3-yaml' package is installed correctly
and /usr/lib/python3/dist-packages is in yout PYTHONPATH.""",
)

BROKEN_YAML_MODULE = FormattedNamedMessage(
    "broken-yaml-module",
    "Error while trying to parse a yaml file using 'yaml' from {path}",
)

FIX_CANNOT_INSTALL_PACKAGE = FormattedNamedMessage(
    "fix-cannot-install-package",
    "Cannot install package {package} version {version}" "",
)

UNATTENDED_UPGRADES_SYSTEMD_JOB_DISABLED = NamedMessage(
    "unattended-upgrades-systemd-job-disabled",
    "apt-daily.timer jobs are not running",
)

UNATTENDED_UPGRADES_CFG_LIST_VALUE_EMPTY = FormattedNamedMessage(
    "unattended-upgrades-cfg-list-value-empty",
    "{cfg_name} is empty",
)

UNATTENDED_UPGRADES_CFG_VALUE_TURNED_OFF = FormattedNamedMessage(
    "unattended-upgrades-cfg-value-turned-off",
    "{cfg_name} is turned off",
)

USER_CONFIG_MIGRATION_MIGRATING = (
    "Migrating /etc/ubuntu-advantage/uaclient.conf"
)
USER_CONFIG_MIGRATION_WARNING_UACLIENT_CONF_LOAD = """\
Warning: Failed to load /etc/ubuntu-advantage/uaclient.conf.preinst-backup
         No automatic migration will occur.
         You may need to use "pro config set" to re-set your settings."""

USER_CONFIG_MIGRATION_WARNING_NEW_USER_CONFIG_WRITE = """\
Warning: Failed to migrate user_config from /etc/ubuntu-advantage/uaclient.conf
         Please run the following to keep your custom settings:"""

USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE = """\
Warning: Failed to migrate /etc/ubuntu-advantage/uaclient.conf
         Please add following to uaclient.conf to keep your config:"""

LIVEPATCH_APPLICATION_STATUS_CLIENT_FAILURE = NamedMessage(
    "livepatch-client-failure",
    "canonical-livepatch status didn't finish successfully",
)

STATUS_NO_SERVICES_AVAILABLE = (
    """No Ubuntu Pro services are available to this system."""
)

STATUS_ALL_HINT = (
    "For a list of all Ubuntu Pro services, run 'pro status --all'"
)
STATUS_SERVICE_HAS_VARIANTS = " * Service has variants"

STATUS_ALL_HINT_WITH_VARIANTS = """\
For a list of all Ubuntu Pro services and variants, run 'pro status --all'"""

SERVICE_DISABLED_MISSING_PACKAGE = FormattedNamedMessage(
    "service-disabled-missing-package",
    """\
The {service} service is not enabled because the {package} package is
not installed.""",
)

INVALID_OPTION_COMBINATION = FormattedNamedMessage(
    "invalid-option-combination",
    "Error: Cannot use {option1} together with {option2}.",
)

PRO_HELP_SERVICE_INFO = NamedMessage(
    "pro-help-service-info",
    "Use pro help <service> to get more details about each service",
)

WARNING_HUMAN_READABLE_OUTPUT = """\
WARNING: this output is intended to be human readable, and subject to change.
In scripts, prefer using machine readable data from the `pro api` command,
or use `pro {command} --format json`.
"""

CLOUD_METADATA_ERROR = FormattedNamedMessage(
    "cloud-metadata-error",
    "An error occurred while talking the the cloud metadata service: {code} - {body}",  # noqa: E501
)

EXTERNAL_API_ERROR = FormattedNamedMessage(
    "external-api-error", "Error connecting to {url}: {code} {body}"
)

JSON_PARSER_ERROR = FormattedNamedMessage(
    "json-parser-error", "{source} returned invalid json: {out}"
)

SNAP_NOT_INSTALLED_ERROR = FormattedNamedMessage(
    "snap-not-installed-error", "snap {snap} is not installed or doesn't exist"
)

UNEXPECTED_SNAPD_API_ERROR = FormattedNamedMessage(
    "unexpected-snapd-api-error", "Unexpected SNAPD API error\n{error}"
)

SNAPD_CONNECTION_REFUSED = NamedMessage(
    "snapd-connection-refused", "Could not reach the SNAPD API"
)

ANBOX_RUN_INIT_CMD = NamedMessage(
    "anbox-run-init-cmd",
    """\
To finish setting up the Anbox Cloud Appliance, run:

$ sudo anbox-cloud-appliance init

You can accept the default answers if you do not have any specific
configuration changes.
For more information, see {url}
""".format(
        url=urls.ANBOX_DOCS_APPLIANCE_INITIALIZE
    ),
)

INSTALLING_PACKAGES = "Installing {}"
INSTALLING_SERVICE_PACKAGES = "Installing {title} packages"
SKIPPING_INSTALLING_PACKAGES = "Skipping installing packages{}"
UNINSTALLING_PACKAGES = "Uninstalling {}"
UNINSTALLING_PACKAGES_FAILED = "Failure when uninstalling {}"

INSTALLING_REQUIRED_SNAPS = NamedMessage(
    "installing-required-snaps", "Installing required snaps"
)

INSTALLING_REQUIRED_SNAP_PACKAGE = FormattedNamedMessage(
    "installing-required-snap-package", "Installing required snap: {snap}"
)

PYCURL_REQUIRED = NamedMessage(
    "pycurl-required",
    (
        "To use an HTTPS proxy for HTTPS connections, please install "
        "pycurl with `apt install python3-pycurl`"
    ),
)
PYCURL_ERROR = FormattedNamedMessage("pycurl-error", "PycURL Error: {e}")

PROXY_AUTH_FAIL = NamedMessage(
    "proxy-auth-fail", "Proxy authentication failed"
)

EXECUTING_COMMAND = "Executing `{}`"
EXECUTING_COMMAND_FAILED = "Executing `{}` failed."
BACKING_UP_FILE = "Backing up {original} as {backup}"

LANDSCAPE_CLIENT_NOT_INSTALLED = NamedMessage(
    "landscape-client-not-installed", "lanscape-client is not installed"
)
LANDSCAPE_NOT_CONFIGURED = NamedMessage(
    "landscape-not-configured",
    """\
Landscape is installed but not configured.
Run `sudo landscape-config` to set it up, or run `sudo pro disable landscape`\
""",
)
LANDSCAPE_NOT_REGISTERED = NamedMessage(
    "landscape-not-registered",
    """\
Landscape is installed and configured but not registered.
Run `sudo landscape-config` to register, or run `sudo pro disable landscape`\
""",
)
LANDSCAPE_SERVICE_NOT_ACTIVE = NamedMessage(
    "landscape-service-not-active",
    """\
Landscape is installed and configured and registered but not running.
Run `sudo landscape-config` to start it, or run `sudo pro disable landscape`\
""",
)
LANDSCAPE_CONFIG_FAILED = NamedMessage(
    "landscape-config-failed",
    """landscape-config command failed""",
)

API_ERROR_ARGS_AND_DATA_TOGETHER = NamedMessage(
    "api-error-args-and-data-together",
    "Cannot provide both --args and --data at the same time",
)

API_JSON_DATA_FORMAT_ERROR = FormattedNamedMessage(
    "api-json-data-format-error",
    "Error parsing API json data parameter:\n{data}",
)

INVALID_SECURITY_ISSUE = FormattedNamedMessage(
    "invalid-security-issue",
    """\
Error: issue "{issue_id}" is not recognized.\n
CVEs should follow the pattern CVE-yyyy-nnn.\n
USNs should follow the pattern USN-nnnn.""",
)

SECURITY_FIX_NOT_FOUND_ISSUE = FormattedNamedMessage(
    "security-fix-not-found-issue",
    "Error: {issue_id} not found.",
)

DISABLE_DURING_CONTRACT_REFRESH = (
    "Due to contract refresh, " "'{}' is now disabled."
)
UNABLE_TO_DISABLE_DURING_CONTRACT_REFRESH = (
    "Unable to disable '{}' as recommended during contract"
    " refresh. Service is still active. See"
    " `pro status`"
)

FIPS_COULD_NOT_DETERMINE_CLOUD_DEFAULT_PACKAGE = (
    "Could not determine cloud, defaulting to generic FIPS package."
)


SERVICE_UPDATING_CHANGED_DIRECTIVES = "Updating '{}' on changed directives."
REPO_UPDATING_APT_SOURCES = (
    "Updating '{}' apt sources list on changed directives."
)
REPO_REFRESH_INSTALLING_PACKAGES = (
    "Installing packages on changed directives: {}"
)
REPO_NO_APT_KEY = "Ubuntu Pro server provided no aptKey directive for {}"
REPO_NO_SUITES = "Ubuntu Pro server provided no suites directive for {}"
REPO_PIN_FAIL_NO_ORIGIN = (
    "Cannot setup apt pin. Empty apt repo origin value '{}'."
)

RELEASE_UPGRADE_APT_LOCK_HELD_WILL_WAIT = (
    "APT lock is held. Ubuntu Pro configuration will wait until it is released"
)
RELEASE_UPGRADE_NO_PAST_RELEASE = "Could not find past release for {}"
RELEASE_UPGRADE_STARTING = (
    "Starting upgrade of Ubuntu Pro service configuration"
)
RELEASE_UPGRADE_SUCCESS = (
    "Finished upgrade of Ubuntu Pro service configuration"
)

CLI_CONFIG_GLOBAL_XOR_UA_PROXY = (
    "\nError: Setting global apt proxy and pro scoped apt proxy at the"
    " same time is unsupported. No apt proxy is set."
)
CLI_INTERRUPT_RECEIVED = "Interrupt received; exiting."
CLI_TRY_HELP = "Try 'pro --help' for more information."
CLI_VALID_CHOICES = "\n{} must be one of: {}"
CLI_EXPECTED_FORMAT = "\nExpected {expected} but found: {actual}"
CLI_CONFIG_VALUE_MUST_BE_POS_INT = (
    "Cannot set {} to {}: " "<value> for interval must be a positive integer."
)
CLI_NO_HELP = "No help available for '{}'"
CONFIG_POS_INT_FAIL_DEFAULT_FALLBACK = (
    "Value for the {} interval must be a positive integer. "
    "Default value will be used."
)
CONFIG_NO_YAML_FILE = "Could not find yaml file: {}"
CONFIG_INVALID_URL = "Invalid url in config. {}: {}"

APT_REMOVING_SOURCE_FILE = "Removing apt source file: {}"
APT_REMOVING_PREFERENCES_FILE = "Removing apt preferences file: {}"
APT_INVALID_CREDENTIALS = "Invalid APT credentials provided for {}"
APT_TIMEOUT = "Timeout trying to access APT repository at {}"
APT_UNEXPECTED_ERROR = (
    "Unexpected APT error. See /var/log/ubuntu-advantage.log"
)
APT_COMMAND_TIMEOUT = (
    "Cannot validate credentials for APT repo."
    " Timeout after {} seconds trying to reach {}."
)


DETACH_WILL_DISABLE = "Detach will disable the following service{}:"

STATUS_TOKEN_NOT_VALID = "This token is not valid."

AWS_NO_VALID_IMDS = "No valid AWS IMDS endpoint discovered at addresses: {}"

GPG_KEY_NOT_FOUND = "GPG key '{}' not found."

SUBP_INVALID_COMMAND = "Invalid command specified '{cmd}'."
SUBP_COMMAND_FAILED = (
    "Failed running command '{cmd}' [exit({exit_code})]." " Message: {stderr}"
)

STATUS_SERVICE = "SERVICE"
STATUS_AVAILABLE = "AVAILABLE"
STATUS_ENTITLED = "ENTITLED"
STATUS_AUTO_ENABLED = "AUTO_ENABLED"
STATUS_STATUS = "STATUS"
STATUS_DESCRIPTION = "DESCRIPTION"
STATUS_NOTICES = "NOTICES"
STATUS_FEATURES = "FEATURES"

STATUS_ENTITLED_ENTITLED = "yes"
STATUS_ENTITLED_UNENTITLED = "no"
STATUS_STATUS_ENABLED = "enabled"
STATUS_STATUS_DISABLED = "disabled"
STATUS_STATUS_INAPPLICABLE = "n/a"
STATUS_STATUS_UNAVAILABLE = "—"
STATUS_STATUS_WARNING = "warning"
STATUS_SUPPORT_ESSENTIAL = "essential"
STATUS_SUPPORT_STANDARD = "standard"
STATUS_SUPPORT_ADVANCED = "advanced"

STATUS_CONTRACT_EXPIRES_UNKNOWN = "Unknown/Expired"

STATUS_FOOTER_ENABLE_SERVICES_WITH = "Enable services with: {}"
STATUS_FOOTER_ACCOUNT = "Account"
STATUS_FOOTER_SUBSCRIPTION = "Subscription"
STATUS_FOOTER_VALID_UNTIL = "Valid until"
STATUS_FOOTER_SUPPORT_LEVEL = "Technical support level"

ANBOX_TITLE = "Anbox Cloud"
ANBOX_DESCRIPTION = "Scalable Android in the cloud"
ANBOX_HELP_TEXT = """\
Anbox Cloud lets you stream mobile apps securely, at any scale, to any device,
letting you focus on your apps. Run Android in system containers on public or
private clouds with ultra low streaming latency. When the anbox-cloud service
is enabled, by default, the Appliance variant is enabled. Enabling this service
allows orchestration to provision a PPA with the Anbox Cloud resources. This
step also configures the Anbox Management Service (AMS) with the necessary
image server credentials. To learn more about Anbox Cloud, see
{url}""".format(
    url=urls.ANBOX_HOME_PAGE
)

CC_TITLE = "CC EAL2"
CC_DESCRIPTION = "Common Criteria EAL2 Provisioning Packages"
CC_HELP_TEXT = """\
Common Criteria is an Information Technology Security Evaluation standard
(ISO/IEC IS 15408) for computer security certification. Ubuntu 16.04 has been
evaluated to assurance level EAL2 through CSEC. The evaluation was performed
on Intel x86_64, IBM Power8 and IBM Z hardware platforms."""
CC_PRE_INSTALL = (
    "(This will download more than 500MB of packages, so may take"
    " some time.)"
)
CC_POST_ENABLE = "Please follow instructions in {} to configure EAL2"

CIS_TITLE = "CIS Audit"
CIS_USG_TITLE = "Ubuntu Security Guide"
CIS_DESCRIPTION = "Security compliance and audit tools"
CIS_HELP_TEXT = """\
Ubuntu Security Guide is a tool for hardening and auditing and allows for
environment-specific customizations. It enables compliance with profiles such
as DISA-STIG and the CIS benchmarks. Find out more at
{url}""".format(
    url=urls.USG_DOCS
)
CIS_POST_ENABLE = "Visit {url} to learn how to use CIS".format(
    url=urls.CIS_HOME_PAGE
)
CIS_USG_POST_ENABLE = "Visit {url} for the next steps".format(
    url=urls.USG_DOCS
)
CIS_IS_NOW_USG = """\
From Ubuntu 20.04 and onwards 'pro enable cis' has been
replaced by 'pro enable usg'. See more information at:
{url}""".format(
    url=urls.USG_DOCS
)

ESM_APPS_TITLE = "Ubuntu Pro: ESM Apps"
ESM_APPS_DESCRIPTION = "Expanded Security Maintenance for Applications"
ESM_APPS_HELP_TEXT = """\
Expanded Security Maintenance for Applications is enabled by default on
entitled workloads. It provides access to a private PPA which includes
available high and critical CVE fixes for Ubuntu LTS packages in the Ubuntu
Main and Ubuntu Universe repositories from the Ubuntu LTS release date until
its end of life. You can find out more about the esm service at
{url}""".format(
    url=urls.ESM_HOME_PAGE
)

ESM_INFRA_TITLE = "Ubuntu Pro: ESM Infra"
ESM_INFRA_DESCRIPTION = "Expanded Security Maintenance for Infrastructure"
ESM_INFRA_HELP_TEXT = """\
Expanded Security Maintenance for Infrastructure provides access to a private
PPA which includes available high and critical CVE fixes for Ubuntu LTS
packages in the Ubuntu Main repository between the end of the standard Ubuntu
LTS security maintenance and its end of life. It is enabled by default with
Ubuntu Pro. You can find out more about the service at
{url}""".format(
    url=urls.ESM_HOME_PAGE
)

FIPS_TITLE = "FIPS"
FIPS_DESCRIPTION = "NIST-certified core packages"
FIPS_HELP_TEXT = """\
FIPS 140-2 is a set of publicly announced cryptographic standards developed by
the National Institute of Standards and Technology applicable for FedRAMP,
HIPAA, PCI and ISO compliance use cases. Note that "fips" does not provide
security patching. For FIPS certified modules with security patches please
see "fips-updates". You can find out more at {url}""".format(
    url=urls.FIPS_HOME_PAGE
)

FIPS_UPDATES_TITLE = "FIPS Updates"
FIPS_UPDATES_DESCRIPTION = (
    "NIST-certified core packages with priority security updates"
)
FIPS_UPDATES_HELP_TEXT = """\
fips-updates installs fips modules including all security patches for those
modules that have been provided since their certification date. You can find
out more at {url}""".format(
    url=urls.FIPS_HOME_PAGE
)

LANDSCAPE_TITLE = "Landscape"
LANDSCAPE_DESCRIPTION = "Management and administration tool for Ubuntu"
LANDSCAPE_HELP_TEXT = """\
Landscape Client can be installed on this machine and enrolled in Canonical's
Landscape SaaS: {saas_url} or a self-hosted Landscape:
{install_url}
Landscape allows you to manage many machines as easily as one, with an
intuitive dashboard and API interface for automation, hardening, auditing, and
more. Find out more about Landscape at {home_url}""".format(
    saas_url=urls.LANDSCAPE_SAAS,
    install_url=urls.LANDSCAPE_DOCS_INSTALL,
    home_url=urls.LANDSCAPE_HOME_PAGE,
)

LIVEPATCH_TITLE = "Livepatch"
LIVEPATCH_DESCRIPTION = "Canonical Livepatch service"
LIVEPATCH_HELP_TEXT = """\
Livepatch provides selected high and critical kernel CVE fixes and other
non-security bug fixes as kernel livepatches. Livepatches are applied without
rebooting a machine which drastically limits the need for unscheduled system
reboots. Due to the nature of fips compliance, livepatches cannot be enabled
on fips-enabled systems. You can find out more about Ubuntu Kernel Livepatch
service at {url}""".format(
    url=urls.LIVEPATCH_HOME_PAGE
)

REALTIME_TITLE = "Real-time kernel"
REALTIME_DESCRIPTION = "Ubuntu kernel with PREEMPT_RT patches integrated"
REALTIME_HELP_TEXT = """\
The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated. It
services latency-dependent use cases by providing deterministic response times.
The Real-time kernel meets stringent preemption specifications and is suitable
for telco applications and dedicated devices in industrial automation and
robotics. The Real-time kernel is currently incompatible with FIPS and
Livepatch."""
REALTIME_GENERIC_TITLE = "Real-time kernel"
REALTIME_GENERIC_DESCRIPTION = "Generic version of the RT kernel (default)"
REALTIME_NVIDIA_TITLE = "Real-time NVIDIA Tegra Kernel"
REALTIME_NVIDIA_DESCRIPTION = "RT kernel optimized for NVIDIA Tegra platform"
REALTIME_INTEL_TITLE = "Real-time Intel IOTG Kernel"
REALTIME_INTEL_DESCRIPTION = "RT kernel optimized for Intel IOTG platform"

ROS_TITLE = "ROS ESM Security Updates"
ROS_DESCRIPTION = "Security Updates for the Robot Operating System"
ROS_HELP_TEXT = """\
ros provides access to a private PPA which includes security-related updates
for available high and critical CVE fixes for Robot Operating System (ROS)
packages. For access to ROS ESM and security updates, both esm-infra and
esm-apps services will also be enabled. To get additional non-security updates,
enable ros-updates. You can find out more about the ROS ESM service at
{url}""".format(
    url=urls.ROS_HOME_PAGE
)

ROS_UPDATES_TITLE = "ROS ESM All Updates"
ROS_UPDATES_DESCRIPTION = "All Updates for the Robot Operating System"
ROS_UPDATES_HELP_TEXT = """\
ros-updates provides access to a private PPA that includes non-security-related
updates for Robot Operating System (ROS) packages. For full access to ROS ESM,
security and non-security updates, the esm-infra, esm-apps, and ros services
will also be enabled. You can find out more about the ROS ESM service at
{url}""".format(
    url=urls.ROS_HOME_PAGE
)

CLI_HELP_EPILOG = (
    "Use {name} {command} --help for more information about a command."
)

CLI_ARGS = "Arguments"
CLI_FLAGS = "Flags"
CLI_AVAILABLE_COMMANDS = "Available Commands"
CLI_FORMAT_DESC = "output in the specified format (default: {})"
CLI_ASSUME_YES = (
    "do not prompt for confirmation before performing the {command}"
)

CLI_API_DESC = "Calls the Client API endpoints."
CLI_API_ENDPOINT = "API endpoint to call"
CLI_API_ARGS = "Options to pass to the API endpoint, formatted as key=value"
CLI_API_DATA = "arguments in JSON format to the API endpoint"

CLI_AUTO_ATTACH_DESC = "Automatically attach on an Ubuntu Pro cloud instance."

CLI_COLLECT_LOGS_DESC = (
    "Collect logs and relevant system information into a tarball."
)
CLI_COLLECT_LOGS_OUTPUT = (
    "tarball where the logs will be stored. (Defaults to " "./ua_logs.tar.gz)"
)

CLI_CONFIG_SHOW_DESC = "Show customisable configuration settings"
CLI_CONFIG_SHOW_KEY = "Optional key or key(s) to show configuration settings."
CLI_CONFIG_SET_DESC = "Set and apply Ubuntu Pro configuration settings"
CLI_CONFIG_SET_KEY_VALUE = (
    "key=value pair to configure for Ubuntu Pro services."
    " Key must be one of: {}"
)
CLI_CONFIG_UNSET_DESC = "Unset Ubuntu Pro configuration setting"
CLI_CONFIG_UNSET_KEY = (
    "configuration key to unset from Ubuntu Pro services. One of: {}"
)
CLI_CONFIG_DESC = "Manage Ubuntu Pro configuration"

CLI_ATTACH_DESC = """\
Attach this machine to Ubuntu Pro with a token obtained from:
{url}

When running this command without a token, it will generate a short code
and prompt you to attach the machine to your Ubuntu Pro account using
a web browser.""".format(
    url=urls.PRO_DASHBOARD
)
CLI_ATTACH_TOKEN = "token obtained for Ubuntu Pro authentication"
CLI_ATTACH_NO_AUTO_ENABLE = (
    "do not enable any recommended services automatically"
)
CLI_ATTACH_ATTACH_CONFIG = (
    "use the provided attach config file instead of passing the token on the "
    "cli"
)
CLI_ATTACH_ATTACH_CONFIG

CLI_FIX_DESC = (
    "Inspect and resolve CVEs and USNs (Ubuntu Security Notices) on this"
    " machine."
)
CLI_FIX_ISSUE = (
    "Security vulnerability ID to inspect and resolve on this system."
    " Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-dd"
)
CLI_FIX_DRY_RUN = (
    "If used, fix will not actually run but will display"
    " everything that will happen on the machine during the"
    " command."
)
CLI_FIX_NO_RELATED = (
    "If used, when fixing a USN, the command will not try to"
    " also fix related USNs to the target USN."
)

CLI_SS_DESC = """\
Show security updates for packages in the system, including all
available Expanded Security Maintenance (ESM) related content.

Shows counts of how many packages are supported for security updates
in the system.

If called with --format json|yaml it shows a summary of the
installed packages based on the origin:
- main/restricted/universe/multiverse: packages from the Ubuntu archive
- esm-infra/esm-apps: packages from the ESM archive
- third-party: packages installed from non-Ubuntu sources
- unknown: packages which don't have an installation source (like local
  deb packages or packages for which the source was removed)

The output contains basic information about Ubuntu Pro. For a
complete status on Ubuntu Pro services, run 'pro status'.
"""
CLI_SS_THIRDPARTY = "List and present information about third-party packages"
CLI_SS_UNAVAILABLE = "List and present information about unavailable packages"
CLI_SS_ESM_INFRA = "List and present information about esm-infra packages"
CLI_SS_ESM_APPS = "List and present information about esm-apps packages"

CLI_REFRESH_DESC = """\
Refresh three distinct Ubuntu Pro related artifacts in the system:

* contract: Update contract details from the server.
* config:   Reload the config file.
* messages: Update APT and MOTD messages related to UA.

You can individually target any of the three specific actions,
by passing it's target to nome to the command.  If no `target`
is specified, all targets are refreshed.
"""
CLI_REFRESH_TARGET = "Target to refresh."

CLI_DETACH_DESC = "Detach this machine from Ubuntu Pro services."

CLI_HELP_DESC = "Provide detailed information about Ubuntu Pro services."
CLI_HELP_SERVICE = "a service to view help output for. One of: {options}"
CLI_HELP_ALL = "Include beta services"

CLI_ENABLE_DESC = "Enable an Ubuntu Pro service."
CLI_ENABLE_SERVICE = (
    "the name(s) of the Ubuntu Pro services to enable." " One of: {options}"
)
CLI_ENABLE_ACCESS_ONLY = (
    "do not auto-install packages. Valid for cc-eal, cis and "
    "realtime-kernel."
)
CLI_ENABLE_BETA = "allow beta service to be enabled"
CLI_ENABLE_VARIANT = "The name of the variant to use when enabling the service"

CLI_DISABLE_DESC = "Disable an Ubuntu Pro service."
CLI_DISABLE_SERVICE = (
    "the name(s) of the Ubuntu Pro services to disable." " One of: {options}"
)

CLI_SYSTEM_DESC = "Output system related information related to Pro services"
CLI_SYSTEM_REBOOT_REQUIRED = "does the system need to be rebooted"
CLI_SYSTEM_REBOOT_REQUIRED_DESC = """\
Report the current reboot-required status for the machine.

This command will output one of the three following states
for the machine regarding reboot:

* no: The machine doesn't require a reboot
* yes: The machine requires a reboot
* yes-kernel-livepatches-applied: There are only kernel related
  packages that require a reboot, but Livepatch has already provided
  patches for the current running kernel. The machine still needs a
  reboot, but you can assess if the reboot can be performed in the
  nearest maintenance window.
"""

CLI_STATUS_DESC = """\
Report current status of Ubuntu Pro services on system.

This shows whether this machine is attached to an Ubuntu Advantage
support contract. When attached, the report includes the specific
support contract details including contract name, expiry dates, and the
status of each service on this system.

The attached status output has four columns:

* SERVICE: name of the service
* ENTITLED: whether the contract to which this machine is attached
  entitles use of this service. Possible values are: yes or no
* STATUS: whether the service is enabled on this machine. Possible
  values are: enabled, disabled, n/a (if your contract entitles
  you to the service, but it isn't available for this machine) or — (if
  you aren't entitled to this service)
* DESCRIPTION: a brief description of the service

The unattached status output instead has three columns. SERVICE
and DESCRIPTION are the same as above, and there is the addition
of:

* AVAILABLE: whether this service would be available if this machine
  were attached. The possible values are yes or no.

If --simulate-with-token is used, then the output has five
columns. SERVICE, AVAILABLE, ENTITLED and DESCRIPTION are the same
as mentioned above, and AUTO_ENABLED shows whether the service is set
to be enabled when that token is attached.

If the --all flag is set, beta and unavailable services are also
listed in the output.
"""
CLI_STATUS_WAIT = "Block waiting on pro to complete"
CLI_STATUS_SIMULATE_WITH_TOKEN = (
    "simulate the output status using a provided token"
)
CLI_STATUS_ALL = "Include unavailable and beta services"

CLI_ROOT_DEBUG = "show all debug log messages to console"
CLI_ROOT_VERSION = "show version of {name}"
CLI_ROOT_ATTACH = "attach this machine to an Ubuntu Pro subscription"
CLI_ROOT_API = "Calls the Client API endpoints."
CLI_ROOT_AUTO_ATTACH = "automatically attach on supported platforms"
CLI_ROOT_COLLECT_LOGS = "collect Pro logs and debug information"
CLI_ROOT_CONFIG = "manage Ubuntu Pro configuration on this machine"
CLI_ROOT_DETACH = "remove this machine from an Ubuntu Pro subscription"
CLI_ROOT_DISABLE = "disable a specific Ubuntu Pro service on this machine"
CLI_ROOT_ENABLE = "enable a specific Ubuntu Pro service on this machine"
CLI_ROOT_FIX = "check for and mitigate the impact of a CVE/USN on this system"
CLI_ROOT_SECURITY_STATUS = "list available security updates for the system"
CLI_ROOT_HELP = "show detailed information about Ubuntu Pro services"
CLI_ROOT_REFRESH = "refresh Ubuntu Pro services"
CLI_ROOT_STATUS = "current status of all Ubuntu Pro services"
CLI_ROOT_SYSTEM = "show system information related to Pro services"
