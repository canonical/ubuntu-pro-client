import logging

from uaclient import messages, system, util
from uaclient.api.u.pro.detach.v1 import detach
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.files import machine_token

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def validate_release_series(cfg: UAConfig, show_message=False):
    if not _is_attached(cfg).is_attached:
        return
    machine_token_file = machine_token.get_machine_token_file(cfg)
    current_series = system.get_release_info().series
    only_series = (
        machine_token_file.entitlements()
        .get("support", {})
        .get("entitlement", {})
        .get("affordances", {})
        .get("onlySeries", None)
    )
    if only_series and only_series != current_series:
        detach()
        allowed_release = system.get_distro_info(only_series)
        message = messages.PRO_ONLY_ALLOWED_FOR_RELEASE.format(
            release=allowed_release.release,
            series_codename=allowed_release.series_codename,
        )
        if show_message:
            print(message)
        LOG.warning(message)
