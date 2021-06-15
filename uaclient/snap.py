from typing import List, Optional

from uaclient import apt, status, util

SNAP_CMD = "/usr/bin/snap"
SNAP_INSTALL_RETRIES = [0.5, 1.0, 5.0]
HTTP_PROXY_OPTION = "proxy.http"
HTTPS_PROXY_OPTION = "proxy.https"


def is_installed() -> bool:
    """Returns whether or not snap is installed"""
    return "snapd" in apt.get_installed_packages()


def configure_snap_proxy(
    http_proxy: Optional[str],
    https_proxy: Optional[str],
    snap_retries: Optional[List[float]] = None,
) -> None:
    """
    Configure snap to use http and https proxies.

    :param http_proxy: http proxy to be used by snap. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by snap. If None, it will
                        not be configured
    :@param snap_retries: Optional list of sleep lengths to apply between
                          snap calls
    """
    if http_proxy or https_proxy:
        print(status.MESSAGE_SETTING_SERVICE_PROXY.format(service="snap"))

    if http_proxy:
        util.subp(
            ["snap", "set", "system", "proxy.http={}".format(http_proxy)],
            retry_sleeps=snap_retries,
        )

    if https_proxy:
        util.subp(
            ["snap", "set", "system", "proxy.https={}".format(https_proxy)],
            retry_sleeps=snap_retries,
        )


def get_config_option_value(key: str) -> Optional[str]:
    """
    Gets the config value from snap.
    :param protocol: can be any valid snap config option
    :return: the value of the snap config option, or None if not set
    """
    try:
        out, _ = util.subp(["snap", "get", "system", key])
        return out.strip()
    except util.ProcessExecutionError:
        return None
