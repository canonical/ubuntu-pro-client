from uaclient.entitlements.cis import CISEntitlement
from uaclient.entitlements.cc import CommonCriteriaEntitlement
from uaclient.entitlements.esm import ESMEntitlement
from uaclient.entitlements import fips
from uaclient.entitlements.livepatch import LivepatchEntitlement

ENTITLEMENT_CLASSES = [
    CommonCriteriaEntitlement, CISEntitlement, ESMEntitlement,
    fips.FIPSEntitlement, fips.FIPSUpdatesEntitlement, LivepatchEntitlement]

ENTITLEMENT_CLASS_BY_NAME = dict(
    (cls.name, cls) for cls in ENTITLEMENT_CLASSES)
