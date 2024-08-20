import logging

from uaclient import lock, messages, system, util
from uaclient.api.u.pro.detach.v1 import detach
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def validate_release_series(cfg: UAConfig, only_series, show_message=False):
    LOG.debug("Validating release series")
    if not _is_attached(cfg).is_attached:
        return
    current_series = system.get_release_info().series
    if only_series != current_series:
        LOG.debug(
            "Detaching due to current series being %s. only_series: %s",
            current_series,
            only_series,
        )
        lock.clear_lock_file_if_present()
        detach()
        allowed_release = system.get_distro_info(only_series)
        message = messages.PRO_ONLY_ALLOWED_FOR_RELEASE.format(
            release=allowed_release.release,
            series_codename=allowed_release.series_codename,
        )
        if show_message:
            print(message)
        LOG.warning(message)
