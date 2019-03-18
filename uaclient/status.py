from datetime import datetime

from uaclient import defaults
from uaclient import util


class TxtColor(object):
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
EXPIRED = 'expired'
NONE = 'none'
COMMUNITY = 'community'
STANDARD = 'standard'
ADVANCED = 'advanced'

# Colorized status output for terminal
STATUS_COLOR = {
    ACTIVE: TxtColor.OKGREEN + ACTIVE + TxtColor.ENDC,
    INACTIVE: TxtColor.FAIL + INACTIVE + TxtColor.ENDC,
    INAPPLICABLE: TxtColor.DISABLEGREY + INAPPLICABLE + TxtColor.ENDC,
    ENTITLED: TxtColor.OKGREEN + ENTITLED + TxtColor.ENDC,
    EXPIRED: TxtColor.FAIL + EXPIRED + TxtColor.ENDC,
    NONE: TxtColor.DISABLEGREY + NONE + TxtColor.ENDC,
    COMMUNITY: TxtColor.DISABLEGREY + COMMUNITY + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN + STANDARD + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN + ADVANCED + TxtColor.ENDC
}

MESSAGE_DISABLED_TMPL = '{title} disabled.'
MESSAGE_NONROOT_USER = 'This command must be run as root (try using sudo)'
MESSAGE_ALREADY_DISABLED_TMPL = '\
{title} is not currently enabled.\nSee `ua status`'
MESSAGE_ENABLED_FAILED_TMPL = 'Could not enable {title}.'
MESSAGE_ENABLED_TMPL = '{title} enabled.'
MESSAGE_ALREADY_ENABLED_TMPL = '{title} is already enabled.\nSee `ua status`'
MESSAGE_INAPPLICABLE_SERIES_TMPL = '\
{title} is not available for Ubuntu {series}.'
MESSAGE_UNENTITLED_TMPL = """\
This subscription is not entitled to {title}.
See `ua status` or https://ubuntu.com/advantage
"""
MESSAGE_UNATTACHED = """\
This machine is not attached to a UA subscription.
See `ua attach` or https://ubuntu.com/advantage
"""


MESSAGE_MOTD_ACTIVE_TMPL = """
 * This system is covered by Ubuntu Advantage{tech_support} until {date}
Run `ua status` for details.
"""
MESSAGE_MOTD_EXPIRED_TMPL = """\
 * Your Ubuntu Advantage subscription {name} expired on {date}!
"""
MESSAGE_MOTD_ESM_ENABLED_UPGRADE_TMPL = """\
 %d are extended security maintenance updates
"""
MESSAGE_MOTD_ESM_DISABLED_UPGRADE_TMPL = """\
 %d additional updates are available with Extended Security Maintenance.
 See `ua enable esm` or https://ubuntu.com/advantage
"""

STATUS_TMPL = '{name: <14}{contract_state: <26}{status}'


def format_entitlement_status(entitlement):
    contract_status = entitlement.contract_status()
    operational_status, _details = entitlement.operational_status()
    fmt_args = {
        'name': entitlement.name,
        'contract_state': STATUS_COLOR.get(contract_status, contract_status),
        'status': STATUS_COLOR.get(operational_status, operational_status)}
    return STATUS_TMPL.format(**fmt_args)


def get_upgradeable_esm_package_count():
    import apt_pkg
    apt_pkg.init()

    cache = apt_pkg.Cache(None)
    dependencyCache = apt_pkg.DepCache(cache)
    upgrade_count = 0

    for package in cache.packages:
        if not package.current_ver:
            continue
        upgrades = [v for v in package.version_list if v > package.current_ver]

        for upgrade in upgrades:
            for package_file, _idx in upgrade.file_list:
                if dependencyCache.policy.get_priority(package_file) == -32768:
                    upgrade_count += 1
                    break
    return upgrade_count


def write_motd_summary(cfg):
    """Persist MOTD summary to cache files."""
    esm_status = get_motd_summary(cfg, esm_only=True)
    util.write_file(defaults.MOTD_UPDATES_AVAILABLE_CACHE_FILE, esm_status)
    ua_motd_status = get_motd_summary(cfg)
    util.write_file(defaults.MOTD_CACHE_FILE, ua_motd_status)


def get_motd_summary(cfg, esm_only=False):
    """Return MOTD summary text for all UA entitlements"""
    from uaclient import entitlements
    if esm_only:
        upgrade_count = get_upgradeable_esm_package_count()
        if cfg.is_attached:
            esm_cfg = cfg.entitlements.get('esm')
            if esm_cfg and esm_cfg['entitlement'].get('entitled'):
                return MESSAGE_MOTD_ESM_ENABLED_UPGRADE_TMPL % upgrade_count
        return MESSAGE_MOTD_ESM_DISABLED_UPGRADE_TMPL % upgrade_count
    if not cfg.is_attached:
        return ''   # No UA attached, so don't announce anything
    motd_lines = []
    tech_support = ''
    support_entitlement = cfg.entitlements.get('support')
    if support_entitlement:
        support_level = support_entitlement.get(
            'affordances', {}).get('supportLevel', COMMUNITY)
        if support_level != COMMUNITY:
            tech_support = ' %s support' % support_level
    # TODO(Support multiple contracts)
    contractInfo = cfg.contracts['contracts'][0]['contractInfo']
    expiry = datetime.strptime(
        contractInfo['effectiveTo'], '%Y-%m-%dT%H:%M:%SZ')
    if expiry >= datetime.utcnow():
        motd_lines.append(MESSAGE_MOTD_ACTIVE_TMPL.format(
            tech_support=tech_support, date=expiry.date()))
    else:
        motd_lines.append(MESSAGE_MOTD_EXPIRED_TMPL.format(
            name=contractInfo['name'], date=expiry.date()))
    for ent_name in ('livepatch', 'fips', 'fips-updates'):
        ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[ent_name]
        entitlement = ent_cls(cfg)
        entitlement_motd = entitlement.get_motd_summary().rstrip('\n')
        if entitlement_motd:
            motd_lines.append(entitlement_motd)
    if not motd_lines:
        return ''
    return '\n'.join(motd_lines) + '\n'
