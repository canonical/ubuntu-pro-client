from uaclient.entitlements.esm import ESMEntitlement
from uaclient.entitlements.fips import FIPSEntitlement, FIPSUpdatesEntitlement
from uaclient.entitlements.livepatch import LivepatchEntitlement

from uaclient.entitlements.base import request_entitlements

ENTITLEMENT_CLASSES = [
    ESMEntitlement, FIPSEntitlement, FIPSUpdatesEntitlement,
    LivepatchEntitlement]

ENTITLEMENT_CLASS_BY_NAME = dict(
    (cls.name, cls) for cls in ENTITLEMENT_CLASSES)
