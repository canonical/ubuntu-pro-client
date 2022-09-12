import logging
import re
from typing import List, Optional

from uaclient import apt, event_logger, exceptions, messages, system

SNAP_CMD = "/usr/bin/snap"
SNAP_INSTALL_RETRIES = [0.5, 1.0, 5.0]
HTTP_PROXY_OPTION = "proxy.http"
HTTPS_PROXY_OPTION = "proxy.https"
SNAP_CHANNEL_SHORTEN_VALUE = "…"

event = event_logger.get_event_logger()


def is_installed() -> bool:
    """Returns whether or not snap is installed"""
    return "snapd" in apt.get_installed_packages_names()


def configure_snap_proxy(
    http_proxy: Optional[str] = None,
    https_proxy: Optional[str] = None,
    retry_sleeps: Optional[List[float]] = None,
) -> None:
    """
    Configure snap to use http and https proxies.

    :param http_proxy: http proxy to be used by snap. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by snap. If None, it will
                        not be configured
    :param retry_sleeps: Optional list of sleep lengths to apply between
        retries. Specifying a list of [0.5, 1] tells subp to retry twice
        on failure; sleeping half a second before the first retry and 1 second
        before the second retry.
    """
    if not system.which(SNAP_CMD):
        logging.debug(
            "Skipping configure snap proxy. {} does not exist.".format(
                SNAP_CMD
            )
        )
        return

    if http_proxy or https_proxy:
        event.info(messages.SETTING_SERVICE_PROXY.format(service="snap"))

    if http_proxy:
        system.subp(
            ["snap", "set", "system", "proxy.http={}".format(http_proxy)],
            retry_sleeps=retry_sleeps,
        )

    if https_proxy:
        system.subp(
            ["snap", "set", "system", "proxy.https={}".format(https_proxy)],
            retry_sleeps=retry_sleeps,
        )


def unconfigure_snap_proxy(
    protocol_type: str, retry_sleeps: Optional[List[float]] = None
) -> None:
    """
    Unset snap configuration settings for http and https proxies.

    :param protocol_type: String either http or https
    :param retry_sleeps: Optional list of sleep lengths to apply between
        retries. Specifying a list of [0.5, 1] tells subp to retry twice
        on failure; sleeping half a second before the first retry and 1 second
        before the second retry.
    """
    if not system.which(SNAP_CMD):
        logging.debug(
            "Skipping unconfigure snap proxy. {} does not exist.".format(
                SNAP_CMD
            )
        )
        return
    system.subp(
        ["snap", "unset", "system", "proxy.{}".format(protocol_type)],
        retry_sleeps=retry_sleeps,
    )


def get_config_option_value(key: str) -> Optional[str]:
    """
    Gets the config value from snap.
    :param protocol: can be any valid snap config option
    :return: the value of the snap config option, or None if not set
    """
    try:
        out, _ = system.subp(["snap", "get", "system", key])
        return out.strip()
    except exceptions.ProcessExecutionError:
        return None


def get_snap_package_info_tracking(package: str) -> Optional[str]:
    out, _ = system.subp(
        ["snap", "info", package, "--color", "never", "--unicode", "never"]
    )
    match = re.search(r"tracking:\s+(?P<tracking>.*)", out)
    if match:
        return match.group("tracking")
    return None


class SnapPackage:
    def __init__(self, name, version, rev, tracking, publisher, notes):
        self.name = name
        self.version = version
        self.rev = rev
        self.tracking = tracking
        self.publisher = publisher
        self.notes = notes


def get_installed_snaps() -> List[SnapPackage]:
    out, _ = system.subp(
        ["snap", "list", "--color", "never", "--unicode", "never"]
    )
    apps = out.splitlines()
    apps = apps[1:]
    snaps = []
    for line in apps:
        pkg = line.split()
        snap = SnapPackage(*pkg)
        if snap.tracking.endswith(SNAP_CHANNEL_SHORTEN_VALUE):
            channel = get_snap_package_info_tracking(snap.name)
            snap.tracking = channel if channel else snap.tracking
        snaps.append(snap)

    return snaps
