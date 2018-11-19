from collections import namedtuple


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
UNAVAILABLE = 'unavailable'
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
    UNAVAILABLE: TxtColor.DISABLEGREY + UNAVAILABLE + TxtColor.ENDC,
    ENTITLED: TxtColor.OKGREEN + ENTITLED + TxtColor.ENDC,
    UNENTITLED: TxtColor.FAIL + UNENTITLED + TxtColor.ENDC,
    EXPIRED: TxtColor.FAIL + EXPIRED + TxtColor.ENDC,
    NONE: TxtColor.DISABLEGREY + NONE + TxtColor.ENDC,
    ESSENTIAL: TxtColor.OKGREEN + ESSENTIAL + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN + STANDARD + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN + ADVANCED + TxtColor.ENDC
}

STATUS_TMPL = '{name: <14}{contract_state: <26}{status}'

EntitlementStatus = namedtuple(
    'EntitlementStatus', ['contract_state', 'service_status'])


def format_entitlement_status(entitlement):
    stat = entitlement.status()
    fmt_args = {
        'name': entitlement.name,
        'contract_state': STATUS_COLOR.get(
            stat.contract_state, stat.contract_state),
        'status': STATUS_COLOR.get(
            stat.service_status, stat.service_status)}
    return STATUS_TMPL.format(**fmt_args)
