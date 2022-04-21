from uaclient.defaults import BASE_UA_URL, DOCUMENTATION_URL


class NamedMessage:
    def __init__(self, name: str, msg: str):
        self.name = name
        self.msg = msg


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
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


OKGREEN_CHECK = TxtColor.OKGREEN + "✔" + TxtColor.ENDC
FAIL_X = TxtColor.FAIL + "✘" + TxtColor.ENDC

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
SECURITY_URL = "{issue}: {title}\nhttps://ubuntu.com/security/{url_path}"
SECURITY_UA_SERVICE_NOT_ENABLED = """\
Error: UA service: {service} is not enabled.
Without it, we cannot fix the system."""
SECURITY_UA_SERVICE_NOT_ENTITLED = """\
Error: The current UA subscription is not entitled to: {service}.
Without it, we cannot fix the system."""
APT_UPDATING_LISTS = "Updating package lists"
DISABLE_FAILED_TMPL = "Could not disable {title}."
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
NO_ACTIVE_OPERATIONS = """No Ubuntu Advantage operations are running"""
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
    "This FIPS install is out of date, run: sudo ua enable fips"
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
Service {name} is recommended by default. Run: sudo ua enable {name}"""
DETACH_SUCCESS = "This machine is now detached."
DETACH_AUTOMATION_FAILURE = "Unable to automatically detach machine"

REFRESH_CONTRACT_ENABLE = "One moment, checking your subscription first"
REFRESH_CONTRACT_SUCCESS = "Successfully refreshed your subscription."
REFRESH_CONTRACT_FAILURE = "Unable to refresh your subscription"
REFRESH_CONFIG_SUCCESS = "Successfully processed your ua configuration."
REFRESH_CONFIG_FAILURE = "Unable to process uaclient.conf"

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

# MOTD and APT command messaging
ANNOUNCE_ESM_TMPL = """\
 * Introducing Extended Security Maintenance for Applications.
   Receive updates to over 30,000 software packages with your
   Ubuntu Advantage subscription. Free for personal use.

     {url}
"""

CONTRACT_EXPIRED_SOON_TMPL = """\
CAUTION: Your {title} service will expire in {remaining_days} days.
Renew UA subscription at {url} to ensure
continued security coverage for your applications.
"""

CONTRACT_EXPIRED_GRACE_PERIOD_TMPL = """\
CAUTION: Your {title} service expired on {expired_date}.
Renew UA subscription at {url} to ensure
continued security coverage for your applications.
Your grace period will expire in {remaining_days} days.
"""

CONTRACT_EXPIRED_MOTD_PKGS_TMPL = """\
*Your {title} subscription has EXPIRED*

{pkg_num} additional security update(s) could have been applied via {title}.

Renew your UA services at {url}
"""

CONTRACT_EXPIRED_APT_PKGS_TMPL = """\
*Your {title} subscription has EXPIRED*
Enabling {title} service would provide security updates for following packages:
  {pkg_names}
{pkg_num} {name} security update(s) NOT APPLIED. Renew your UA services at
{url}
"""

DISABLED_MOTD_NO_PKGS_TMPL = """\
Enable {title} to receive additional future security updates.
See {url} or run: sudo ua status
"""

CONTRACT_EXPIRED_APT_NO_PKGS_TMPL = (
    """\
*Your {title} subscription has EXPIRED*
"""
    + DISABLED_MOTD_NO_PKGS_TMPL
)


DISABLED_APT_PKGS_TMPL = """\
*The following packages could receive security updates \
with {title} service enabled:
  {pkg_names}
Learn more about {title} service {eol_release}at {url}
"""

UBUNTU_NO_WARRANTY = """\
Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
applicable law.
"""

APT_PROXY_CONFIG_HEADER = """\
/*
 * Autogenerated by ubuntu-advantage-tools
 * Do not edit this file directly
 *
 * To change what ubuntu-advantage-tools sets, run one of the following:
 * Substitute "apt_https_proxy" for "apt_http_proxy" as necessary.
 *   sudo ua config set apt_http_proxy=<value>
 *   sudo ua config unset apt_http_proxy
 */
"""

UACLIENT_CONF_HEADER = """\
# Ubuntu-Advantage client config file.
# If you modify this file, run "ua refresh config" to ensure changes are
# picked up by Ubuntu-Advantage client.

"""

SETTING_SERVICE_PROXY = "Setting {service} proxy"
ERROR_USING_PROXY = (
    'Error trying to use "{proxy}" as proxy to reach "{test_url}": {error}'
)

PROXY_DETECTED_BUT_NOT_CONFIGURED = """\
No proxy set in config; however, proxy is configured for: {{services}}.
See {docs_url} for more information on ua proxy configuration.
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
This machine is not attached to a UA subscription.
See """
    + BASE_UA_URL,
)

ENABLE_FAILURE_UNATTACHED = FormattedNamedMessage(
    "enable-failure-unattached",
    """\
To use '{name}' you need an Ubuntu Advantage subscription
Personal and community subscriptions are available at no charge
See """
    + BASE_UA_URL,
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
{title} is not currently enabled\nSee: sudo ua status""",
)

ALREADY_ENABLED = FormattedNamedMessage(
    "service-already-enabled",
    """\
{title} is already enabled.\nSee: sudo ua status""",
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

APT_INSTALL_FAILED = NamedMessage("apt-install-failes", "APT install failed.")

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
Ubuntu Advantage server provided no aptURL directive for {entitlement_name}""",
)

ALREADY_ATTACHED = FormattedNamedMessage(
    name="already-attached",
    msg=(
        "This machine is already attached to '{account_name}'\n"
        "To use a different subscription first run: sudo ua detach."
    ),
)

ALREADY_ATTACHED_ON_PRO = FormattedNamedMessage(
    "already-attached-on-pro",
    """\
Skipping attach: Instance '{instance_id}' is already attached.""",
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
Attach requires a token: sudo ua attach <TOKEN>
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
Failed to enable default services, check: sudo ua status""",
)

INVALID_CONTRACT_DELTAS_SERVICE_TYPE = FormattedNamedMessage(
    "invalid-contract-deltas-service-type",
    "Could not determine contract delta service type {orig} {new}",
)

INVALID_SERVICE_OP_FAILURE = FormattedNamedMessage(
    "invalid-service-or-failure",
    """\
Cannot {operation} unknown service '{name}'.
{service_msg}""",
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
    "Livepatch is not currently supported for the real-time kernel.",
)
REALTIME_BETA_FLAG_REQUIRED = NamedMessage(
    "beta-flag-required",
    "Use `ua enable realtime-kernel --beta` to acknowledge the real-time"
    " kernel is currently in beta and comes with no support.",
)
REALTIME_BETA_PROMPT = """\
The real-time kernel is a beta version of the 22.04 Ubuntu kernel with the
PREEMPT_RT patchset integrated for x86_64 and ARM64.

{bold}You will not be able to revert to your original kernel after enabling\
 real-time.{end_bold}

Do you want to continue? [ default = Yes ]: (Y/n) """.format(
    bold=TxtColor.BOLD, end_bold=TxtColor.ENDC
)
REALTIME_PRE_DISABLE_PROMPT = """\
This will disable the Real-Time Kernel entitlement but the Real-Time Kernel\
 will remain installed.
Are you sure? (y/N) """

REALTIME_ERROR_INSTALL_ON_CONTAINER = NamedMessage(
    "realtime-error-install-on-container",
    "Cannot install Real-Time Kernel on a container.",
)


LOG_CONNECTIVITY_ERROR_TMPL = CONNECTIVITY_ERROR.msg + " {error}"
LOG_CONNECTIVITY_ERROR_WITH_URL_TMPL = (
    CONNECTIVITY_ERROR.msg + " Failed to access URL: {url}. {error}"
)
