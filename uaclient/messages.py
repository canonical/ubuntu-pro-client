from uaclient.defaults import BASE_UA_URL, DOCUMENTATION_URL


class NamedMessage:
    def __init__(self, name: str, msg: str):
        self.name = name
        self.msg = msg


class TxtColor:
    OKGREEN = "\033[92m"
    DISABLEGREY = "\033[37m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


OKGREEN_CHECK = TxtColor.OKGREEN + "✔" + TxtColor.ENDC
FAIL_X = TxtColor.FAIL + "✘" + TxtColor.ENDC

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
APT_INSTALL_FAILED = "APT install failed."
APT_UPDATE_FAILED = "APT update failed."
APT_UPDATE_INVALID_URL_CONFIG = (
    "APT update failed to read APT config for the following URL{}:\n{}."
)
APT_POLICY_FAILED = "Failure checking APT policy."
APT_UPDATING_LISTS = "Updating package lists"
CONNECTIVITY_ERROR = """\
Failed to connect to authentication server
Check your Internet connection and try again."""
LOG_CONNECTIVITY_ERROR_TMPL = CONNECTIVITY_ERROR + " {error}"
LOG_CONNECTIVITY_ERROR_WITH_URL_TMPL = (
    CONNECTIVITY_ERROR + " Failed to access URL: {url}. {error}"
)
SSL_VERIFICATION_ERROR_CA_CERTIFICATES = """\
Failed to access URL: {url}
Cannot verify certificate of server
Please install "ca-certificates" and try again."""
SSL_VERIFICATION_ERROR_OPENSSL_CONFIG = """\
Failed to access URL: {url}
Cannot verify certificate of server
Please check your openssl configuration."""
NONROOT_USER = "This command must be run as root (try using sudo)."
ALREADY_DISABLED_TMPL = """\
{title} is not currently enabled\nSee: sudo ua status"""
ENABLED_FAILED_TMPL = "Could not enable {title}."
DISABLE_FAILED_TMPL = "Could not disable {title}."
ENABLED_TMPL = "{title} enabled"
ALREADY_ATTACHED = """\
This machine is already attached to '{account_name}'
To use a different subscription first run: sudo ua detach."""
ALREADY_ATTACHED_ON_PRO = """\
Skipping attach: Instance '{instance_id}' is already attached."""
ALREADY_ENABLED_TMPL = """\
{title} is already enabled.\nSee: sudo ua status"""
INAPPLICABLE_ARCH_TMPL = """\
{title} is not available for platform {arch}.
Supported platforms are: {supported_arches}."""
INAPPLICABLE_SERIES_TMPL = """\
{title} is not available for Ubuntu {series}."""
INAPPLICABLE_KERNEL_TMPL = """\
{title} is not available for kernel {kernel}.
Supported flavors are: {supported_kernels}."""
INAPPLICABLE_KERNEL_VER_TMPL = """\
{title} is not available for kernel {kernel}.
Minimum kernel version required: {min_kernel}."""
UNENTITLED_TMPL = (
    """\
This subscription is not entitled to {title}
For more information see: """
    + BASE_UA_URL
    + "."
)
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
UNATTACHED = (
    """\
This machine is not attached to a UA subscription.
See """
    + BASE_UA_URL
)
MISSING_APT_URL_DIRECTIVE = """\
Ubuntu Advantage server provided no aptURL directive for {entitlement_name}"""
NO_ACTIVE_OPERATIONS = """No Ubuntu Advantage operations are running"""
LOCK_HELD = """Operation in progress: {lock_holder} (pid:{pid})"""
LOCK_HELD_ERROR = (
    """\
Unable to perform: {lock_request}.
"""
    + LOCK_HELD
)
REBOOT_SCRIPT_FAILED = (
    "Failed running reboot_cmds script. See: /var/log/ubuntu-advantage.log"
)
LIVEPATCH_LTS_REBOOT_REQUIRED = (
    "Livepatch support requires a system reboot across LTS upgrade."
)
SNAPD_DOES_NOT_HAVE_WAIT_CMD = (
    "snapd does not have wait command.\n"
    "Enabling Livepatch can fail under this scenario\n"
    "Please, upgrade snapd if Livepatch enable fails and try again."
)
FIPS_INSTALL_OUT_OF_DATE = (
    "This FIPS install is out of date, run: sudo ua enable fips"
)
FIPS_REBOOT_REQUIRED = (
    "FIPS support requires system reboot to complete configuration."
)
FIPS_DISABLE_REBOOT_REQUIRED = (
    "Disabling FIPS requires system reboot to complete operation."
)
FIPS_PACKAGE_NOT_AVAILABLE = "{service} {pkg} package could not be installed"
FIPS_RUN_APT_UPGRADE = """\
Please run `apt upgrade` to ensure all FIPS packages are updated to the correct
version.
"""
ATTACH_FORBIDDEN_EXPIRED = """\
Contract \"{contract_id}\" expired on {date}"""
ATTACH_FORBIDDEN_NOT_YET = """\
Contract \"{contract_id}\" is not effective until {date}"""
ATTACH_FORBIDDEN_NEVER = """\
Contract \"{contract_id}\" has never been effective"""
ATTACH_FORBIDDEN = """\
Attach denied:
{{reason}}
Visit {url} to manage contract tokens.""".format(
    url=BASE_UA_URL
)
ATTACH_EXPIRED_TOKEN = (
    """\
Expired token or contract. To obtain a new token visit: """
    + BASE_UA_URL
)
ATTACH_INVALID_TOKEN = (
    """\
Invalid token. See """
    + BASE_UA_URL
)
ATTACH_TOKEN_ARG_XOR_CONFIG = """\
Do not pass the TOKEN arg if you are using --attach-config.
Include the token in the attach-config file instead.
    """
ATTACH_REQUIRES_TOKEN = (
    """\
Attach requires a token: sudo ua attach <TOKEN>
To obtain a token please visit: """
    + BASE_UA_URL
    + "."
)
ATTACH_FAILURE = (
    """\
Failed to attach machine. See """
    + BASE_UA_URL
)
ATTACH_FAILURE_DEFAULT_SERVICES = """\
Failed to enable default services, check: sudo ua status"""
ATTACH_SUCCESS_TMPL = """\
This machine is now attached to '{contract_name}'
"""
ATTACH_SUCCESS_NO_CONTRACT_NAME = """\
This machine is now successfully attached'
"""

JSON_FORMAT_REQUIRE_ASSUME_YES = """\
json formatted response requires --assume-yes flag."""

INVALID_SERVICE_OP_FAILURE_TMPL = """\
Cannot {operation} unknown service '{name}'.
{service_msg}"""
UNEXPECTED_ERROR = """\
Unexpected error(s) occurred.
For more details, see the log: /var/log/ubuntu-advantage.log
To file a bug run: ubuntu-bug ubuntu-advantage-tools"""
ENABLE_FAILURE_UNATTACHED_TMPL = (
    """\
To use '{name}' you need an Ubuntu Advantage subscription
Personal and community subscriptions are available at no charge
See """
    + BASE_UA_URL
)
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

INCOMPATIBLE_SERVICE_STOPS_ENABLE = """\
Cannot enable {service_being_enabled} when \
{incompatible_service} is enabled."""

REQUIRED_SERVICE_STOPS_ENABLE = """\
Cannot enable {service_being_enabled} when {required_service} is disabled.
"""

DEPENDENT_SERVICE_STOPS_DISABLE = """\
Cannot disable {service_being_disabled} when {dependent_service} is enabled.
"""
FAILED_DISABLING_DEPENDENT_SERVICE = """\
Cannot disable dependent service: {required_service}"""
DISABLING_DEPENDENT_SERVICE = """\
Disabling dependent service: {required_service}"""

FIPS_BLOCK_ON_CLOUD = (
    """\
Ubuntu {series} does not provide {cloud} optimized FIPS kernel
For help see: """
    + BASE_UA_URL
    + "."
)
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
NOT_SETTING_PROXY_INVALID_URL = (
    '"{proxy}" is not a valid url. Not setting as proxy.'
)
NOT_SETTING_PROXY_NOT_WORKING = (
    '"{proxy}" is not working. Not setting as proxy.'
)
ERROR_USING_PROXY = (
    'Error trying to use "{proxy}" as proxy to reach "{test_url}": {error}'
)

PROXY_DETECTED_BUT_NOT_CONFIGURED = """\
No proxy set in config; however, proxy is configured for: {{services}}.
See {docs_url} for more information on ua proxy configuration.
""".format(
    docs_url=DOCUMENTATION_URL
)

FIPS_UPDATES_INVALIDATES_FIPS = NamedMessage(
    "fips-updates-invalidates-fips",
    "FIPS cannot be enabled if FIPS Updates has ever been enabled because"
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
ERROR_INVALID_CONFIG_VALUE = """\
Invalid value for {path_to_value} in /etc/ubuntu-advantage/uaclient.conf. \
Expected {expected_value}, found {value}."""
INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY = """\
Failed to find the machine token overlay file: {file_path}"""
ERROR_JSON_DECODING_IN_FILE = """\
Found error: {error} when reading json file: {file_path}"""
