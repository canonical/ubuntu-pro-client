
class TxtColor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    DISABLEGREY = '\033[37m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

ACTIVE = 'active'
INACTIVE = 'inactive'
INAPPLICABLE = 'inapplicable'
ENTITLED = 'entitled'
UNENTITLED = 'unentitled'
EXPIRED = 'expired'
NONE = 'none'
ESSENTIAL = 'essential'
STANDARD = 'standard'
ADVANCED = 'advanced'

# Colorized status output for terminal
STATUS_COLOR = {
    ACTIVE: TxtColor.OKGREEN + ACTIVE + TxtColor.ENDC,
    INACTIVE: TxtColor.FAIL + INACTIVE + TxtColor.ENDC,
    INAPPLICABLE: TxtColor.DISABLEGREY + INAPPLICABLE + TxtColor.ENDC,
    ENTITLED: TxtColor.OKGREEN + ENTITLED + TxtColor.ENDC,
    UNENTITLED: TxtColor.FAIL + UNENTITLED + TxtColor.ENDC,
    EXPIRED: TxtColor.FAIL + EXPIRED + TxtColor.ENDC,
    NONE: TxtColor.DISABLEGREY + NONE + TxtColor.ENDC,
    ESSENTIAL: TxtColor.OKGREEN + ESSENTIAL + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN + STANDARD + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN + ADVANCED + TxtColor.ENDC
}

MESSAGE_NONROOT_USER = 'This command must be run as root (try using sudo)'
MESSAGE_ALREADY_ENABLED_TMPL = '{title} is already enabled.'
MESSAGE_UNENTITLED_TMPL = """\
This subscription is not entitled to {title}.
See `ua status` or https://ubuntu.com/advantage
"""
MESSAGE_UNATTACHED = """\
This machine is not attached to a UA subscription.

See `ua attach` or https://ubuntu.com/advantage
"""

STATUS_TMPL = '{name: <14}{contract_state: <26}{status}'


def format_entitlement_status(entitlement):
    contract_status = entitlement.contract_status()
    operational_status = entitlement.operational_status()
    fmt_args = {
        'name': entitlement.name,
        'contract_state': STATUS_COLOR.get(contract_status, contract_status),
        'status': STATUS_COLOR.get(operational_status, operational_status)}
    return STATUS_TMPL.format(**fmt_args)
