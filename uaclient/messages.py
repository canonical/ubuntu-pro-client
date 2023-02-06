from typing import Dict, Optional  # noqa: F401

from uaclient.defaults import BASE_UA_URL, DOCUMENTATION_URL


class NamedMessage:
    def __init__(self, name: str, msg: str):
        self.name = name
        self.msg = msg
        # we should use this field whenever we want to provide
        # extra information to the message. This is specially
        # useful if the message represents an error.
        self.additional_info = None  # type: Optional[Dict[str, str]]

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


class TxtColor:
    OKGREEN = "\033[92m"
    DISABLEGREY = "\033[37m"
    INFOBLUE = "\033[94m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


OKGREEN_CHECK = TxtColor.OKGREEN + "✔" + TxtColor.ENDC
FAIL_X = TxtColor.FAIL + "✘" + TxtColor.ENDC
BLUE_INFO = TxtColor.INFOBLUE + "[info]" + TxtColor.ENDC

ERROR_INVALID_CONFIG_VALUE = """\
Invalid value for {path_to_value} in /etc/ubuntu-advantage/uaclient.conf. \
Expected {expected_value}, found {value}."""
INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY = """\
Failed to find the machine token overlay file: {file_path}"""
ERROR_JSON_DECODING_IN_FILE = """\
Found error: {error} when reading json file: {file_path}"""

SECURITY_FIX_NOT_FOUND_ISSUE = "Error: {issue_id} not found."
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
SECURITY_USE_PRO_TMPL = (
    "For easiest security on {title}, use Ubuntu Pro."
    " https://ubuntu.com/{cloud}/pro."
)
SECURITY_ISSUE_RESOLVED = OKGREEN_CHECK + " {issue} is resolved."
SECURITY_ISSUE_NOT_RESOLVED = FAIL_X + " {issue} is not resolved."
SECURITY_ISSUE_UNAFFECTED = (
    OKGREEN_CHECK + " {issue} does not affect your system."
)
SECURITY_AFFECTED_PKGS = (
    "{count} affected source package{plural_str} installed"
)
USN_FIXED = "{issue} is addressed."
CVE_FIXED = "{issue} is resolved."
CVE_FIXED_BY_LIVEPATCH = (
    OKGREEN_CHECK
    + " {issue} is resolved by livepatch patch version: {version}."
)
SECURITY_URL = "{issue}: {title}\nhttps://ubuntu.com/security/{url_path}"
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
APT_UPDATING_LISTS = "Updating package lists"
DISABLE_FAILED_TMPL = "Could not disable {title}."
ACCESS_ENABLED_TMPL = "{title} access enabled"
ENABLED_TMPL = "{title} enabled"
UNABLE_TO_DETERMINE_CLOUD_TYPE = (
    """\
Unable to determine auto-attach platform support
For more information see: """
    + BASE_UA_URL
    + "."
)
UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE = (
    """\
Auto-attach image support is not available on {cloud_type}
See: """
    + BASE_UA_URL
)
UNSUPPORTED_AUTO_ATTACH = (
    """\
Auto-attach image support is not available on this image
See: """
    + BASE_UA_URL
)
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
DETACH_AUTOMATION_FAILURE = "Unable to automatically detach machine"

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

UPDATE_CHECK_CONTRACT_FAILURE = (
    """Failed to check for change in machine contract. Reason: {reason}"""
)
UPDATE_MOTD_NO_REQUIRED_CMD = (
    "Required command to update MOTD messages not found: {cmd}."
)

INCOMPATIBLE_SERVICE = """\
{service_being_enabled} cannot be enabled with {incompatible_service}.
Disable {incompatible_service} and proceed to enable {service_being_enabled}? \
(y/N) """

REQUIRED_SERVICE = """\
{service_being_enabled} cannot be enabled with {required_service} disabled.
Enable {required_service} and proceed to enable {service_being_enabled}? \
(y/N) """

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

ANNOUNCE_ESM_APPS_TMPL = """\
 * Introducing Expanded Security Maintenance for Applications.
   Receive updates to over 25,000 software packages with your
   Ubuntu Pro subscription. Free for personal use.

     {url}
"""

CONTRACT_EXPIRED_MOTD_SOON_TMPL = """\
CAUTION: Your Ubuntu Pro subscription will expire in {remaining_days} days.
Renew your subscription at https://ubuntu.com/pro to ensure continued security
coverage for your applications.
"""

CONTRACT_EXPIRED_MOTD_GRACE_PERIOD_TMPL = """\
CAUTION: Your Ubuntu Pro subscription expired on {expired_date}.
Renew your subscription at https://ubuntu.com/pro to ensure continued security
coverage for your applications.
Your grace period will expire in {remaining_days} days.
"""

CONTRACT_EXPIRED_MOTD_PKGS_TMPL = """\
*Your Ubuntu Pro subscription has EXPIRED*
{pkg_num} additional security update(s) require Ubuntu Pro with '{service}' enabled.
Renew your service at https://ubuntu.com/pro
"""  # noqa: E501

CONTRACT_EXPIRED_MOTD_NO_PKGS_TMPL = """\
*Your Ubuntu Pro subscription has EXPIRED*
Renew your service at https://ubuntu.com/pro
"""

CONTRACT_EXPIRES_SOON_APT_NEWS = """\
#
# CAUTION: Your Ubuntu Pro subscription will expire in {remaining_days} days.
# Renew your subscription at https://ubuntu.com/pro to ensure continued
# security coverage for your applications.
#
"""
CONTRACT_EXPIRED_GRACE_PERIOD_APT_NEWS = """\
#
# CAUTION: Your Ubuntu Pro subscription expired on {expired_date}.
# Renew your subscription at https://ubuntu.com/pro to ensure continued
# security coverage for your applications.
# Your grace period will expire in {remaining_days} days.
#
"""
CONTRACT_EXPIRED_APT_NEWS = """\
#
# *Your Ubuntu Pro subscription has EXPIRED*
# Renew your service at https://ubuntu.com/pro
#
"""

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

UACLIENT_CONF_HEADER = """\
# Ubuntu Pro client config file.
# If you modify this file, run "pro refresh config" to ensure changes are
# picked up by Ubuntu Pro client.

"""

SETTING_SERVICE_PROXY = "Setting {service} proxy"
ERROR_USING_PROXY = (
    'Error trying to use "{proxy}" as proxy to reach "{test_url}": {error}'
)

PROXY_DETECTED_BUT_NOT_CONFIGURED = """\
No proxy set in config; however, proxy is configured for: {{services}}.
See {docs_url} for more information on pro proxy configuration.
""".format(
    docs_url=DOCUMENTATION_URL
)

FIPS_BLOCK_ON_CLOUD = FormattedNamedMessage(
    "cloud-non-optimized-fips-kernel",
    """\
Ubuntu {series} does not provide {cloud} optimized FIPS kernel
For help see: """
    + BASE_UA_URL
    + ".",
)

UNATTACHED = NamedMessage(
    "unattached",
    """\
This machine is not attached to an Ubuntu Pro subscription.
See """
    + BASE_UA_URL,
)

VALID_SERVICE_FAILURE_UNATTACHED = FormattedNamedMessage(
    "valid-service-failure-unattached",
    """\
To use '{valid_service}' you need an Ubuntu Pro subscription
Personal and community subscriptions are available at no charge
See """
    + BASE_UA_URL,
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

DEPENDENT_SERVICE_NOT_FOUND = FormattedNamedMessage(
    "dependent-service-not-found", "Dependent service {service} not found."
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
    "enable-failes", "Could not enable {title}."
)

UNENTITLED = FormattedNamedMessage(
    "subscription-not-entitled-to-service",
    """\
This subscription is not entitled to {title}
For more information see: """
    + BASE_UA_URL
    + ".",
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
    """\
Invalid token. See """
    + BASE_UA_URL,
)

MAGIC_ATTACH_TOKEN_ALREADY_ACTIVATED = NamedMessage(
    "magic-attach-token-already-activated",
    "The magic attach token is already activated.",
)

MAGIC_ATTACH_EXPIRED_TOKEN = NamedMessage(
    "magic-attach-token-expired",
    "The magic attach token has expired or never existed.",
)

MAGIC_ATTACH_TOKEN_ERROR = NamedMessage(
    "magic-attach-token-error",
    "The magic attach token is invalid, has expired or never existed",
)

MAGIC_ATTACH_INVALID_EMAIL = FormattedNamedMessage(
    "magic-attach-invalid-email",
    "{email} is not a valid email.",
)

MAGIC_ATTACH_UNAVAILABLE = NamedMessage(
    "magic-attach-service-unavailable",
    "Service unavailable, please try again later.",
)

MAGIC_ATTACH_INVALID_PARAM = FormattedNamedMessage(
    "magic-attach-invalid-param",
    "This attach flow does not support {param} with value: {value}",
)

REQUIRED_SERVICE_NOT_FOUND = FormattedNamedMessage(
    "required-service-not-found", "Required service {service} not found."
)

UNEXPECTED_CONTRACT_TOKEN_ON_ATTACHED_MACHINE = NamedMessage(
    "unexpeced-contract-token-on-attached-machine",
    "Got unexpected contract_token on an already attached machine",
)

APT_UPDATE_INVALID_REPO = FormattedNamedMessage(
    "apt-update-invalid-repo", "APT update failed.\n{repo_msg}"
)

APT_INSTALL_FAILED = NamedMessage("apt-install-failed", "APT install failed.")

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

SNAPD_NOT_PROPERLY_INSTALLED = FormattedNamedMessage(
    "snapd-not-properly-installed-for-livepatch",
    (
        "{snap_cmd} is present but snapd is not installed;"
        " cannot enable {service}"
    ),
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
        url=BASE_UA_URL
    ),
)

ATTACH_EXPIRED_TOKEN = NamedMessage(
    "attach-experied-token",
    """\
Expired token or contract. To obtain a new token visit: """
    + BASE_UA_URL,
)

ATTACH_TOKEN_ARG_XOR_CONFIG = NamedMessage(
    "attach-token-xor-config",
    """\
Do not pass the TOKEN arg if you are using --attach-config.
Include the token in the attach-config file instead.
    """,
)

ATTACH_REQUIRES_TOKEN = NamedMessage(
    "attach-requires-token",
    """\
Attach requires a token: sudo pro attach <TOKEN>
To obtain a token please visit: """
    + BASE_UA_URL
    + ".",
)

ATTACH_FAILURE = NamedMessage(
    "attach-failure",
    """\
Failed to attach machine. See """
    + BASE_UA_URL,
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

LIVEPATCH_ERROR_INSTALL_ON_CONTAINER = NamedMessage(
    "livepatch-error-install-on-container",
    "Cannot install Livepatch on a container.",
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
REALTIME_BETA_FLAG_REQUIRED = NamedMessage(
    "beta-flag-required",
    "Use `pro enable realtime-kernel --beta` to acknowledge the real-time"
    " kernel is currently in beta and comes with no support.",
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
This will disable Ubuntu Pro updates to the Real-time kernel on this machine.
The Real-time kernel will remain installed.\
Are you sure? (y/N) """

REALTIME_ERROR_INSTALL_ON_CONTAINER = NamedMessage(
    "realtime-error-install-on-container",
    "Cannot install Real-time kernel on a container.",
)

GCP_SERVICE_ACCT_NOT_ENABLED_ERROR = NamedMessage(
    "gcp-pro-service-account-not-enabled",
    "Failed to attach machine\n"
    "{error_msg}\n"
    "For more information, "
    "see https://cloud.google.com/iam/docs/service-accounts",
)

LOG_CONNECTIVITY_ERROR_TMPL = CONNECTIVITY_ERROR.msg + " {error}"
LOG_CONNECTIVITY_ERROR_WITH_URL_TMPL = (
    CONNECTIVITY_ERROR.msg + " Failed to access URL: {url}. {error}"
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

AVAILABILITY_FROM_UNKNOWN_SERVICE = """\
Ignoring availability of unknown service {service} from contract server
"""

NOTICE_FIPS_MANUAL_DISABLE_URL = """\
FIPS kernel is running in a disabled state.
  To manually remove fips kernel: https://discourse.ubuntu.com/t/20738
"""
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
Enter your token (from {}) to attach this system:""".format(
    BASE_UA_URL
)
PROMPT_EXPIRED_ENTER_TOKEN = """\
Enter your new token to renew Ubuntu Pro subscription on this system:"""
PROMPT_UA_SUBSCRIPTION_URL = """\
Open a browser to: {}""".format(
    BASE_UA_URL
)

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

KERNEL_PARSE_ERROR = "Failed to parse kernel: {kernel}"

LSCPU_ARCH_PARSE_ERROR = NamedMessage(
    name="lscpu-arch-parse-error",
    msg="Failed to parse architecture from output of lscpu",
)

WARN_NEW_VERSION_AVAILABLE = FormattedNamedMessage(
    name="new-version-available",
    msg="A new version of the client is available: {version}. \
Please upgrade to the latest version to get the new features \
and bug fixes.",
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
NO_EOL_DATA_FOR_SERIES = "Unable to get {} dates for series {}"

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
{repository} packages until {year}"""
SS_SERVICE_ADVERTISE_COUNTS = (
    " and has {updates} pending security update{plural}."
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
    url=BASE_UA_URL
)

SS_POLICY_HINT = """\
For example, run:
    apt-cache policy {package}
to learn more about that package."""

SS_NO_THIRD_PARTY = "You have no packages installed from a third party."
SS_NO_UNAVAILABLE = (
    "You have no packages installed that are no longer available."
)
SS_NO_INTERIM_PRO_SUPPORT = "Ubuntu Pro is not available for non-LTS releases."

SS_SERVICE_HELP = "Run 'pro help {service}' to learn more"
SS_BOLD_PACKAGES = """\
Package names in {bold}bold{end_bold} currently have an available update
with '{{service}}' enabled""".format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)

ENTITLEMENT_NOT_FOUND = FormattedNamedMessage(
    "entitlement-not-found",
    'could not find entitlement named "{name}"',
)

TRY_UBUNTU_PRO_BETA = """\
Try Ubuntu Pro beta with a free personal subscription on up to 5 machines.
Learn more at https://ubuntu.com/pro"""

INVALID_STATE_FILE = "Invalid state file: {}"

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
RETRY_ERROR_DETAIL_URL_ERROR_CODE = "a {code} while reaching {url}"
RETRY_ERROR_DETAIL_URL_ERROR_URL = "an error while reaching {url}"
RETRY_ERROR_DETAIL_URL_ERROR_GENERIC = "a network error"
RETRY_ERROR_DETAIL_UNKNOWN = "an unknown error"

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
