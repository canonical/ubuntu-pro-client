import sys
from gettext import NullTranslations, translation
from typing import Callable, Dict, Optional

from uaclient.messages import urls

if sys.stdout.encoding is None or "UTF-8" not in sys.stdout.encoding.upper():
    t = NullTranslations()
else:
    t = translation("ubuntu-pro", "/usr/share/locale", fallback=True)


class PluralizableString:
    def __init__(self, pluralize_fn: Callable):
        self.pluralize_fn = pluralize_fn

    def pluralize(self, n: int) -> str:
        return self.pluralize_fn(n)


P = PluralizableString


###############################################################################
#                              MISCELLANEOUS                                  #
###############################################################################
# Things that don't fit with the others. Some of these are used as pieces in
# messages below.
# If one of the groups of messages in this section grows enough, it should get
# its own section.


class TxtColor:
    OKGREEN = "\033[92m"
    DISABLEGREY = "\033[37m"
    INFOBLUE = "\033[94m"
    WARNINGYELLOW = "\033[93m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


STANDALONE_YES = t.gettext("yes")
STANDALONE_NO = t.gettext("no")

OKGREEN_CHECK = TxtColor.OKGREEN + "✔" + TxtColor.ENDC
FAIL_X = TxtColor.FAIL + "✘" + TxtColor.ENDC
BLUE_INFO = TxtColor.INFOBLUE + "[info]" + TxtColor.ENDC

PROMPT_YES_NO = t.gettext("""Are you sure? (y/N) """)
PROCEED_YES_NO = t.gettext("Do you want to proceed? (y/N) ")

CLI_INTERRUPT_RECEIVED = t.gettext("Interrupt received; exiting.")

LOCK_HELD = t.gettext("""Operation in progress: {lock_holder} (pid:{pid})""")

REFRESH_CONTRACT_SUCCESS = t.gettext(
    "Successfully refreshed your subscription."
)
REFRESH_CONFIG_SUCCESS = t.gettext(
    "Successfully processed your pro configuration."
)
REFRESH_MESSAGES_SUCCESS = t.gettext(
    "Successfully updated Ubuntu Pro related APT and MOTD messages."
)

REBOOT_SCRIPT_FAILED = t.gettext(
    "Failed running reboot_cmds script. See: /var/log/ubuntu-advantage.log"
)

RELEASE_UPGRADE_APT_LOCK_HELD_WILL_WAIT = t.gettext(
    "APT lock is held. Ubuntu Pro configuration will wait until it is released"
)
RELEASE_UPGRADE_NO_PAST_RELEASE = t.gettext(
    "Could not find past release for {release}"
)
RELEASE_UPGRADE_STARTING = t.gettext(
    "Starting upgrade of Ubuntu Pro service configuration"
)
RELEASE_UPGRADE_SUCCESS = t.gettext(
    "Finished upgrade of Ubuntu Pro service configuration"
)

PRO_ONLY_ALLOWED_FOR_RELEASE = t.gettext(
    "Detaching Ubuntu Pro. Previously attached subscription \
was only valid for Ubuntu {release} ({series_codename}) release."
)

MISSING_YAML_MODULE = t.gettext(
    """\
Couldn't import the YAML module.
Make sure the 'python3-yaml' package is installed correctly
and /usr/lib/python3/dist-packages is in your PYTHONPATH."""
)
BROKEN_YAML_MODULE = t.gettext(
    "Error while trying to parse a yaml file using 'yaml' from {path}"
)

SNAPD_DOES_NOT_HAVE_WAIT_CMD = t.gettext(
    "snapd does not have a wait command.\n"
    "Enabling Livepatch can fail under this scenario.\n"
    "Please, upgrade snapd if Livepatch enable fails and try again."
)

WARN_NEW_VERSION_AVAILABLE_CLI = (
    "\n"
    + BLUE_INFO
    + t.gettext(
        """\
 A new version is available: {version}
Please run:
    sudo apt install ubuntu-pro-client
to get the latest bug fixes and new features."""
    )
)

UNKNOWN_ERROR = t.gettext("an unknown error")

###############################################################################
#                      GENERIC SYSTEM OPERATIONS                              #
###############################################################################


EXECUTING_COMMAND = t.gettext("Executing `{command}`")
EXECUTING_COMMAND_FAILED = t.gettext("Executing `{command}` failed.")
SUBP_INVALID_COMMAND = t.gettext("Invalid command specified '{cmd}'.")
SUBP_COMMAND_FAILED = t.gettext(
    "Failed running command '{cmd}' [exit({exit_code})]." " Message: {stderr}"
)

INSTALLING_PACKAGES = t.gettext("Installing {packages}")
INSTALLING_SERVICE_PACKAGES = t.gettext("Installing {title} packages")
INSTALLING_REQUIRED_SNAPS = t.gettext("Installing required snaps")
INSTALLING_REQUIRED_SNAP_PACKAGE = t.gettext(
    "Installing required snap: {snap}"
)
SKIPPING_INSTALLING_PACKAGES = t.gettext(
    "Skipping installing packages: {packages}"
)
UNINSTALLING_PACKAGES = t.gettext("Uninstalling {packages}")
UNINSTALLING_PACKAGES_FAILED = t.gettext(
    "Failure when uninstalling {packages}"
)
FIX_CANNOT_INSTALL_PACKAGE = t.gettext(
    "Cannot install package {package} version {version}"
)

APT_POLICY_FAILED = t.gettext("Failure checking APT policy.")
APT_UPDATING_LISTS = t.gettext("Updating package lists")
APT_UPDATING_LIST = t.gettext("Updating {name} package lists")
APT_UPDATE_FAILED = t.gettext("APT update failed.")
APT_INSTALL_FAILED = t.gettext("APT install failed.")

BACKING_UP_FILE = t.gettext("Backing up {original} as {backup}")
WARN_PACKAGES_REMOVAL = t.gettext("The following package(s) will be REMOVED:")
WARN_PACKAGES_REINSTALL = t.gettext(
    "The following package(s) will be reinstalled from the archive:"
)


###############################################################################
#                   MOTD/APTNEWS CONTRACT STATUS                              #
###############################################################################


CONTRACT_EXPIRED_WITH_PKGS = P(
    lambda n: t.ngettext(
        """\
*Your Ubuntu Pro subscription has EXPIRED*
{{pkg_num}} additional security update requires Ubuntu Pro with '{{service}}' enabled.
Renew your subscription at {url}""",  # noqa: E501
        """\
*Your Ubuntu Pro subscription has EXPIRED*
{{pkg_num}} additional security updates require Ubuntu Pro with '{{service}}' enabled.
Renew your subscription at {url}""",  # noqa: E501
        n,
    ).format(url=urls.PRO_DASHBOARD)
)
CONTRACT_EXPIRES_SOON = P(
    lambda n: t.ngettext(
        """\
CAUTION: Your Ubuntu Pro subscription will expire in {{remaining_days}} day.
Renew your subscription at {url} to ensure
continued security coverage for your applications.""",
        """\
CAUTION: Your Ubuntu Pro subscription will expire in {{remaining_days}} days.
Renew your subscription at {url} to ensure
continued security coverage for your applications.""",
        n,
    ).format(url=urls.PRO_DASHBOARD)
)
CONTRACT_EXPIRED_GRACE_PERIOD = P(
    lambda n: t.ngettext(
        """\
CAUTION: Your Ubuntu Pro subscription expired on {{expired_date}}.
Renew your subscription at {url} to ensure
continued security coverage for your applications.
Your grace period will expire in {{remaining_days}} day.""",
        """\
CAUTION: Your Ubuntu Pro subscription expired on {{expired_date}}.
Renew your subscription at {url} to ensure
continued security coverage for your applications.
Your grace period will expire in {{remaining_days}} days.""",
        n,
    ).format(url=urls.PRO_DASHBOARD)
)
CONTRACT_EXPIRED = t.gettext(
    """\
*Your Ubuntu Pro subscription has EXPIRED*
Renew your subscription at {url}"""
).format(url=urls.PRO_DASHBOARD)


###############################################################################
#                         CONFIGURATION                                       #
###############################################################################


SETTING_SERVICE_PROXY = t.gettext("Setting {service} proxy")
PROXY_DETECTED_BUT_NOT_CONFIGURED = t.gettext(
    """\
No proxy set in config; however, proxy is configured for: {{services}}.
See {url} for more information on pro proxy configuration.
"""
).format(url=urls.PRO_CLIENT_DOCS_PROXY_CONFIG)
SETTING_SERVICE_PROXY_SCOPE = t.gettext("Setting {scope} APT proxy")
CLI_CONFIG_GLOBAL_XOR_UA_PROXY = t.gettext(
    "\nError: Setting global apt proxy and pro scoped apt proxy at the"
    " same time is unsupported. No apt proxy is set."
)
WARNING_CONFIG_FIELD_RENAME = t.gettext(
    """\
Warning: {old} has been renamed to {new}."""
)
WARNING_APT_PROXY_OVERWRITE = t.gettext(
    """\
Warning: Setting the {current_proxy} proxy will overwrite the {previous_proxy}
proxy previously set via `pro config`.
"""
)
WARNING_DEPRECATED_FIELD = t.gettext(
    """\
Using deprecated "{old}" config field.
Please migrate to using "{new}"
"""
)

USER_CONFIG_MIGRATION_MIGRATING = t.gettext(
    "Migrating /etc/ubuntu-advantage/uaclient.conf"
)
USER_CONFIG_MIGRATION_WARNING_UACLIENT_CONF_LOAD = t.gettext(
    """\
Warning: Failed to load /etc/ubuntu-advantage/uaclient.conf.preinst-backup
         No automatic migration will occur.
         You may need to use "pro config set" to re-set your settings."""
)

USER_CONFIG_MIGRATION_WARNING_NEW_USER_CONFIG_WRITE = t.gettext(
    """\
Warning: Failed to migrate user_config from /etc/ubuntu-advantage/uaclient.conf
         Please run the following to keep your custom settings:"""
)

USER_CONFIG_MIGRATION_WARNING_NEW_UACLIENT_CONF_WRITE = t.gettext(
    """\
Warning: Failed to migrate /etc/ubuntu-advantage/uaclient.conf
         Please add following to uaclient.conf to keep your config:"""
)


###############################################################################
#               ATTACH/DETACH/ENABLE/DISABLE SUBCOMMAND                       #
###############################################################################


# ATTACH
AUTO_ATTACH_RUNNING = t.gettext(
    "Currently attempting to automatically attach this machine to "
    "an Ubuntu Pro subscription"
)
ATTACH_SUCCESS_TMPL = t.gettext(
    """\
This machine is now attached to '{contract_name}'
"""
)
ATTACH_SUCCESS_NO_CONTRACT_NAME = t.gettext(
    """\
This machine is now successfully attached'
"""
)
ENABLE_BY_DEFAULT_TMPL = t.gettext("Enabling default service {name}")
ENABLE_BY_DEFAULT_MANUAL_TMPL = t.gettext(
    """\
Service {name} is recommended by default. Run: sudo pro enable {name}"""
)
CLI_MAGIC_ATTACH_INIT = t.gettext("Initiating attach operation...")
CLI_MAGIC_ATTACH_FAILED = t.gettext("Failed to perform attach...")
CLI_MAGIC_ATTACH_SIGN_IN = t.gettext(
    """\
Please sign in to your Ubuntu Pro account at this link:
{url}
And provide the following code: {bold}{{user_code}}{end_bold}"""
).format(
    url=urls.PRO_ATTACH,
    bold=TxtColor.BOLD,
    end_bold=TxtColor.ENDC,
)
CLI_MAGIC_ATTACH_PROCESSING = t.gettext("Attaching the machine...")

LIMITED_TO_RELEASE = t.gettext(
    "Limited to release: Ubuntu {release} ({series_codename})."
)

# DETACH
DETACH_WILL_DISABLE = P(
    lambda n: t.ngettext(
        "Detach will disable the following service:",
        "Detach will disable the following services:",
        n,
    )
)
DETACH_SUCCESS = t.gettext("This machine is now detached.")

# ENABLE
REFRESH_CONTRACT_ENABLE = t.gettext(
    "One moment, checking your subscription first"
)
ENABLING_TMPL = t.gettext("Enabling {title}")
ENABLED_TMPL = t.gettext("{title} enabled")
ACCESS_ENABLED_TMPL = t.gettext("{title} access enabled")
ENABLE_FAILED = t.gettext("Could not enable {title}.")
INCOMPATIBLE_SERVICE = t.gettext(
    """\
{service_being_enabled} cannot be enabled with {incompatible_service}.
Disable {incompatible_service} and proceed to enable {service_being_enabled}? \
(y/N) """
)
DISABLING_INCOMPATIBLE_SERVICE = t.gettext(
    "Disabling incompatible service: {service}"
)
REQUIRED_SERVICE = t.gettext(
    """\
{service_being_enabled} cannot be enabled with {required_service} disabled.
Enable {required_service} and proceed to enable {service_being_enabled}? \
(y/N) """
)
ENABLING_REQUIRED_SERVICE = t.gettext("Enabling required service: {service}")
ENABLE_REBOOT_REQUIRED_TMPL = t.gettext(
    """\
A reboot is required to complete {operation}."""
)
CONFIGURING_APT_ACCESS = t.gettext("Configuring APT access to {service}")
AUTO_SELECTING_VARIANT = t.gettext(
    """\
No variant specified. To specify a variant, use the variant option.
Auto-selecting {variant} variant. Proceed? (y/N) """
)

# DISABLE
REMOVING_APT_CONFIGURATION = t.gettext("Removing APT access to {title}")
DISABLE_FAILED_TMPL = t.gettext("Could not disable {title}.")
DEPENDENT_SERVICE = t.gettext(
    """\
{dependent_service} depends on {service_being_disabled}.
Disable {dependent_service} and proceed to disable {service_being_disabled}? \
(y/N) """
)
DISABLING_DEPENDENT_SERVICE = t.gettext(
    """\
Disabling dependent service: {required_service}"""
)
APT_REMOVING_SOURCE_FILE = t.gettext("Removing apt source file: {filename}")
APT_REMOVING_PREFERENCES_FILE = t.gettext(
    "Removing apt preferences file: {filename}"
)
PURGING_PACKAGES = t.gettext(
    "Uninstalling all packages installed from {title}"
)

# Kernel checks for Purge
PURGE_EXPERIMENTAL = t.gettext(
    "(The --purge flag is still experimental - use with caution)"
)
PURGE_KERNEL_REMOVAL = t.gettext(
    "Purging the {service} packages would uninstall the following kernel(s):"
)
PURGE_CURRENT_KERNEL = t.gettext(
    "{kernel_version} is the current running kernel."
)
PURGE_NO_ALTERNATIVE_KERNEL = t.gettext(
    """\
No other valid Ubuntu kernel was found in the system.
Removing the package would potentially make the system unbootable.
Aborting.
"""
)
PURGE_KERNEL_CONFIRMATION = t.gettext(
    """\
If you cannot guarantee that other kernels in this system are bootable and
working properly, *do not proceed*. You may end up with an unbootable system.
"""
    + PROCEED_YES_NO
)

# These are for the retry-auto-attach functionality
AUTO_ATTACH_RETRY_NOTICE = t.gettext(
    """\
Failed to automatically attach to an Ubuntu Pro subscription {num_attempts} time(s).
The failure was due to: {reason}.
The next attempt is scheduled for {next_run_datestring}.
You can try manually with `sudo pro auto-attach`."""  # noqa: E501
)

AUTO_ATTACH_RETRY_TOTAL_FAILURE_NOTICE = t.gettext(
    """\
Failed to automatically attach to an Ubuntu Pro subscription {num_attempts} time(s).
The most recent failure was due to: {reason}.
Try re-launching the instance or report this issue by running `ubuntu-bug ubuntu-advantage-tools`
You can try manually with `sudo pro auto-attach`."""  # noqa: E501
)

RETRY_ERROR_DETAIL_INVALID_PRO_IMAGE = t.gettext(
    """\
Canonical servers did not recognize this machine as Ubuntu Pro: \"{detail}\""""
)
RETRY_ERROR_DETAIL_NON_AUTO_ATTACH_IMAGE = t.gettext(
    "Canonical servers did not recognize this image as Ubuntu Pro"
)
RETRY_ERROR_DETAIL_LOCK_HELD = t.gettext("the pro lock was held by pid {pid}")
RETRY_ERROR_DETAIL_CONTRACT_API_ERROR = t.gettext(
    'an error from Canonical servers: "{error_msg}"'
)
RETRY_ERROR_DETAIL_CONNECTIVITY_ERROR = t.gettext("a connectivity error")
RETRY_ERROR_DETAIL_URL_ERROR_URL = t.gettext("an error while reaching {url}")

# These are related messages but actually occur during a "refresh"
DISABLE_DURING_CONTRACT_REFRESH = t.gettext(
    "Due to contract refresh, '{service}' is now disabled."
)
UNABLE_TO_DISABLE_DURING_CONTRACT_REFRESH = t.gettext(
    "Unable to disable '{service}' as recommended during contract"
    " refresh. Service is still active. See"
    " `pro status`"
)
SERVICE_UPDATING_CHANGED_DIRECTIVES = t.gettext(
    "Updating '{service}' on changed directives."
)
REPO_UPDATING_APT_SOURCES = t.gettext(
    "Updating '{service}' apt sources list on changed directives."
)
REPO_REFRESH_INSTALLING_PACKAGES = t.gettext(
    "Installing packages on changed directives: {packages}"
)


###############################################################################
#                           FIX SUBCOMMAND                                    #
###############################################################################


SECURITY_FIX_ATTACH_PROMPT = t.gettext(
    """\
Choose: [S]ubscribe at {url} [A]ttach existing token [C]ancel"""
).format(url=urls.PRO_SUBSCRIBE)
SECURITY_FIX_ENABLE_PROMPT = t.gettext(
    """\
Choose: [E]nable {service} [C]ancel"""
)
SECURITY_FIX_RENEW_PROMPT = t.gettext(
    """\
Choose: [R]enew your subscription (at {url}) [C]ancel"""
).format(url=urls.PRO_DASHBOARD)
SECURITY_FIX_RELEASE_STREAM = t.gettext("A fix is available in {fix_stream}.")
SECURITY_UPDATE_NOT_INSTALLED = t.gettext("The update is not yet installed.")
SECURITY_UPDATE_NOT_INSTALLED_SUBSCRIPTION = t.gettext(
    """\
The update is not installed because this system is not attached to a
subscription.
"""
)
SECURITY_UPDATE_NOT_INSTALLED_EXPIRED = t.gettext(
    """\
The update is not installed because this system is attached to an
expired subscription.
"""
)
SECURITY_SERVICE_DISABLED = t.gettext(
    """\
The update is not installed because this system does not have
{service} enabled.
"""
)
SECURITY_UPDATE_INSTALLED = t.gettext("The update is already installed.")
SECURITY_USE_PRO_TMPL = t.gettext(
    """\
For easiest security on {title}, use Ubuntu Pro instances.
Learn more at {cloud_specific_url}"""
)

FIX_ISSUE_CONTEXT_REQUESTED = t.gettext("requested")
FIX_ISSUE_CONTEXT_RELATED = t.gettext("related")
SECURITY_ISSUE_RESOLVED = OKGREEN_CHECK + t.gettext(" {issue} is resolved.")
SECURITY_ISSUE_RESOLVED_ISSUE_CONTEXT = OKGREEN_CHECK + t.gettext(
    " {issue} [{context}] is resolved."
)
SECURITY_ISSUE_NOT_RESOLVED = FAIL_X + t.gettext(" {issue} is not resolved.")
SECURITY_ISSUE_NOT_RESOLVED_ISSUE_CONTEXT = FAIL_X + t.gettext(
    " {issue} [{context}] is not resolved."
)
SECURITY_ISSUE_UNAFFECTED = OKGREEN_CHECK + t.gettext(
    " {issue} does not affect your system."
)
SECURITY_ISSUE_UNAFFECTED_ISSUE_CONTEXT = OKGREEN_CHECK + t.gettext(
    " {issue} [{context}] does not affect your system."
)
SECURITY_PKG_STILL_AFFECTED = P(
    lambda n: t.ngettext(
        "{num_pkgs} package is still affected: {pkgs}",
        "{num_pkgs} packages are still affected: {pkgs}",
        n,
    )
)
SECURITY_AFFECTED_PKGS = P(
    lambda n: t.ngettext(
        "{count} affected source package is installed: {pkgs}",
        "{count} affected source packages are installed: {pkgs}",
        n,
    )
)
SECURITY_NO_AFFECTED_PKGS = t.gettext(
    "No affected source packages are installed."
)
CVE_FIXED = t.gettext("{issue} is resolved.")
CVE_FIXED_BY_LIVEPATCH = OKGREEN_CHECK + t.gettext(
    " {issue} is resolved by livepatch patch version: {version}."
)
SECURITY_DRY_RUN_UA_SERVICE_NOT_ENABLED = t.gettext(
    """\
{bold}Ubuntu Pro service: {{service}} is not enabled.
To proceed with the fix, a prompt would ask permission to automatically enable
this service.
{{{{ pro enable {{service}} }}}}{end_bold}"""
).format(bold=TxtColor.BOLD, end_bold=TxtColor.ENDC)
SECURITY_DRY_RUN_UA_NOT_ATTACHED = t.gettext(
    """\
{bold}The machine is not attached to an Ubuntu Pro subscription.
To proceed with the fix, a prompt would ask to attach
the machine to a subscription or use an existing token.
{{ pro attach }}{end_bold}"""
).format(bold=TxtColor.BOLD, end_bold=TxtColor.ENDC)
SECURITY_DRY_RUN_UA_EXPIRED_SUBSCRIPTION = t.gettext(
    """\
{bold}The machine has an expired subscription.
To proceed with the fix, a prompt would ask to attach the machine to a
new subscription or use a new Ubuntu Pro subscription token.
{{ pro detach --assume-yes }}
{{ pro attach }}{end_bold}"""
).format(bold=TxtColor.BOLD, end_bold=TxtColor.ENDC)
SECURITY_DRY_RUN_WARNING = t.gettext(
    """\
{bold}WARNING: The option --dry-run is being used.
No packages will be installed when running this command.{end_bold}"""
).format(bold=TxtColor.BOLD, end_bold=TxtColor.ENDC)
SECURITY_UA_SERVICE_NOT_ENABLED = t.gettext(
    """\
Error: Ubuntu Pro service: {service} is not enabled.
Without it, we cannot fix the system."""
)
SECURITY_UA_SERVICE_NOT_ENTITLED = t.gettext(
    """\
Error: The current Ubuntu Pro subscription is not entitled to: {service}.
Without it, we cannot fix the system."""
)
SECURITY_UA_SERVICE_REQUIRED = t.gettext(
    """\
{service} is required for upgrade."""
)
SECURITY_UA_SERVICE_WITH_EXPIRED_SUB = t.gettext(
    """\
{service} is required for upgrade, but current subscription is expired."""
)
SECURITY_UA_SERVICE_NOT_ENABLED_SHORT = t.gettext(
    """\
{service} is required for upgrade, but it is not enabled."""
)
SECURITY_UA_APT_FAILURE = t.gettext(
    """\
APT failed to install the package.
"""
)
SECURITY_CVE_STATUS_NEEDED = t.gettext(
    """\
Sorry, no fix is available yet."""
)
SECURITY_CVE_STATUS_TRIAGE = t.gettext(
    """\
Ubuntu security engineers are investigating this issue."""
)
SECURITY_CVE_STATUS_PENDING = t.gettext(
    """\
A fix is coming soon. Try again tomorrow."""
)
SECURITY_CVE_STATUS_IGNORED = t.gettext(
    """\
Sorry, no fix is available."""
)
SECURITY_CVE_STATUS_DNE = t.gettext(
    """\
Source package does not exist on this release."""
)
SECURITY_CVE_STATUS_NOT_AFFECTED = t.gettext(
    """\
Source package is not affected on this release."""
)
SECURITY_CVE_STATUS_UNKNOWN = t.gettext(
    """\
UNKNOWN: {status}"""
)

SECURITY_FOUND_CVES = t.gettext("Associated CVEs:")
SECURITY_FOUND_LAUNCHPAD_BUGS = t.gettext("Found Launchpad bugs:")
SECURITY_FIXING_REQUESTED_USN = t.gettext(
    """\
Fixing requested {issue_id}"""
)
SECURITY_FIXING_RELATED_USNS = t.gettext(
    """\
Fixing related USNs:"""
)
SECURITY_RELATED_USNS = t.gettext(
    """\
Found related USNs:\n- {related_usns}"""
)
SECURITY_USN_SUMMARY = t.gettext(
    """\
Summary:"""
)
SECURITY_RELATED_USN_ERROR = t.gettext(
    """\
Even though a related USN failed to be fixed, note
that {{issue_id}} was fixed. Related USNs do not
affect the original USN. Learn more about the related
USNs, please refer to this page:

{url}
"""
).format(url=urls.PRO_CLIENT_DOCS_RELATED_USNS)
SECURITY_UBUNTU_STANDARD_UPDATES_POCKET = t.gettext("Ubuntu standard updates")
SECURITY_UA_INFRA_POCKET = t.gettext("Ubuntu Pro: ESM Infra")
SECURITY_UA_APPS_POCKET = t.gettext("Ubuntu Pro: ESM Apps")

SECURITY_APT_NON_ROOT = t.gettext(
    """\
Package fixes cannot be installed.
To install them, run this command as root (try using sudo)"""
)

PROMPT_ENTER_TOKEN = t.gettext(
    """\
Enter your token (from {url}) to attach this system:"""
).format(url=urls.PRO_DASHBOARD)
PROMPT_EXPIRED_ENTER_TOKEN = t.gettext(
    """\
Enter your new token to renew Ubuntu Pro subscription on this system:"""
)


###############################################################################
#                      SECURITYSTATUS SUBCOMMAND                              #
###############################################################################


SS_SUMMARY_TOTAL = t.gettext("{count} packages installed:")
SS_SUMMARY_ARCHIVE = P(
    lambda n: t.ngettext(
        "{offset}{count} package from Ubuntu {repository} repository",
        "{offset}{count} packages from Ubuntu {repository} repository",
        n,
    )
)
SS_SUMMARY_THIRD_PARTY = P(
    lambda n: t.ngettext(
        "{offset}{count} package from a third party",
        "{offset}{count} packages from third parties",
        n,
    )
)
SS_SUMMARY_UNAVAILABLE = P(
    lambda n: t.ngettext(
        "{offset}{count} package no longer available for download",
        "{offset}{count} packages no longer available for download",
        n,
    )
)

SS_HELP_CALL = t.gettext(
    """\
To get more information about the packages, run
    pro security-status --help
for a list of available options."""
)

SS_UPDATE_CALL = t.gettext(
    """\
 Make sure to run
    sudo apt update
to get the latest package information from apt."""
)
SS_UPDATE_DAYS = (
    t.gettext("The system apt information was updated {days} day(s) ago.")
    + SS_UPDATE_CALL
)
SS_UPDATE_UNKNOWN = (
    t.gettext("The system apt cache may be outdated.") + SS_UPDATE_CALL
)

SS_INTERIM_SUPPORT = t.gettext(
    "Main/Restricted packages receive updates until {date}."
)
SS_LTS_SUPPORT = t.gettext(
    """\
This machine is receiving security patching for Ubuntu Main/Restricted
repository until {date}."""
)

SS_IS_ATTACHED = t.gettext(
    "This machine is attached to an Ubuntu Pro subscription."
)
SS_IS_NOT_ATTACHED = t.gettext(
    "This machine is NOT attached to an Ubuntu Pro subscription."
)

SS_THIRD_PARTY = t.gettext(
    """\
Packages from third parties are not provided by the official Ubuntu
archive, for example packages from Personal Package Archives in Launchpad."""
)
SS_UNAVAILABLE = t.gettext(
    """\
Packages that are not available for download may be left over from a
previous release of Ubuntu, may have been installed directly from a
.deb file, or are from a source which has been disabled."""
)

SS_NO_SECURITY_COVERAGE = t.gettext(
    """\
This machine is NOT receiving security patches because the LTS period has ended
and esm-infra is not enabled."""
)

SS_SERVICE_ADVERTISE = t.gettext(
    """\
Ubuntu Pro with '{service}' enabled provides security updates for
{repository} packages until {year}."""
)
SS_SERVICE_ADVERTISE_COUNTS = P(
    lambda n: t.ngettext(
        "There is {updates} pending security update.",
        "There are {updates} pending security updates.",
        n,
    )
)

SS_SERVICE_ENABLED = t.gettext(
    """\
{repository} packages are receiving security updates from
Ubuntu Pro with '{service}' enabled until {year}."""
)
SS_SERVICE_ENABLED_COUNTS = P(
    lambda n: t.ngettext(
        """\
You have received {updates} security
update.""",
        """\
You have received {updates} security
updates.""",
        n,
    )
)

SS_SERVICE_COMMAND = t.gettext("Enable {service} with: pro enable {service}")
SS_LEARN_MORE = t.gettext(
    """\
Try Ubuntu Pro with a free personal subscription on up to 5 machines.
Learn more at {url}
"""
).format(url=urls.PRO_HOME_PAGE)

SS_SHOW_HINT = t.gettext(
    """\
For example, run:
    apt-cache show {package}
to learn more about that package."""
)

SS_NO_THIRD_PARTY = t.gettext(
    "You have no packages installed from a third party."
)
SS_NO_UNAVAILABLE = t.gettext(
    "You have no packages installed that are no longer available."
)
SS_NO_INTERIM_PRO_SUPPORT = t.gettext(
    "Ubuntu Pro is not available for non-LTS releases."
)

SS_SERVICE_HELP = t.gettext("Run 'pro help {service}' to learn more")

SS_UPDATES_AVAILABLE = t.gettext(
    "Installed packages with an available {service} update:"
)
SS_UPDATES_INSTALLED = t.gettext(
    "Installed packages with an {service} update applied:"
)
SS_OTHER_PACKAGES = t.gettext("Installed packages covered by {service}:")
SS_FURTHER_OTHER_PACKAGES = t.gettext(
    "Further installed packages covered by {service}:"
)
SS_PACKAGES_HEADER = t.gettext("Packages:")


###############################################################################
#                           STATUS SUBCOMMAND                                 #
###############################################################################


STATUS_SERVICE = t.gettext("SERVICE")
STATUS_AVAILABLE = t.gettext("AVAILABLE")
STATUS_ENTITLED = t.gettext("ENTITLED")
STATUS_AUTO_ENABLED = t.gettext("AUTO_ENABLED")
STATUS_STATUS = t.gettext("STATUS")
STATUS_DESCRIPTION = t.gettext("DESCRIPTION")
STATUS_NOTICES = t.gettext("NOTICES")
STATUS_FEATURES = t.gettext("FEATURES")

STATUS_ENTITLED_ENTITLED = STANDALONE_YES
STATUS_ENTITLED_UNENTITLED = STANDALONE_NO
STATUS_STATUS_ENABLED = t.gettext("enabled")
STATUS_STATUS_DISABLED = t.gettext("disabled")
STATUS_STATUS_INAPPLICABLE = t.gettext("n/a")
STATUS_STATUS_UNAVAILABLE = "—"
STATUS_STATUS_WARNING = t.gettext("warning")
STATUS_SUPPORT_ESSENTIAL = t.gettext("essential")
STATUS_SUPPORT_STANDARD = t.gettext("standard")
STATUS_SUPPORT_ADVANCED = t.gettext("advanced")

STATUS_CONTRACT_EXPIRES_UNKNOWN = t.gettext("Unknown/Expired")

STATUS_FOOTER_ENABLE_SERVICES_WITH = t.gettext(
    "Enable services with: {command}"
)
STATUS_FOOTER_ACCOUNT = t.gettext("Account")
STATUS_FOOTER_SUBSCRIPTION = t.gettext("Subscription")
STATUS_FOOTER_VALID_UNTIL = t.gettext("Valid until")
STATUS_FOOTER_SUPPORT_LEVEL = t.gettext("Technical support level")

STATUS_TOKEN_NOT_VALID = t.gettext("This token is not valid.")
NO_ACTIVE_OPERATIONS = t.gettext("""No Ubuntu Pro operations are running""")

STATUS_NO_SERVICES_AVAILABLE = t.gettext(
    """No Ubuntu Pro services are available to this system."""
)
STATUS_ALL_HINT = t.gettext(
    "For a list of all Ubuntu Pro services, run 'pro status --all'"
)
STATUS_SERVICE_HAS_VARIANTS = t.gettext(" * Service has variants")
STATUS_ALL_HINT_WITH_VARIANTS = t.gettext(
    """\
For a list of all Ubuntu Pro services and variants, run 'pro status --all'"""
)

NOTICE_REFRESH_CONTRACT_WARNING = t.gettext(
    """\
A change has been detected in your contract.
Please run `sudo pro refresh`."""
)


###############################################################################
#                        CLI HELP TEXT                                        #
###############################################################################
# This encompasses help text for subcommands, flags, and arguments for the CLI
# Also, any generic strings about the CLI itself go here.


CLI_HELP_EPILOG = t.gettext(
    "Use {name} {command} --help for more information about a command."
)

CLI_HELP_FLAG_DESC = t.gettext(
    "Displays help on {name} and command line options"
)

CLI_HELP_HEADER_QUICK_START = t.gettext("Quick start commands")
CLI_HELP_HEADER_SECURITY = t.gettext("Security-related commands")
CLI_HELP_HEADER_TROUBLESHOOT = t.gettext("Troubleshooting-related commands")
CLI_HELP_HEADER_OTHER = t.gettext("Other commands")


CLI_HELP_VARIANTS_HEADER = t.gettext("Variants:")
CLI_FLAGS = t.gettext("Flags")
CLI_AVAILABLE_COMMANDS = t.gettext("Available Commands")
CLI_FORMAT_DESC = t.gettext(
    "output in the specified format (default: {default})"
)
CLI_ASSUME_YES = t.gettext(
    "do not prompt for confirmation before performing the {command}"
)

CLI_API_DESC = t.gettext("Calls the Client API endpoints.")
CLI_API_ENDPOINT = t.gettext("API endpoint to call")
CLI_API_SHOW_PROGRESS = t.gettext(
    "For endpoints that support progress updates, show each progress update "
    "on a new line in JSON format"
)
CLI_API_ARGS = t.gettext(
    "Options to pass to the API endpoint, formatted as key=value"
)
CLI_API_DATA = t.gettext("arguments in JSON format to the API endpoint")

CLI_AUTO_ATTACH_DESC = t.gettext(
    "Automatically attach on an Ubuntu Pro cloud instance."
)

CLI_COLLECT_LOGS_DESC = t.gettext(
    "Collect logs and relevant system information into a tarball."
)
CLI_COLLECT_LOGS_OUTPUT = t.gettext(
    "tarball where the logs will be stored. (Defaults to " "./pro_logs.tar.gz)"
)

CLI_CONFIG_SHOW_DESC = t.gettext("Show customizable configuration settings")
CLI_CONFIG_SHOW_KEY = t.gettext(
    "Optional key or key(s) to show configuration settings."
)
CLI_CONFIG_SET_DESC = t.gettext(
    "Set and apply Ubuntu Pro configuration settings"
)
CLI_CONFIG_SET_KEY_VALUE = t.gettext(
    "key=value pair to configure for Ubuntu Pro services."
    " Key must be one of: {options}"
)
CLI_CONFIG_UNSET_DESC = t.gettext("Unset Ubuntu Pro configuration setting")
CLI_CONFIG_UNSET_KEY = t.gettext(
    "configuration key to unset from Ubuntu Pro services. One of: {options}"
)
CLI_CONFIG_DESC = t.gettext("Manage Ubuntu Pro configuration")

CLI_ATTACH_DESC = t.gettext(
    """\
Attach this machine to an Ubuntu Pro subscription with a token obtained from:
{url}

When running this command without a token, it will generate a short code
and prompt you to attach the machine to your Ubuntu Pro account using
a web browser."""
).format(url=urls.PRO_DASHBOARD)
CLI_ATTACH_TOKEN = t.gettext("token obtained for Ubuntu Pro authentication")
CLI_ATTACH_NO_AUTO_ENABLE = t.gettext(
    "do not enable any recommended services automatically"
)
CLI_ATTACH_ATTACH_CONFIG = t.gettext(
    "use the provided attach config file instead of passing the token on the "
    "cli"
)

CLI_FIX_DESC = t.gettext(
    "Inspect and resolve CVEs and USNs (Ubuntu Security Notices) on this"
    " machine."
)
CLI_FIX_ISSUE = t.gettext(
    "Security vulnerability ID to inspect and resolve on this system."
    " Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-dd"
)
CLI_FIX_DRY_RUN = t.gettext(
    "If used, fix will not actually run but will display"
    " everything that will happen on the machine during the"
    " command."
)
CLI_FIX_NO_RELATED = t.gettext(
    "If used, when fixing a USN, the command will not try to"
    " also fix related USNs to the target USN."
)

CLI_FIX_FAIL_UPDATING_ESM_CACHE = t.gettext(
    "WARNING: Failed to update ESM cache - package availability may be inaccurate"  # noqa
)

CLI_FIX_FAIL_UPDATING_ESM_CACHE_NON_ROOT = t.gettext(
    "{bold}WARNING: Unable to update ESM cache when running as non-root,\n"
    "please run sudo apt update and try again "
    "if packages cannot be found.{end_bold}"
).format(bold=TxtColor.BOLD, end_bold=TxtColor.ENDC)

CLI_SS_DESC = t.gettext(
    """\
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
)
CLI_SS_THIRDPARTY = t.gettext(
    "List and present information about third-party packages"
)
CLI_SS_UNAVAILABLE = t.gettext(
    "List and present information about unavailable packages"
)
CLI_SS_ESM_INFRA = t.gettext(
    "List and present information about esm-infra packages"
)
CLI_SS_ESM_APPS = t.gettext(
    "List and present information about esm-apps packages"
)

CLI_REFRESH_DESC = t.gettext(
    """\
Refresh three distinct Ubuntu Pro related artifacts in the system:

* contract: Update contract details from the server.
* config:   Reload the config file.
* messages: Update APT and MOTD messages related to UA.

You can individually target any of the three specific actions,
by passing the target name to the command.  If no `target`
is specified, all targets are refreshed.
"""
)
CLI_REFRESH_TARGET = t.gettext("Target to refresh.")

CLI_DETACH_DESC = t.gettext(
    "Detach this machine from an Ubuntu Pro subscription."
)

CLI_HELP_DESC = t.gettext(
    "Provide detailed information about Ubuntu Pro services."
)
CLI_HELP_SERVICE = t.gettext(
    "a service to view help output for. One of: {options}"
)
CLI_HELP_ALL = t.gettext("Include beta services")

CLI_ENABLE_DESC = t.gettext("Enable an Ubuntu Pro service.")
CLI_ENABLE_SERVICE = t.gettext(
    "the name(s) of the Ubuntu Pro services to enable." " One of: {options}"
)
CLI_ENABLE_ACCESS_ONLY = t.gettext(
    "do not auto-install packages. Valid for cc-eal, cis and "
    "realtime-kernel."
)
CLI_ENABLE_BETA = t.gettext("allow beta service to be enabled")
CLI_ENABLE_VARIANT = t.gettext(
    "The name of the variant to use when enabling the service"
)

CLI_DISABLE_DESC = t.gettext("Disable an Ubuntu Pro service.")
CLI_DISABLE_SERVICE = t.gettext(
    "the name(s) of the Ubuntu Pro services to disable." " One of: {options}"
)
CLI_PURGE = t.gettext(
    "disable the service and remove/downgrade related packages (experimental)"
)

CLI_SYSTEM_DESC = t.gettext(
    "Output system related information related to Pro services"
)
CLI_SYSTEM_REBOOT_REQUIRED = t.gettext("does the system need to be rebooted")
CLI_SYSTEM_REBOOT_REQUIRED_DESC = t.gettext(
    """\
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
)

CLI_STATUS_DESC = t.gettext(
    """\
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
  you to the service, but it isn't available for this machine) or - (if
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
)
CLI_STATUS_WAIT = t.gettext("Block waiting on pro to complete")
CLI_STATUS_SIMULATE_WITH_TOKEN = t.gettext(
    "simulate the output status using a provided token"
)
CLI_STATUS_ALL = t.gettext("Include unavailable and beta services")

CLI_ROOT_DEBUG = t.gettext("show all debug log messages to console")
CLI_ROOT_VERSION = t.gettext("show version of {name}")
CLI_ROOT_ATTACH = t.gettext(
    "attach this machine to an Ubuntu Pro subscription"
)
CLI_ROOT_API = t.gettext("Calls the Client API endpoints.")
CLI_ROOT_AUTO_ATTACH = t.gettext("automatically attach on supported platforms")
CLI_ROOT_COLLECT_LOGS = t.gettext("collect Pro logs and debug information")
CLI_ROOT_CONFIG = t.gettext("manage Ubuntu Pro configuration on this machine")
CLI_ROOT_DETACH = t.gettext(
    "remove this machine from an Ubuntu Pro subscription"
)
CLI_ROOT_DISABLE = t.gettext(
    "disable a specific Ubuntu Pro service on this machine"
)
CLI_ROOT_ENABLE = t.gettext(
    "enable a specific Ubuntu Pro service on this machine"
)
CLI_ROOT_FIX = t.gettext(
    "check for and mitigate the impact of a CVE/USN on this system"
)
CLI_ROOT_SECURITY_STATUS = t.gettext(
    "list available security updates for the system"
)
CLI_ROOT_HELP = t.gettext(
    "show detailed information about Ubuntu Pro services"
)
CLI_ROOT_REFRESH = t.gettext("refresh Ubuntu Pro services")
CLI_ROOT_STATUS = t.gettext("current status of all Ubuntu Pro services")
CLI_ROOT_SYSTEM = t.gettext("show system information related to Pro services")

WARNING_HUMAN_READABLE_OUTPUT = t.gettext(
    """\
WARNING: this output is intended to be human readable, and subject to change.
In scripts, prefer using machine readable data from the `pro api` command,
or use `pro {command} --format json`.
"""
)


###############################################################################
#                        SERVICE-SPECIFIC MESSAGES                            #
###############################################################################


ANBOX_TITLE = t.gettext("Anbox Cloud")
ANBOX_DESCRIPTION = t.gettext("Scalable Android in the cloud")
ANBOX_HELP_TEXT = t.gettext(
    """\
Anbox Cloud lets you stream mobile apps securely, at any scale, to any device,
letting you focus on your apps. Run Android in system containers on public or
private clouds with ultra low streaming latency. When the anbox-cloud service
is enabled, by default, the Appliance variant is enabled. Enabling this service
allows orchestration to provision a PPA with the Anbox Cloud resources. This
step also configures the Anbox Management Service (AMS) with the necessary
image server credentials. To learn more about Anbox Cloud, see
{url}"""
).format(url=urls.ANBOX_HOME_PAGE)
ANBOX_RUN_INIT_CMD = t.gettext(
    """\
To finish setting up the Anbox Cloud Appliance, run:

$ sudo anbox-cloud-appliance init

You can accept the default answers if you do not have any specific
configuration changes.
For more information, see {url}
"""
).format(url=urls.ANBOX_DOCS_APPLIANCE_INITIALIZE)

CC_TITLE = t.gettext("CC EAL2")
CC_DESCRIPTION = t.gettext("Common Criteria EAL2 Provisioning Packages")
CC_HELP_TEXT = t.gettext(
    """\
Common Criteria is an Information Technology Security Evaluation standard
(ISO/IEC IS 15408) for computer security certification. Ubuntu 16.04 has been
evaluated to assurance level EAL2 through CSEC. The evaluation was performed
on Intel x86_64, IBM Power8 and IBM Z hardware platforms."""
)
CC_PRE_INSTALL = t.gettext(
    "(This will download more than 500MB of packages, so may take"
    " some time.)"
)
CC_POST_ENABLE = t.gettext(
    "Please follow instructions in {filename} to configure EAL2"
)

CIS_TITLE = t.gettext("CIS Audit")
CIS_USG_TITLE = t.gettext("Ubuntu Security Guide")
CIS_DESCRIPTION = t.gettext("Security compliance and audit tools")
CIS_HELP_TEXT = t.gettext(
    """\
Ubuntu Security Guide is a tool for hardening and auditing and allows for
environment-specific customizations. It enables compliance with profiles such
as DISA-STIG and the CIS benchmarks. Find out more at
{url}"""
).format(url=urls.USG_DOCS)
CIS_POST_ENABLE = t.gettext("Visit {url} to learn how to use CIS").format(
    url=urls.CIS_HOME_PAGE
)
CIS_USG_POST_ENABLE = t.gettext("Visit {url} for the next steps").format(
    url=urls.USG_DOCS
)
CIS_IS_NOW_USG = t.gettext(
    """\
From Ubuntu 20.04 onward 'pro enable cis' has been
replaced by 'pro enable usg'. See more information at:
{url}"""
).format(url=urls.USG_DOCS)

ESM_APPS_TITLE = t.gettext("Ubuntu Pro: ESM Apps")
ESM_APPS_DESCRIPTION = t.gettext(
    "Expanded Security Maintenance for Applications"
)
ESM_APPS_HELP_TEXT = t.gettext(
    """\
Expanded Security Maintenance for Applications is enabled by default on
entitled workloads. It provides access to a private PPA which includes
available high and critical CVE fixes for Ubuntu LTS packages in the Ubuntu
Main and Ubuntu Universe repositories from the Ubuntu LTS release date until
its end of life. You can find out more about the esm service at
{url}"""
).format(url=urls.ESM_HOME_PAGE)

ESM_INFRA_TITLE = t.gettext("Ubuntu Pro: ESM Infra")
ESM_INFRA_DESCRIPTION = t.gettext(
    "Expanded Security Maintenance for Infrastructure"
)
ESM_INFRA_HELP_TEXT = t.gettext(
    """\
Expanded Security Maintenance for Infrastructure provides access to a private
PPA which includes available high and critical CVE fixes for Ubuntu LTS
packages in the Ubuntu Main repository between the end of the standard Ubuntu
LTS security maintenance and its end of life. It is enabled by default with
Ubuntu Pro. You can find out more about the service at
{url}"""
).format(url=urls.ESM_HOME_PAGE)

FIPS_TITLE = t.gettext("FIPS")
FIPS_DESCRIPTION = t.gettext("NIST-certified FIPS crypto packages")
FIPS_HELP_TEXT = t.gettext(
    """\
Installs FIPS 140 crypto packages for FedRAMP, FISMA and compliance use cases.
Note that "fips" does not provide security patching. For FIPS certified
modules with security patches please see "fips-updates". If you are unsure,
choose "fips-updates" for maximum security. Find out more at {url}"""
).format(url=urls.FIPS_HOME_PAGE)
FIPS_COULD_NOT_DETERMINE_CLOUD_DEFAULT_PACKAGE = t.gettext(
    "Could not determine cloud, defaulting to generic FIPS package."
)
NOTICE_FIPS_MANUAL_DISABLE_URL = t.gettext(
    """\
FIPS kernel is running in a disabled state.
  To manually remove fips kernel: {url}
"""
).format(url=urls.PRO_CLIENT_DOCS_REMOVE_FIPS)
NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD = t.gettext(
    """\
Warning: FIPS kernel is not optimized for your specific cloud.
To fix it, run the following commands:

    1. sudo pro disable fips
    2. sudo apt remove ubuntu-fips
    3. sudo pro enable fips --assume-yes
    4. sudo reboot
"""
)
PROMPT_FIPS_PRE_ENABLE = (
    t.gettext(
        """\
This will install the FIPS packages. The Livepatch service will be unavailable.
Warning: This action can take some time and cannot be undone.
"""
    )
    + PROMPT_YES_NO
)
PROMPT_FIPS_UPDATES_PRE_ENABLE = (
    t.gettext(
        """\
This will install the FIPS packages including security updates.
Warning: This action can take some time and cannot be undone.
"""
    )
    + PROMPT_YES_NO
)
PROMPT_FIPS_CONTAINER_PRE_ENABLE = (
    t.gettext(
        """\
Warning: Enabling {title} in a container.
         This will install the FIPS packages but not the kernel.
         This container must run on a host with {title} enabled to be
         compliant.
Warning: This action can take some time and cannot be undone.
"""
    )
    + PROMPT_YES_NO
)
PROMPT_FIPS_PRE_DISABLE = (
    t.gettext(
        """\
This will disable the {title} entitlement but the {title} packages will remain installed.
"""  # noqa: E501
    )
    + PROMPT_YES_NO
)
KERNEL_DOWNGRADE_WARNING = t.gettext(
    """\
This will downgrade the kernel from {current_version} to {new_version}.
Warning: Downgrading the kernel may cause hardware failures.  Please ensure the
         hardware is compatible with the new kernel version before proceeding.
"""
)
KERNEL_FLAVOR_CHANGE_WARNING_PROMPT = t.gettext(
    """\
The "{variant}" variant of {service} is based on the "{base_flavor}" Ubuntu
kernel but this machine is running the "{current_flavor}" kernel.
The "{current_flavor}" kernel may have significant hardware support
differences from "{variant}" {service}.

Warning: Installing {variant} {service} may result in lost hardware support
         and may prevent the system from booting.

Do you accept the risk and wish to continue? (y/N) """
)
FIPS_SYSTEM_REBOOT_REQUIRED = t.gettext(
    "FIPS support requires system reboot to complete configuration."
)
FIPS_REBOOT_REQUIRED_MSG = t.gettext("Reboot to FIPS kernel required")
FIPS_INSTALL_OUT_OF_DATE = t.gettext(
    "This FIPS install is out of date, run: sudo pro enable fips"
)
FIPS_DISABLE_REBOOT_REQUIRED = t.gettext(
    "Disabling FIPS requires system reboot to complete operation."
)
FIPS_PACKAGE_NOT_AVAILABLE = t.gettext(
    "{service} {pkg} package could not be installed"
)
FIPS_RUN_APT_UPGRADE = t.gettext(
    """\
Please run `apt upgrade` to ensure all FIPS packages are updated to the correct
version.
"""
)
FIPS_PACKAGES_UPGRADE_FAILURE = (
    t.gettext(
        "Failure occurred while upgrading packages to {service} versions."
    )
    + "\n"
    + FIPS_RUN_APT_UPGRADE
)

FIPS_UPDATES_TITLE = t.gettext("FIPS Updates")
FIPS_UPDATES_DESCRIPTION = t.gettext(
    "FIPS compliant crypto packages with stable security updates"
)
FIPS_UPDATES_HELP_TEXT = t.gettext(
    """\
fips-updates installs FIPS 140 crypto packages including all security patches
for those modules that have been provided since their certification date.
You can find out more at {url}"""
).format(url=urls.FIPS_HOME_PAGE)

FIPS_PREVIEW_TITLE = t.gettext("FIPS Preview")
FIPS_PREVIEW_DESCRIPTION = t.gettext(
    "Preview of FIPS crypto packages undergoing certification with NIST"  # noqa
)
FIPS_PREVIEW_HELP_TEXT = t.gettext(
    """\
Installs FIPS crypto packages that are under certification with NIST,
for FedRAMP, FISMA and compliance use cases."""
)
PROMPT_FIPS_PREVIEW_PRE_ENABLE = t.gettext(
    """\
This will install crypto packages that have been submitted to NIST for review
but do not have FIPS certification yet. Use this for early access to the FIPS
modules.
Please note that the Livepatch service will be unavailable after
this operation.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)

LANDSCAPE_TITLE = t.gettext("Landscape")
LANDSCAPE_DESCRIPTION = t.gettext(
    "Management and administration tool for Ubuntu"
)
LANDSCAPE_HELP_TEXT = t.gettext(
    """\
Landscape Client can be installed on this machine and enrolled in Canonical's
Landscape SaaS: {saas_url} or a self-hosted Landscape:
{install_url}
Landscape allows you to manage many machines as easily as one, with an
intuitive dashboard and API interface for automation, hardening, auditing, and
more. Find out more about Landscape at {home_url}"""
).format(
    saas_url=urls.LANDSCAPE_SAAS,
    install_url=urls.LANDSCAPE_DOCS_INSTALL,
    home_url=urls.LANDSCAPE_HOME_PAGE,
)
LANDSCAPE_CONFIG_REMAINS = t.gettext(
    """\
/etc/landscape/client.conf contains your landscape-client configuration.
To re-enable Landscape with the same configuration, run:
    sudo pro enable landscape --assume-yes
"""
)

LIVEPATCH_TITLE = t.gettext("Livepatch")
LIVEPATCH_DESCRIPTION = t.gettext("Canonical Livepatch service")
LIVEPATCH_HELP_TEXT = t.gettext(
    """\
Livepatch provides selected high and critical kernel CVE fixes and other
non-security bug fixes as kernel livepatches. Livepatches are applied without
rebooting a machine which drastically limits the need for unscheduled system
reboots. Due to the nature of fips compliance, livepatches cannot be enabled
on fips-enabled systems. You can find out more about Ubuntu Kernel Livepatch
service at {url}"""
).format(url=urls.LIVEPATCH_HOME_PAGE)
LIVEPATCH_KERNEL_NOT_SUPPORTED_DESCRIPTION = t.gettext(
    "Current kernel is not covered by livepatch"
)
LIVEPATCH_KERNEL_NOT_SUPPORTED_UNATTACHED = t.gettext(
    "Kernels covered by livepatch are listed here: {url}"
).format(url=urls.LIVEPATCH_SUPPORTED_KERNELS)
LIVEPATCH_UNABLE_TO_CONFIGURE = t.gettext(
    "Unable to configure livepatch: {error_msg}"
)
LIVEPATCH_UNABLE_TO_ENABLE = t.gettext("Unable to enable Livepatch: ")
LIVEPATCH_DISABLE_REATTACH = t.gettext(
    "Disabling Livepatch prior to re-attach with new token"
)
LIVEPATCH_LTS_REBOOT_REQUIRED = t.gettext(
    "Livepatch coverage requires a system reboot across LTS upgrade."
)
INSTALLING_LIVEPATCH = t.gettext("Installing Livepatch")
SETTING_UP_LIVEPATCH = t.gettext("Setting up Livepatch")

REALTIME_TITLE = t.gettext("Real-time kernel")
REALTIME_DESCRIPTION = t.gettext(
    "Ubuntu kernel with PREEMPT_RT patches integrated"
)
REALTIME_HELP_TEXT = t.gettext(
    """\
The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated. It
services latency-dependent use cases by providing deterministic response times.
The Real-time kernel meets stringent preemption specifications and is suitable
for telco applications and dedicated devices in industrial automation and
robotics. The Real-time kernel is currently incompatible with FIPS and
Livepatch."""
)
REALTIME_GENERIC_TITLE = t.gettext("Real-time kernel")
REALTIME_GENERIC_DESCRIPTION = t.gettext(
    "Generic version of the RT kernel (default)"
)
REALTIME_NVIDIA_TITLE = t.gettext("Real-time NVIDIA Tegra Kernel")
REALTIME_NVIDIA_DESCRIPTION = t.gettext(
    "RT kernel optimized for NVIDIA Tegra platform"
)
REALTIME_RASPI_TITLE = t.gettext("Raspberry Pi Real-time for Pi5/Pi4")
REALTIME_RASPI_DESCRIPTION = t.gettext(
    "24.04 Real-time kernel optimised for Raspberry Pi"
)
REALTIME_INTEL_TITLE = t.gettext("Real-time Intel IOTG Kernel")
REALTIME_INTEL_DESCRIPTION = t.gettext(
    "RT kernel optimized for Intel IOTG platform"
)
REALTIME_PROMPT = t.gettext(
    """\
The Real-time kernel is an Ubuntu kernel with PREEMPT_RT patches integrated.

{bold}\
This will change your kernel. To revert to your original kernel, you will need
to make the change manually.\
{end_bold}

Do you want to continue? [ default = Yes ]: (Y/n) """
).format(bold=TxtColor.BOLD, end_bold=TxtColor.ENDC)
REALTIME_PRE_DISABLE_PROMPT = t.gettext(
    """\
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
)

ROS_TITLE = t.gettext("ROS ESM Security Updates")
ROS_DESCRIPTION = t.gettext("Security Updates for the Robot Operating System")
ROS_HELP_TEXT = t.gettext(
    """\
ros provides access to a private PPA which includes security-related updates
for available high and critical CVE fixes for Robot Operating System (ROS)
packages. For access to ROS ESM and security updates, both esm-infra and
esm-apps services will also be enabled. To get additional non-security updates,
enable ros-updates. You can find out more about the ROS ESM service at
{url}"""
).format(url=urls.ROS_HOME_PAGE)

ROS_UPDATES_TITLE = t.gettext("ROS ESM All Updates")
ROS_UPDATES_DESCRIPTION = t.gettext(
    "All Updates for the Robot Operating System"
)
ROS_UPDATES_HELP_TEXT = t.gettext(
    """\
ros-updates provides access to a private PPA that includes non-security-related
updates for Robot Operating System (ROS) packages. For full access to ROS ESM,
security and non-security updates, the esm-infra, esm-apps, and ros services
will also be enabled. You can find out more about the ROS ESM service at
{url}"""
).format(url=urls.ROS_HOME_PAGE)


###############################################################################
#                              NAMED MESSAGES                                 #
###############################################################################
# These are mostly used in json output of cli commands for errors or warnings


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


class FormattedNamedMessage:
    def __init__(self, name: str, msg: str):
        self.name = name
        self.tmpl_msg = msg

    def format(self, **msg_params) -> NamedMessage:
        return NamedMessage(
            name=self.name, msg=self.tmpl_msg.format(**msg_params)
        )

    def __repr__(self):
        return "FormattedNamedMessage({}, {})".format(
            self.name.__repr__(),
            self.tmpl_msg.__repr__(),
        )


ANBOX_FAIL_TO_ENABLE_ON_CONTAINER = NamedMessage(
    "anbox-fail-to-enable-on-container",
    """\
It is only possible to enable Anbox Cloud on a container using
the --access-only flag.""",
)

ATTACH_FAILURE_RESTRICTED_RELEASE = FormattedNamedMessage(
    "attach-failure-restricted-release",
    t.gettext(
        "Attach failed. Attaching to this contract \
is only allowed on the Ubuntu {release} ({series_codename}) release."
    ),
)

UNEXPECTED_ERROR = FormattedNamedMessage(
    "unexpected-error",
    t.gettext(
        """\
An unexpected error occurred: {error_msg}
For more details, see the log: {log_path}
If you think this is a bug, please run: ubuntu-bug ubuntu-advantage-tools"""
    ),
)

SSL_VERIFICATION_ERROR_CA_CERTIFICATES = FormattedNamedMessage(
    "ssl-verification-error-ca-certificate",
    t.gettext(
        """\
Failed to access URL: {url}
Cannot verify certificate of server
Please install "ca-certificates" and try again."""
    ),
)

SSL_VERIFICATION_ERROR_OPENSSL_CONFIG = FormattedNamedMessage(
    "ssl-verification-error-openssl-config",
    t.gettext(
        """\
Failed to access URL: {url}
Cannot verify certificate of server
Please check your openssl configuration."""
    ),
)

API_UNKNOWN_ARG = FormattedNamedMessage(
    name="api-unknown-argument",
    msg=t.gettext("Ignoring unknown argument '{arg}'"),
)

WARN_NEW_VERSION_AVAILABLE = FormattedNamedMessage(
    name="new-version-available",
    msg=t.gettext(
        "A new version of the client is available: {version}. \
Please upgrade to the latest version to get the new features \
and bug fixes."
    ),
)
ENABLE_ACCESS_ONLY_NOT_SUPPORTED = FormattedNamedMessage(
    name="enable-access-only-not-supported",
    msg=t.gettext("{title} does not support being enabled with --access-only"),
)

DISABLE_PURGE_NOT_SUPPORTED = FormattedNamedMessage(
    name="disable-purge-not-supported",
    msg=t.gettext("{title} does not support being disabled with --purge"),
)

FAILED_DISABLING_DEPENDENT_SERVICE = FormattedNamedMessage(
    "failed-disabling-dependent-service",
    t.gettext(
        """\
Cannot disable dependent service: {required_service}{error}"""
    ),
)
REPO_PURGE_FAIL_NO_ORIGIN = FormattedNamedMessage(
    "repo-purge-fail-no-origin",
    t.gettext(
        "Cannot disable {entitlement_name} with purge: no origin value defined"
    )
    + "\n"
    + DISABLE_FAILED_TMPL,
)
ERROR_ENABLING_REQUIRED_SERVICE = FormattedNamedMessage(
    "error-enabling-required-service",
    t.gettext("Cannot enable required service: {service}{error}"),
)

SERVICE_ERROR_INSTALL_ON_CONTAINER = FormattedNamedMessage(
    "service-error-install-on-container",
    t.gettext("Cannot install {title} on a container."),
)
SERVICE_NOT_CONFIGURED = FormattedNamedMessage(
    "service-not-configured", t.gettext("{title} is not configured")
)
SERVICE_DISABLED_MISSING_PACKAGE = FormattedNamedMessage(
    "service-disabled-missing-package",
    t.gettext(
        """\
The {service} service is not enabled because the {package} package is
not installed."""
    ),
)
SERVICE_IS_ACTIVE = FormattedNamedMessage(
    "service-is-active", t.gettext("{title} is active")
)
NO_APT_URL_FOR_SERVICE = FormattedNamedMessage(
    "no-apt-url-for-service",
    t.gettext("{title} does not have an aptURL directive"),
)
NO_SUITES_FOR_SERVICE = FormattedNamedMessage(
    "no-suites-for-service",
    t.gettext("{title} does not have a suites directive"),
)
ALREADY_DISABLED = FormattedNamedMessage(
    "service-already-disabled",
    t.gettext(
        """\
{title} is not currently enabled - nothing to do.
See: sudo pro status"""
    ),
)
CANNOT_DISABLE_NOT_APPLICABLE = FormattedNamedMessage(
    "cannot-disable-not-applicable",
    t.gettext(
        """\
Disabling {title} with pro is not supported.\nSee: sudo pro status"""
    ),
)
ALREADY_ENABLED = FormattedNamedMessage(
    "service-already-enabled",
    t.gettext(
        """\
{title} is already enabled - nothing to do.
See: sudo pro status"""
    ),
)
UNENTITLED = FormattedNamedMessage(
    "subscription-not-entitled-to-service",
    t.gettext(
        """\
This subscription is not entitled to {{title}}
View your subscription at: {url}"""
    ).format(url=urls.PRO_DASHBOARD),
)
SERVICE_NOT_ENTITLED = FormattedNamedMessage(
    "service-not-entitled", t.gettext("{title} is not entitled")
)
AUTO_SELECTED_VARIANT_WARNING = FormattedNamedMessage(
    "auto-selected-variant", t.gettext("Auto-selected {variant_name} variant")
)

INAPPLICABLE_KERNEL_VER = FormattedNamedMessage(
    "inapplicable-kernel-version",
    t.gettext(
        """\
{title} is not available for kernel {kernel}.
Minimum kernel version required: {min_kernel}."""
    ),
)
INAPPLICABLE_KERNEL = FormattedNamedMessage(
    "inapplicable-kernel",
    t.gettext(
        """\
{title} is not available for kernel {kernel}.
Supported flavors are: {supported_kernels}."""
    ),
)
INAPPLICABLE_SERIES = FormattedNamedMessage(
    "inapplicable-series",
    t.gettext(
        """\
{title} is not available for Ubuntu {series}."""
    ),
)
INAPPLICABLE_ARCH = FormattedNamedMessage(
    "inapplicable-arch",
    t.gettext(
        """\
{title} is not available for platform {arch}.
Supported platforms are: {supported_arches}."""
    ),
)
INAPPLICABLE_VENDOR_NAME = FormattedNamedMessage(
    "inapplicable-vendor-name",
    t.gettext(
        """\
{title} is not available for CPU vendor {vendor}.
Supported CPU vendors are: {supported_vendors}."""
    ),
)
NO_ENTITLEMENT_AFFORDANCES_CHECKED = NamedMessage(
    "no-entitlement-affordances-checked",
    t.gettext("no entitlement affordances checked"),
)

FIPS_BLOCK_ON_CLOUD = FormattedNamedMessage(
    "cloud-non-optimized-fips-kernel",
    t.gettext(
        """\
Ubuntu {{series}} does not provide {{cloud}} optimized FIPS kernel
For help see: {url}"""
    ).format(url=urls.PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES),
)
FIPS_REBOOT_REQUIRED = NamedMessage(
    "fips-reboot-required", t.gettext("Reboot to FIPS kernel required")
)
FIPS_ERROR_WHEN_FIPS_UPDATES_ENABLED = FormattedNamedMessage(
    "fips-enable-when-fips-updates-enabled",
    t.gettext("Cannot enable {fips} when {fips_updates} is enabled."),
)
FIPS_PROC_FILE_ERROR = FormattedNamedMessage(
    "fips-proc-file-error", t.gettext("{file_name} is not set to 1")
)
FIPS_ERROR_WHEN_FIPS_UPDATES_ONCE_ENABLED = FormattedNamedMessage(
    "fips-enable-when-fips-updates-once-enabled",
    t.gettext("Cannot enable {fips} because {fips_updates} was once enabled."),
)
FIPS_UPDATES_INVALIDATES_FIPS = NamedMessage(
    "fips-updates-invalidates-fips",
    t.gettext(
        "FIPS cannot be enabled if FIPS Updates has ever been enabled because"
        " FIPS Updates installs security patches that aren't officially"
        " certified."
    ),
)
FIPS_INVALIDATES_FIPS_UPDATES = NamedMessage(
    "fips-invalidates-fips-updates",
    t.gettext(
        "FIPS Updates cannot be enabled if FIPS is enabled."
        " FIPS Updates installs security patches that aren't officially"
        " certified."
    ),
)

LIVEPATCH_INVALIDATES_FIPS = NamedMessage(
    "livepatch-invalidates-fips",
    t.gettext(
        "Livepatch cannot be enabled while running the official FIPS"
        " certified kernel. If you would like a FIPS compliant kernel"
        " with additional bug fixes and security updates, you can use"
        " the FIPS Updates service with Livepatch."
    ),
)
LIVEPATCH_NOT_ENABLED = NamedMessage(
    "livepatch-not-enabled",
    t.gettext("canonical-livepatch snap is not installed."),
)
LIVEPATCH_ERROR_WHEN_FIPS_ENABLED = NamedMessage(
    "livepatch-error-when-fips-enabled",
    t.gettext("Cannot enable Livepatch when FIPS is enabled."),
)
LIVEPATCH_KERNEL_UPGRADE_REQUIRED = NamedMessage(
    name="livepatch-kernel-upgrade-required",
    msg=t.gettext(
        """\
The running kernel has reached the end of its active livepatch window.
Please upgrade the kernel with apt and reboot for continued livepatch coverage."""  # noqa: E501
    ),
)
LIVEPATCH_KERNEL_EOL = FormattedNamedMessage(
    name="livepatch-kernel-eol",
    msg=t.gettext(
        """\
The current kernel ({{version}}, {{arch}}) has reached the end of its livepatch coverage.
Covered kernels are listed here: {url}
Either switch to a covered kernel or `sudo pro disable livepatch` to dismiss this warning."""  # noqa: E501
    ).format(url=urls.LIVEPATCH_SUPPORTED_KERNELS),
)
LIVEPATCH_KERNEL_NOT_SUPPORTED = FormattedNamedMessage(
    name="livepatch-kernel-not-supported",
    msg=t.gettext(
        """\
The current kernel ({{version}}, {{arch}}) is not covered by livepatch.
Covered kernels are listed here: {url}
Either switch to a covered kernel or `sudo pro disable livepatch` to dismiss this warning."""  # noqa: E501
    ).format(
        url=urls.LIVEPATCH_SUPPORTED_KERNELS
    ),  # noqa: E501
)
LIVEPATCH_APPLICATION_STATUS_CLIENT_FAILURE = NamedMessage(
    "livepatch-client-failure",
    t.gettext("canonical-livepatch status didn't finish successfully"),
)

LIVEPATCH_CLIENT_FAILURE_WARNING = FormattedNamedMessage(
    "livepatch-client-failure-warning",
    t.gettext(
        """\
Error running canonical-livepatch status:
{livepatch_error}"""
    ),
)

REALTIME_FIPS_INCOMPATIBLE = NamedMessage(
    "realtime-fips-incompatible",
    t.gettext(
        "Realtime and FIPS require different kernels, so you cannot enable"
        " both at the same time."
    ),
)
REALTIME_FIPS_UPDATES_INCOMPATIBLE = NamedMessage(
    "realtime-fips-updates-incompatible",
    t.gettext(
        "Realtime and FIPS Updates require different kernels, so you cannot"
        " enable both at the same time."
    ),
)
REALTIME_LIVEPATCH_INCOMPATIBLE = NamedMessage(
    "realtime-livepatch-incompatible",
    t.gettext("Livepatch does not currently cover the Real-time kernel."),
)
REALTIME_VARIANT_INCOMPATIBLE = FormattedNamedMessage(
    "realtime-variant-incompatible",
    t.gettext("{service} cannot be enabled together with {variant}"),
)
REALTIME_ERROR_INSTALL_ON_CONTAINER = NamedMessage(
    "realtime-error-install-on-container",
    t.gettext("Cannot install Real-time kernel on a container."),
)

ROS_REQUIRES_ESM = NamedMessage(
    "ros-requires-esm",
    t.gettext("ROS packages assume ESM updates are enabled."),
)
ROS_UPDATES_REQUIRES_ROS = NamedMessage(
    "ros-updates-requires-ros",
    t.gettext(
        "ROS bug-fix updates assume ROS security fix updates are enabled."
    ),
)

UNATTENDED_UPGRADES_SYSTEMD_JOB_DISABLED = NamedMessage(
    "unattended-upgrades-systemd-job-disabled",
    t.gettext("apt-daily.timer jobs are not running"),
)
UNATTENDED_UPGRADES_CFG_LIST_VALUE_EMPTY = FormattedNamedMessage(
    "unattended-upgrades-cfg-list-value-empty",
    t.gettext("{cfg_name} is empty"),
)
UNATTENDED_UPGRADES_CFG_VALUE_TURNED_OFF = FormattedNamedMessage(
    "unattended-upgrades-cfg-value-turned-off",
    t.gettext("{cfg_name} is turned off"),
)
UNATTENDED_UPGRADES_UNINSTALLED = NamedMessage(
    "unattended-upgrades-uninstalled",
    t.gettext("unattended-upgrades package is not installed"),
)

LANDSCAPE_NOT_REGISTERED = NamedMessage(
    "landscape-not-registered",
    t.gettext(
        """\
Landscape is installed and configured but not registered.
Run `sudo landscape-config` to register, or run `sudo pro disable landscape`\
"""
    ),
)
LANDSCAPE_SERVICE_NOT_ACTIVE = NamedMessage(
    "landscape-service-not-active",
    t.gettext(
        "landscape-client is either not installed or installed but disabled."
    ),
)

INVALID_SECURITY_ISSUE = FormattedNamedMessage(
    "invalid-security-issue",
    t.gettext(
        """\
Error: issue "{issue_id}" is not recognized.\n
CVEs should follow the pattern CVE-yyyy-nnn.\n
USNs should follow the pattern USN-nnnn."""
    ),
)


GENERIC_UNKNOWN_ISSUE = NamedMessage(
    "unknown-issue",
    UNKNOWN_ERROR,
)

###############################################################################
#                              ERROR MESSAGES                                 #
###############################################################################


E_APT_PROCESS_CONFLICT = NamedMessage(
    "apt-process-conflict", t.gettext("Another process is running APT.")
)

E_APT_UPDATE_INVALID_URL_CONFIG = FormattedNamedMessage(
    "apt-update-invalid-url-config",
    t.gettext(
        """\
APT update failed to read APT config for the following:
{failed_repos}"""
    ),
)

E_APT_UPDATE_PROCESS_CONFLICT = NamedMessage(
    "apt-update-failed-process-conflict",
    APT_UPDATE_FAILED + " " + E_APT_PROCESS_CONFLICT.msg,
)

E_APT_UPDATE_INVALID_REPO = FormattedNamedMessage(
    "apt-update-invalid-repo", APT_UPDATE_FAILED + "\n{repo_msg}"
)

E_APT_UPDATE_FAILED = FormattedNamedMessage(
    "apt-update-failed", APT_UPDATE_FAILED + "\n{detail}"
)

E_APT_INSTALL_PROCESS_CONFLICT = NamedMessage(
    "apt-install-failed-process-conflict",
    APT_INSTALL_FAILED + " " + E_APT_PROCESS_CONFLICT.msg,
)

E_APT_INSTALL_INVALID_REPO = FormattedNamedMessage(
    "apt-install-invalid-repo", APT_INSTALL_FAILED + " {repo_msg}"
)

E_APT_INVALID_CREDENTIALS = FormattedNamedMessage(
    "apt-invalid-credentials",
    t.gettext("Invalid APT credentials provided for {repo}"),
)

E_APT_TIMEOUT = FormattedNamedMessage(
    "apt-timeout",
    t.gettext("Timeout trying to access APT repository at {repo}"),
)

E_APT_UNEXPECTED_ERROR = FormattedNamedMessage(
    "apt-unexpected-error",
    t.gettext(
        """\
Unexpected APT error.
{detail}
See /var/log/ubuntu-advantage.log"""
    ),
)

E_APT_COMMAND_TIMEOUT = FormattedNamedMessage(
    "apt-command-timeout",
    t.gettext(
        "Cannot validate credentials for APT repo."
        " Timeout after {seconds} seconds trying to reach {repo}."
    ),
)

E_SNAP_NOT_INSTALLED_ERROR = FormattedNamedMessage(
    "snap-not-installed-error",
    t.gettext("snap {snap} is not installed or doesn't exist"),
)

E_UNEXPECTED_SNAPD_API_ERROR = FormattedNamedMessage(
    "unexpected-snapd-api-error",
    t.gettext("Unexpected SNAPD API error\n{error}"),
)

E_SNAPD_CONNECTION_REFUSED = NamedMessage(
    "snapd-connection-refused", t.gettext("Could not reach the SNAPD API")
)

E_CANNOT_INSTALL_SNAPD = NamedMessage(
    "cannot-install-snapd", t.gettext("Failed to install snapd on the system")
)

E_ERROR_INSTALLING_LIVEPATCH = FormattedNamedMessage(
    "error-installing-livepatch",
    t.gettext("Unable to install Livepatch client: {error_msg}"),
)

E_NOT_SETTING_PROXY_NOT_WORKING = FormattedNamedMessage(
    "proxy-not-working",
    t.gettext('"{proxy}" is not working. Not setting as proxy.'),
)

E_NOT_SETTING_PROXY_INVALID_URL = FormattedNamedMessage(
    "proxy-invalid-url",
    t.gettext('"{proxy}" is not a valid url. Not setting as proxy.'),
)

E_PYCURL_REQUIRED = NamedMessage(
    "pycurl-required",
    t.gettext(
        "To use an HTTPS proxy for HTTPS connections, please install "
        "pycurl with `apt install python3-pycurl`"
    ),
)

E_PYCURL_ERROR = FormattedNamedMessage(
    "pycurl-error", t.gettext("PycURL Error: {e}")
)

E_PROXY_AUTH_FAIL = NamedMessage(
    "proxy-auth-fail", t.gettext("Proxy authentication failed")
)

E_CONNECTIVITY_ERROR = FormattedNamedMessage(
    "connectivity-error",
    t.gettext(
        """\
Failed to connect to {url}
{cause_error}
"""
    ),
)

E_EXTERNAL_API_ERROR = FormattedNamedMessage(
    "external-api-error", t.gettext("Error connecting to {url}: {code} {body}")
)

E_INVALID_SERVICE_OP_FAILURE = FormattedNamedMessage(
    "invalid-service-or-failure",
    t.gettext(
        """\
Cannot {operation} unknown service '{invalid_service}'.
{service_msg}"""
    ),
)

E_ALREADY_ATTACHED = FormattedNamedMessage(
    name="already-attached",
    msg=t.gettext(
        "This machine is already attached to '{account_name}'\n"
        "To use a different subscription first run: sudo pro detach."
    ),
)

E_ATTACH_FAILURE = NamedMessage(
    "attach-failure",
    t.gettext("Failed to attach machine. See {url}").format(
        url=urls.PRO_DASHBOARD
    ),
)

E_ATTACH_CONFIG_READ_ERROR = FormattedNamedMessage(
    "attach-config-read-error",
    t.gettext("Error while reading {config_name}:\n{error}"),
)

E_ATTACH_INVALID_TOKEN = NamedMessage(
    "attach-invalid-token",
    t.gettext("Invalid token. See {url}").format(url=urls.PRO_DASHBOARD),
)

E_ATTACH_FORBIDDEN_EXPIRED = FormattedNamedMessage(
    "attach-forbidden-expired",
    t.gettext(
        """\
Attach denied:
Contract "{{contract_id}}" expired on {{date}}
Visit {url} to manage contract tokens."""
    ).format(url=urls.PRO_DASHBOARD),
)

E_ATTACH_FORBIDDEN_NOT_YET = FormattedNamedMessage(
    "attach-forbidden-not-yet",
    t.gettext(
        """\
Attach denied:
Contract "{{contract_id}}" is not effective until {{date}}
Visit {url} to manage contract tokens."""
    ).format(url=urls.PRO_DASHBOARD),
)

E_ATTACH_FORBIDDEN_NEVER = FormattedNamedMessage(
    "attach-forbidden-never",
    t.gettext(
        """\
Attach denied:
Contract "{{contract_id}}" has never been effective
Visit {url} to manage contract tokens."""
    ).format(url=urls.PRO_DASHBOARD),
)

E_ATTACH_EXPIRED_TOKEN = NamedMessage(
    "attach-experied-token",
    t.gettext(
        """\
Expired token or contract. To obtain a new token visit: {url}"""
    ).format(url=urls.PRO_DASHBOARD),
)

E_MAGIC_ATTACH_TOKEN_ALREADY_ACTIVATED = NamedMessage(
    "magic-attach-token-already-activated",
    t.gettext("The magic attach token is already activated."),
)

E_MAGIC_ATTACH_TOKEN_ERROR = NamedMessage(
    "magic-attach-token-error",
    t.gettext(
        "The magic attach token is invalid, has expired or never existed"
    ),
)

E_MAGIC_ATTACH_UNAVAILABLE = NamedMessage(
    "magic-attach-service-unavailable",
    t.gettext("Service unavailable, please try again later."),
)

E_MAGIC_ATTACH_INVALID_PARAM = FormattedNamedMessage(
    "magic-attach-invalid-param",
    t.gettext("This attach flow does not support {param} with value: {value}"),
)

E_MISSING_APT_URL_DIRECTIVE = FormattedNamedMessage(
    "missing-apt-url-directive",
    t.gettext(
        """\
Ubuntu Pro server provided no aptURL directive for {entitlement_name}"""
    ),
)

E_UNATTACHED = NamedMessage(
    "unattached",
    t.gettext(
        """\
This machine is not attached to an Ubuntu Pro subscription.
See {url}"""
    ).format(url=urls.PRO_HOME_PAGE),
)

E_VALID_SERVICE_FAILURE_UNATTACHED = FormattedNamedMessage(
    "valid-service-failure-unattached",
    t.gettext(
        """\
Cannot {{operation}} services when unattached - nothing to do.
To use '{{valid_service}}' you need an Ubuntu Pro subscription.
Personal and community subscriptions are available at no charge.
See {url}"""
    ).format(url=urls.PRO_HOME_PAGE),
)

E_MIXED_SERVICES_FAILURE_UNATTACHED = FormattedNamedMessage(
    "mixed-services-failure-unattached",
    E_INVALID_SERVICE_OP_FAILURE.tmpl_msg
    + "\n"
    + E_VALID_SERVICE_FAILURE_UNATTACHED.tmpl_msg,
)

E_ENTITLEMENT_NOT_FOUND = FormattedNamedMessage(
    "entitlement-not-found",
    t.gettext('could not find entitlement named "{entitlement_name}"'),
)

E_ENTITLEMENTS_NOT_ENABLED_ERROR = NamedMessage(
    "entitlements-not-enabled",
    t.gettext("failed to enable some services"),
)

E_ENTITLEMENT_NOT_ENABLED_ERROR = FormattedNamedMessage(
    "entitlement-not-enabled",
    t.gettext("failed to enable {service}"),
)

E_ENTITLEMENT_NOT_DISABLED_ERROR = FormattedNamedMessage(
    "entitlement-not-disabled",
    t.gettext("failed to disable {service}"),
)

E_ATTACH_FAILURE_DEFAULT_SERVICES = NamedMessage(
    "attach-failure-default-service",
    t.gettext(
        """\
Failed to enable default services, check: sudo pro status"""
    ),
)

E_ATTACH_FAILURE_UNEXPECTED = NamedMessage(
    "attach-failure-unexpected-error",
    t.gettext(
        """\
Something went wrong during the attach process. Check the logs."""
    ),
)

E_REPO_NO_APT_KEY = FormattedNamedMessage(
    "repo-no-apt-key",
    t.gettext(
        "Ubuntu Pro server provided no aptKey directive for {entitlement_name}"
    ),
)

E_REPO_NO_SUITES = FormattedNamedMessage(
    "repo-no-suites",
    t.gettext(
        "Ubuntu Pro server provided no suites directive for {entitlement_name}"
    ),
)

E_REPO_PIN_FAIL_NO_ORIGIN = FormattedNamedMessage(
    "repo-pin-fail-no-origin",
    t.gettext(
        "Cannot setup apt pin. Empty apt repo origin value for "
        "{entitlement_name}"
    )
    + "\n"
    + ENABLE_FAILED,
)

E_INVALID_CONTRACT_DELTAS_SERVICE_TYPE = FormattedNamedMessage(
    "invalid-contract-deltas-service-type",
    t.gettext("Could not determine contract delta service type {orig} {new}"),
)

E_REQUIRED_SERVICE_STOPS_ENABLE = FormattedNamedMessage(
    "required-service-stops-enable",
    t.gettext(
        """\
Cannot enable {service_being_enabled} when {required_service} is disabled.
"""
    ),
)
E_INCOMPATIBLE_SERVICE_STOPS_ENABLE = FormattedNamedMessage(
    "incompatible-service-stops-enable",
    t.gettext(
        """\
Cannot enable {service_being_enabled} when \
{incompatible_service} is enabled."""
    ),
)
E_DEPENDENT_SERVICE_STOPS_DISABLE = FormattedNamedMessage(
    "depedent-service-stops-disable",
    t.gettext(
        """\
Cannot disable {service_being_disabled} when {dependent_service} is enabled.
"""
    ),
)

E_INVALID_PRO_IMAGE = FormattedNamedMessage(
    name="invalid-pro-image",
    msg=t.gettext(
        """\
Failed to identify this image as a valid Ubuntu Pro image.
Details:
{error_msg}"""
    ),
)

E_CLOUD_METADATA_ERROR = FormattedNamedMessage(
    "cloud-metadata-error",
    t.gettext(
        "An error occurred while talking the the cloud metadata service: {code} - {body}"  # noqa: E501
    ),
)

E_GCP_SERVICE_ACCT_NOT_ENABLED_ERROR = FormattedNamedMessage(
    "gcp-pro-service-account-not-enabled",
    t.gettext(
        """\
Failed to attach machine
{{status_code}}: {{error_msg}}
For more information, see {url}"""
    ).format(url=urls.GCP_SERVICE_ACCOUNT_DOCS),
)

E_AWS_NO_VALID_IMDS = FormattedNamedMessage(
    "aws-no-valid-imds",
    t.gettext(
        "No valid AWS IMDS endpoint discovered at addresses: {addresses}"
    ),
)

E_UNABLE_TO_DETERMINE_CLOUD_TYPE = NamedMessage(
    "auto-attach-cloud-type-error",
    t.gettext(
        """\
Unable to determine cloud platform."""
    ),
)

E_UNSUPPORTED_AUTO_ATTACH = NamedMessage(
    "auto-attach-image-not-viable",
    t.gettext(
        """\
Auto-attach image support is not available on this image
See: {url}"""
    ).format(url=urls.PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES),
)

E_UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE = FormattedNamedMessage(
    "auto-attach-unsupported-cloud-type-error",
    t.gettext(
        """\
Auto-attach image support is not available on {{cloud_type}}
See: {url}"""
    ).format(url=urls.PRO_CLIENT_DOCS_CLOUD_PRO_IMAGES),
)

E_INVALID_FILE_FORMAT = FormattedNamedMessage(
    name="invalid-file-format",
    msg=t.gettext("{file_name} is not valid {file_format}"),
)

E_INVALID_FILE_ENCODING = FormattedNamedMessage(
    name="invalid-file-encoding",
    msg=t.gettext("{file_name} is not encoded as {file_encoding}"),
)

E_ERROR_PARSING_VERSION_OS_RELEASE = FormattedNamedMessage(
    "error-parsing-version-os-release",
    t.gettext(
        """\
Could not parse /etc/os-release VERSION: {orig_ver} (modified to {mod_ver})"""
    ),
)

E_MISSING_SERIES_ON_OS_RELEASE = FormattedNamedMessage(
    "missing-series-on-os-release",
    t.gettext(
        """\
Could not extract series information from /etc/os-release.
The VERSION filed does not have version information: {version}
and the VERSION_CODENAME information is not present"""
    ),
)

E_INVALID_LOCK_FILE = FormattedNamedMessage(
    "invalid-lock-file",
    t.gettext(
        """\
There is a corrupted lock file in the system. To continue, please remove it
from the system by running:

$ sudo rm {lock_file_path}"""
    ),
)

E_JSON_PARSER_ERROR = FormattedNamedMessage(
    "json-parser-error", t.gettext("{source} returned invalid json: {out}")
)

E_INVALID_BOOLEAN_CONFIG_VALUE = FormattedNamedMessage(
    "invalid-boolean-config-value",
    t.gettext(
        """\
Invalid value for {path_to_value} in /etc/ubuntu-advantage/uaclient.conf. \
Expected {expected_value}, found {value}."""
    ),
)

E_CLI_CONFIG_VALUE_MUST_BE_POS_INT = FormattedNamedMessage(
    "invalid-posint-config-value",
    t.gettext(
        "Cannot set {key} to {value}: "
        "<value> for interval must be a positive integer."
    ),
)

E_CONFIG_INVALID_URL = FormattedNamedMessage(
    "invalid-url-config-value",
    t.gettext("Invalid url in config. {key}: {value}"),
)

E_CONFIG_NO_YAML_FILE = FormattedNamedMessage(
    "invalid-feature-yaml-config-value",
    t.gettext("Could not find yaml file: {filepath}"),
)

E_INVALID_PROXY_COMBINATION = NamedMessage(
    "invalid-proxy-combination-config",
    t.gettext(
        """\
Error: Setting global apt proxy and pro scoped apt proxy
at the same time is unsupported.
Cancelling config process operation.
"""
    ),
)

E_MISSING_DISTRO_INFO_FILE = NamedMessage(
    "missing-distro-info-file",
    t.gettext("Can't load the distro-info database."),
)

E_MISSING_SERIES_IN_DISTRO_INFO_FILE = FormattedNamedMessage(
    "missing-series-in-distro-info-file",
    t.gettext("Can't find series {series} in the distro-info database."),
)

E_INVALID_OPTION_COMBINATION = FormattedNamedMessage(
    "invalid-option-combination",
    t.gettext("Error: Cannot use {option1} together with {option2}."),
)

E_CLI_NO_HELP = FormattedNamedMessage(
    "no-help-content", t.gettext("No help available for '{name}'")
)

E_SECURITY_FIX_CLI_ISSUE_REGEX_FAIL = FormattedNamedMessage(
    "invalid-security-issue-id-format",
    t.gettext(
        'Error: issue "{issue}" is not recognized.\n'
        'Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"'
    ),
)

E_CLI_VALID_CHOICES = FormattedNamedMessage(
    "invalid-arg-choice", "\n" + t.gettext("{arg} must be one of: {choices}")
)

E_CLI_EMPTY_CONFIG_VALUE = FormattedNamedMessage(
    "empty-value",
    t.gettext("Empty value provided for {arg}."),
)

E_CLI_EXPECTED_FORMAT = FormattedNamedMessage(
    "generic-invalid-format",
    "\n" + t.gettext("Expected {expected} but found: {actual}"),
)

E_REFRESH_CONFIG_FAILURE = NamedMessage(
    "refresh-config-failure", t.gettext("Unable to process uaclient.conf")
)

E_REFRESH_CONTRACT_FAILURE = NamedMessage(
    "refresh-contract-failure",
    t.gettext("Unable to refresh your subscription"),
)

E_REFRESH_MESSAGES_FAILURE = NamedMessage(
    "refresh-messages-failure",
    t.gettext("Unable to update Ubuntu Pro related APT and MOTD messages."),
)

E_JSON_FORMAT_REQUIRE_ASSUME_YES = NamedMessage(
    "json-format-require-assume-yes",
    t.gettext(
        """\
json formatted response requires --assume-yes flag."""
    ),
)

E_ATTACH_TOKEN_ARG_XOR_CONFIG = NamedMessage(
    "attach-token-xor-config",
    t.gettext(
        """\
Do not pass the TOKEN arg if you are using --attach-config.
Include the token in the attach-config file instead.
    """
    ),
)

E_API_ERROR_ARGS_AND_DATA_TOGETHER = NamedMessage(
    "api-error-args-and-data-together",
    t.gettext("Cannot provide both --args and --data at the same time"),
)

E_PROMPT_DENIED = NamedMessage(
    "prompt-denied",
    t.gettext("Operation cancelled by user"),
)

E_LOCK_HELD_ERROR = FormattedNamedMessage(
    "lock-held-error",
    t.gettext(
        """\
Unable to perform: {lock_request}.
"""
    )
    + LOCK_HELD,
)

E_NONROOT_USER = NamedMessage(
    "nonroot-user",
    t.gettext("This command must be run as root (try using sudo)."),
)

E_SECURITY_API_INVALID_METADATA = FormattedNamedMessage(
    "security-api-invalid-metadata",
    t.gettext("Metadata for {issue} is invalid. Error: {error_msg}.")
    + "\n"
    + SECURITY_ISSUE_NOT_RESOLVED,
)

E_SECURITY_FIX_NOT_FOUND_ISSUE = FormattedNamedMessage(
    "security-fix-not-found-issue",
    t.gettext("Error: {issue_id} not found."),
)

E_GPG_KEY_NOT_FOUND = FormattedNamedMessage(
    "gpg-key-not-found", t.gettext("GPG key '{keyfile}' not found.")
)

E_API_INVALID_ENDPOINT = FormattedNamedMessage(
    name="api-invalid-endpoint",
    msg=t.gettext("'{endpoint}' is not a valid endpoint"),
)

E_API_MISSING_ARG = FormattedNamedMessage(
    name="api-missing-argument",
    msg=t.gettext("Missing argument '{arg}' for endpoint {endpoint}"),
)

E_API_NO_ARG_FOR_ENDPOINT = FormattedNamedMessage(
    name="api-no-argument-for-endpoint",
    msg=t.gettext("{endpoint} accepts no arguments"),
)

E_API_JSON_DATA_FORMAT_ERROR = FormattedNamedMessage(
    "api-json-data-format-error",
    t.gettext("Error parsing API json data parameter:\n{data}"),
)

E_API_BAD_ARGS_FORMAT = FormattedNamedMessage(
    name="api-args-wrong-format",
    msg=t.gettext("'{arg}' is not formatted as 'key=value'"),
)

E_API_VERSION_ERROR = FormattedNamedMessage(
    "unable-to-determine-version",
    t.gettext("Unable to determine version: {error_msg}"),
)

E_AUTO_ATTACH_DISABLED_ERROR = NamedMessage(
    "auto-attach-disabled",
    t.gettext("features.disable_auto_attach set in config"),
)

E_UNATTENDED_UPGRADES_ERROR = FormattedNamedMessage(
    "unable-to-determine-unattended-upgrade-status",
    t.gettext("Unable to determine unattended-upgrades status: {error_msg}"),
)

E_INCORRECT_TYPE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-type",
    t.gettext(
        "Expected value with type {expected_type} but got type: {got_type}"
    ),
)

E_INCORRECT_LIST_ELEMENT_TYPE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-list-element-type",
    t.gettext("Got value with incorrect type at index {index}:\n{nested_msg}"),
)

E_INCORRECT_FIELD_TYPE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-field-type",
    t.gettext(
        'Got value with incorrect type for field "{key}":\n{nested_msg}'
    ),
)

E_INCORRECT_ENUM_VALUE_ERROR_MESSAGE = FormattedNamedMessage(
    "incorrect-enum-value",
    t.gettext(
        "Value provided was not found in {enum_class}'s allowed: "
        "value: {values}"
    ),
)

E_PYCURL_CA_CERTIFICATES = NamedMessage(
    "pycurl-ca-certificates-error", "Problem reading SSL CA certificates"
)

E_UPDATING_ESM_CACHE = FormattedNamedMessage(
    "error-updating-esm-cache",
    t.gettext("Error updating ESM services cache: {error}"),
)

E_ENTITLEMENTS_APT_DIRECTIVES_ARE_NOT_UNIQUE = FormattedNamedMessage(
    "entitlements-apt-directives-are-not-unique",
    t.gettext(
        "There is a problem with the resource directives provided by {url}\n"
        "These entitlements: {names} are sharing the following directives\n"
        " - APT url: {apt_url}\n - Suite: {suite}\n"
        "These directives need to be unique for every entitlement."
    ),
)

E_LANDSCAPE_CONFIG_FAILED = NamedMessage(
    "landscape-config-failed",
    t.gettext("landscape-config command failed"),
)

E_NON_INTERACTIVE_KERNEL_PURGE_DISALLOWED = NamedMessage(
    "non-interactive-kernel-purge-disallowed",
    t.gettext(
        "You must use the pro command to purge a service that has installed a "
        "kernel"
    ),
)

E_NOT_SUPPORTED = NamedMessage(
    "not-supported",
    t.gettext("The operation is not supported"),
)

E_CONTRACT_EXPIRED = NamedMessage(
    "contract-expired",
    CONTRACT_EXPIRED,
)

E_INVALID_URL = FormattedNamedMessage(
    "invalid-url",
    t.gettext("Invalid URL: {url}"),
)
