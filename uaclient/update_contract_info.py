import logging

from uaclient import exceptions, lock, messages, system, util
from uaclient.api.u.pro.detach.v1 import detach
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def validate_release_series(cfg: UAConfig, only_series, show_message=False):
    LOG.debug("Validating release series")
    if not _is_attached(cfg).is_attached:
        return

    current_series = system.get_release_info().series
    try:
        allowed_release = system.get_distro_info(only_series)
    except exceptions.MissingSeriesInDistroInfoFile:
        # If onlySeries is not present on the distro-info CSV
        # we consider that it is newer than the current release
        pass
    else:
        current_release = system.get_distro_info(current_series)
        # Only series is now meant to be allowed on the specified release
        # and all previous releases
        if current_release.eol > allowed_release.eol:
            LOG.debug(
                "Detaching due to current series %s being higher than only_series: %s",  # noqa
                current_series,
                only_series,
            )
            lock.clear_lock_file_if_present()
            detach()
            message = messages.PRO_ONLY_ALLOWED_FOR_RELEASE.format(
                release=allowed_release.release,
                series_codename=allowed_release.series_codename,
            )
            if show_message:
                print(message)
            LOG.warning(message)
