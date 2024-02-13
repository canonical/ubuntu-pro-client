import http.client
import json
import logging
import re
import socket
from typing import List, NamedTuple, Optional

from uaclient import apt, event_logger, exceptions, messages, system, util

SNAP_CMD = "/usr/bin/snap"
SNAP_INSTALL_RETRIES = [0.5, 1.0, 5.0]
HTTP_PROXY_OPTION = "proxy.http"
HTTPS_PROXY_OPTION = "proxy.https"
SNAPD_SOCKET_PATH = "/run/snapd.socket"
SNAPD_SNAPS_API = "/v2/snaps/{}"

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


SnapPackage = NamedTuple(
    "SnapPackage",
    [
        ("name", str),
        ("version", str),
        ("revision", str),
        ("channel", str),
        ("publisher", str),
    ],
)


def is_snapd_installed() -> bool:
    """Returns whether or not snap is installed"""
    return "snapd" in apt.get_installed_packages_names()


def is_snapd_installed_as_a_snap() -> bool:
    """Returns whether or not snapd is installed as a snap"""
    return any((snap.name == "snapd" for snap in get_installed_snaps()))


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
    if not is_snapd_installed():
        LOG.debug("Skipping configure snap proxy. snapd is not installed.")
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
    if not is_snapd_installed():
        LOG.debug("Skipping unconfigure snap proxy. snapd is not installed.")
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


def get_installed_snaps() -> List[SnapPackage]:
    out, _ = system.subp(
        ["snap", "list", "--color", "never", "--unicode", "never"]
    )
    apps = out.splitlines()
    apps = apps[1:]
    snaps = []
    for line in apps:
        snap = line.split()[0]
        snaps.append(get_snap_info(snap))

    return snaps


def install_snapd():
    event.info(messages.APT_UPDATING_LIST.format(name="standard Ubuntu"))
    try:
        apt.update_sources_list(apt.get_system_sources_file())
    except exceptions.UbuntuProError as e:
        LOG.debug(
            "Trying to install snapd. Ignoring apt-get update failure: %s",
            str(e),
        )
    try:
        system.subp(
            ["apt-get", "install", "--assume-yes", "snapd"],
            retry_sleeps=apt.APT_RETRIES,
        )
    except exceptions.ProcessExecutionError:
        raise exceptions.CannotInstallSnapdError()


def run_snapd_wait_cmd():
    try:
        system.subp([SNAP_CMD, "wait", "system", "seed.loaded"], capture=True)
    except exceptions.ProcessExecutionError as e:
        if re.search(r"unknown command .*wait", str(e).lower()):
            LOG.warning(
                "Detected version of snapd that does not have wait command"
            )
            event.info(messages.SNAPD_DOES_NOT_HAVE_WAIT_CMD)
        else:
            raise


def install_snap(
    snap: str,
    channel: Optional[str] = None,
    classic_confinement_support: bool = False,
):
    cmd = [SNAP_CMD, "install", snap]

    if classic_confinement_support:
        cmd += ["--classic"]

    if channel:
        cmd += ["--channel={}".format(channel)]

    system.subp(
        cmd,
        capture=True,
        retry_sleeps=SNAP_INSTALL_RETRIES,
    )


def refresh_snap(snap: str):
    system.subp([SNAP_CMD, "refresh", snap], capture=True)


def get_snap_info(snap: str) -> SnapPackage:
    snap_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    snap_sock.connect(SNAPD_SOCKET_PATH)

    conn = http.client.HTTPConnection("localhost")
    conn.sock = snap_sock
    url = SNAPD_SNAPS_API.format(snap)

    try:
        conn.request("GET", SNAPD_SNAPS_API.format(snap))
        response = conn.getresponse()
        out = response.read().decode("utf-8")

        try:
            data = json.loads(out)
        except json.JSONDecodeError as e:
            LOG.warning(
                "JSONDecodeError while parsing result of snap api call to %s, "
                'returning None. output was: "%s"',
                url,
                out,
                exc_info=e,
            )
            raise exceptions.InvalidJson(
                source="SNAPD API {}".format(url), out=out
            )

        # This means that the snap doesn't exist or is not installed
        if response.status != 200:
            if (
                response.status == 404
                and data.get("result", {}).get("kind") == "snap-not-found"
            ):
                raise exceptions.SnapNotInstalledError(snap=snap)
            else:
                error_msg = data.get("result", {}).get("message")
                raise exceptions.UnexpectedSnapdAPIError(error=error_msg)

    except ConnectionRefusedError:
        raise exceptions.SnapdAPIConnectionRefused()
    finally:
        conn.close()
        snap_sock.close()

    snap_info = data.get("result", {})
    return SnapPackage(
        name=snap_info.get("name", ""),
        version=snap_info.get("version", ""),
        revision=snap_info.get("revision", ""),
        channel=snap_info.get("channel", ""),
        publisher=snap_info.get("publisher", {}).get("username", ""),
    )
