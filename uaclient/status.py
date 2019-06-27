import enum
import sys

try:
    from typing import Any, Dict  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class TxtColor:
    OKGREEN = '\033[92m'
    DISABLEGREY = '\033[37m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


@enum.unique
class ApplicationStatus(enum.Enum):
    """
    An enum to represent the current application status of an entitlement
    """
    ENABLED = object()
    DISABLED = object()
    PENDING = object()


@enum.unique
class ContractStatus(enum.Enum):
    """
    An enum to represent whether a user is entitled to an entitlement

    (The value of each member is the string that will be used in status
    output.)
    """
    ENTITLED = 'entitled'
    UNENTITLED = 'none'


@enum.unique
class ApplicabilityStatus(enum.Enum):
    """
    An enum to represent whether an entitlement could apply to this machine
    """
    APPLICABLE = object()
    INAPPLICABLE = object()


@enum.unique
class UserFacingStatus(enum.Enum):
    """
    An enum representing the states we will display in status output.

    This enum should only be used in display code, it should not be used in
    business logic.
    """
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    INAPPLICABLE = 'n/a'
    PENDING = 'pending'


ESSENTIAL = 'essential'
STANDARD = 'standard'
ADVANCED = 'advanced'

# Colorized status output for terminal
STATUS_COLOR = {
    UserFacingStatus.ACTIVE.value: (
        TxtColor.OKGREEN + UserFacingStatus.ACTIVE.value + TxtColor.ENDC),
    UserFacingStatus.PENDING.value: (
        TxtColor.DISABLEGREY + UserFacingStatus.PENDING.value + TxtColor.ENDC),
    UserFacingStatus.INACTIVE.value: (
        TxtColor.FAIL + UserFacingStatus.INACTIVE.value + TxtColor.ENDC),
    UserFacingStatus.INAPPLICABLE.value: (
        TxtColor.DISABLEGREY + UserFacingStatus.INAPPLICABLE.value + TxtColor.ENDC),  # noqa: E501
    ContractStatus.ENTITLED.value: (
        TxtColor.OKGREEN + ContractStatus.ENTITLED.value + TxtColor.ENDC),
    ContractStatus.UNENTITLED.value: (
        TxtColor.DISABLEGREY + ContractStatus.UNENTITLED.value + TxtColor.ENDC),  # noqa: E501
    ESSENTIAL: TxtColor.OKGREEN + ESSENTIAL + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN + STANDARD + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN + ADVANCED + TxtColor.ENDC
}

MESSAGE_APT_INSTALL_FAILED = 'APT install failed.'
MESSAGE_APT_UPDATE_FAILED = 'APT update failed.'
MESSAGE_APT_POLICY_FAILED = 'Failure checking APT policy.'
MESSAGE_DISABLED_TMPL = '{title} disabled.'
MESSAGE_NONROOT_USER = 'This command must be run as root (try using sudo)'
MESSAGE_ALREADY_DISABLED_TMPL = """\
{title} is not currently enabled.\nSee `ua status`"""
MESSAGE_ENABLED_FAILED_TMPL = 'Could not enable {title}.'
MESSAGE_ENABLED_TMPL = '{title} enabled.'
MESSAGE_ALREADY_ENABLED_TMPL = '{title} is already enabled.\nSee `ua status`'
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
See `ua status` or https://ubuntu.com/advantage"""
MESSAGE_UNATTACHED = """\
This machine is not attached to a UA subscription.
See `ua attach` or https://ubuntu.com/advantage"""

STATUS_SERVICE_HEADER = '\nSERVICE'
STATUS_TMPL = '{name: <14}{entitled: <26}{status}'

MESSAGE_ATTACH_FAILURE_TMPL = """\
Could not attach machine. Error contacting server {url}"""
MESSAGE_ATTACH_SUCCESS_TMPL = """\
This machine is now attached to '{contract_name}'.
"""

MESSAGE_ENABLE_BY_DEFAULT_TMPL = 'Enabling default service {name}'
MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL = """\
Service {name} is recommended by default. To enable run `ua enable {name}`"""
MESSAGE_DETACH_SUCCESS = 'This machine is now detached'

MESSAGE_REFRESH_ENABLE = 'One moment, checking your subscription first'
MESSAGE_REFRESH_SUCCESS = 'Successfully refreshed your subscription'
MESSAGE_REFRESH_FAILURE = 'Unable to refresh your subscription'


def colorize(string: str) -> str:
    """Return colorized string if using a tty, else original string."""
    return STATUS_COLOR.get(string, string) if sys.stdout.isatty() else string


def format_tabular(status: 'Dict[str, Any]') -> str:
    """Format status dict for tabular output."""
    if not status['attached']:
        return MESSAGE_UNATTACHED
    tech_support_level = status['techSupportLevel']

    pairs = [
        ('Account', status['account']),
        ('Subscription', status['subscription']),
    ]
    if status['origin'] != 'free':
        pairs.append(('Valid until', str(status['expires'])))
        pairs.append(('Technical support level', colorize(tech_support_level)))
    template_length = max([len(pair[0]) for pair in pairs])
    template = '{{:>{}}}: {{}}'.format(template_length)
    content = [template.format(*pair) for pair in pairs]
    content.append(STATUS_SERVICE_HEADER)
    for service_status in status['services']:
        entitled = service_status['entitled']
        fmt_args = {
            'name': service_status['name'],
            'entitled': colorize(entitled),
            'status': colorize(service_status['status'])}
        content.append(STATUS_TMPL.format(**fmt_args))
    content.append('\nEnable entitlements with `ua enable <service>`')
    return '\n'.join(content)
