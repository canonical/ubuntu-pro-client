import datetime
import enum
import json
import logging
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from uaclient import event_logger, exceptions, messages, system, util
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IncorrectTypeError,
    StringDataValue,
    data_list,
)
from uaclient.files import state_files
from uaclient.http import serviceclient

HTTP_PROXY_OPTION = "http-proxy"
HTTPS_PROXY_OPTION = "https-proxy"

LIVEPATCH_CMD = "/snap/bin/canonical-livepatch"

LIVEPATCH_API_V1_KERNELS_SUPPORTED = "/v1/api/kernels/supported"

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


@enum.unique
class LivepatchSupport(enum.Enum):
    SUPPORTED = object()
    KERNEL_UPGRADE_REQUIRED = object()
    KERNEL_EOL = object()
    UNSUPPORTED = object()
    UNKNOWN = object()


class LivepatchPatchFixStatus(DataObject):
    fields = [
        Field("name", StringDataValue, required=False, dict_key="Name"),
        Field("patched", BoolDataValue, required=False, dict_key="Patched"),
    ]

    def __init__(
        self,
        name: Optional[str],
        patched: Optional[bool],
    ):
        self.name = name
        self.patched = patched


class LivepatchPatchStatus(DataObject):
    fields = [
        Field("state", StringDataValue, required=False, dict_key="State"),
        Field(
            "fixes",
            data_list(LivepatchPatchFixStatus),
            required=False,
            dict_key="Fixes",
        ),
        Field("version", StringDataValue, required=False, dict_key="Version"),
    ]

    def __init__(
        self,
        state: Optional[str],
        fixes: Optional[List[LivepatchPatchFixStatus]],
        version: Optional[str],
    ):
        self.state = state
        self.fixes = fixes
        self.version = version


class LivepatchStatusStatus(DataObject):
    fields = [
        Field("kernel", StringDataValue, required=False, dict_key="Kernel"),
        Field(
            "livepatch",
            LivepatchPatchStatus,
            required=False,
            dict_key="Livepatch",
        ),
        Field(
            "supported",
            StringDataValue,
            required=False,
            dict_key="Supported",
        ),
    ]

    def __init__(
        self,
        kernel: Optional[str],
        livepatch: Optional[LivepatchPatchStatus],
        supported: Optional[str],
    ):
        self.kernel = kernel
        self.livepatch = livepatch
        self.supported = supported


class LivepatchStatus(DataObject):
    fields = [
        Field(
            "status",
            data_list(LivepatchStatusStatus),
            required=False,
            dict_key="Status",
        ),
    ]

    def __init__(
        self,
        status: Optional[List[LivepatchStatusStatus]],
    ):
        self.status = status


def status() -> Optional[LivepatchStatusStatus]:
    if not is_livepatch_installed():
        LOG.debug("canonical-livepatch is not installed")
        return None

    try:
        out, _ = system.subp(
            [LIVEPATCH_CMD, "status", "--verbose", "--format", "json"]
        )
    except exceptions.ProcessExecutionError as e:
        # only raise an error if there is a legitimate problem, not just lack
        # of enablement
        if "Machine is not enabled" in e.stderr:
            LOG.warning(e.stderr)
            return None
        LOG.warning(
            "canonical-livepatch returned error when checking status:\n%s",
            exc_info=e,
        )
        raise e

    try:
        status_json = json.loads(out)
    except json.JSONDecodeError as e:
        LOG.warning(
            "JSONDecodeError while parsing livepatch status, returning None. "
            'output was: "%s"',
            out,
            exc_info=e,
        )
        return None

    try:
        status_root = LivepatchStatus.from_dict(status_json)
    except IncorrectTypeError:
        LOG.warning(
            "canonical-livepatch status returned unexpected structure: %s",
            out,
        )
        return None

    if status_root.status is None or len(status_root.status) < 1:
        LOG.debug("canonical-livepatch has no status")
        return None

    return status_root.status[0]


def _convert_str_to_livepatch_support_status(
    status_str: Optional[str],
) -> Optional[LivepatchSupport]:
    if status_str == "supported":
        return LivepatchSupport.SUPPORTED
    if status_str == "kernel-upgrade-required":
        return LivepatchSupport.KERNEL_UPGRADE_REQUIRED
    if status_str == "kernel-end-of-life":
        return LivepatchSupport.KERNEL_EOL
    if status_str == "unsupported":
        return LivepatchSupport.UNSUPPORTED
    if status_str == "unknown":
        return LivepatchSupport.UNKNOWN
    return None


class UALivepatchClient(serviceclient.UAServiceClient):
    cfg_url_base_attr = "livepatch_url"

    def is_kernel_supported(
        self,
        version: str,
        flavor: str,
        arch: str,
        codename: str,
        build_date: Optional[datetime.datetime],
    ) -> Optional[LivepatchSupport]:
        query_params = {
            "kernel-version": version,
            "flavour": flavor,
            "architecture": arch,
            "codename": codename,
            "build-date": (
                build_date.isoformat() if build_date is not None else "unknown"
            ),
        }
        headers = self.headers()
        try:
            response = self.request_url(
                LIVEPATCH_API_V1_KERNELS_SUPPORTED,
                query_params=query_params,
                headers=headers,
            )
        except Exception as e:
            LOG.warning("error while checking livepatch supported kernels API")
            LOG.warning(e)
            return None

        if response.code != 200:
            LOG.warning("livepatch supported kernels API was unsuccessful")
            LOG.warning(response.body)
            return None

        api_supported_val = response.json_dict.get("Supported")
        if api_supported_val is None or isinstance(api_supported_val, bool):
            # old version, True means supported, None means unsupported
            if api_supported_val:
                return LivepatchSupport.SUPPORTED
            return LivepatchSupport.UNSUPPORTED
        # new version, value is a string
        return _convert_str_to_livepatch_support_status(api_supported_val)


def _on_supported_kernel_cli() -> Optional[LivepatchSupport]:
    try:
        lp_status = status()
    except exceptions.ProcessExecutionError:
        return None

    if lp_status is None:
        return None
    return _convert_str_to_livepatch_support_status(lp_status.supported)


def _on_supported_kernel_cache(
    version: str, flavor: str, arch: str, codename: str
) -> Tuple[bool, Optional[bool]]:
    """Check local cache of kernel support

    :return: (is_cache_valid, result)
    """
    try:
        cache_data = state_files.livepatch_support_cache.read()
    except Exception:
        cache_data = None

    if cache_data is not None:
        one_week_ago = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(days=7)
        if all(
            [
                cache_data.cached_at > one_week_ago,  # less than one week old
                cache_data.version == version,
                cache_data.flavor == flavor,
                cache_data.arch == arch,
                cache_data.codename == codename,
            ]
        ):
            if cache_data.supported is None:
                LOG.warning("livepatch kernel support cache has None value")
            return (True, cache_data.supported)
    return (False, None)


def _on_supported_kernel_api(
    version: str,
    flavor: str,
    arch: str,
    codename: str,
    build_date: Optional[datetime.datetime],
) -> Optional[LivepatchSupport]:
    supported = UALivepatchClient().is_kernel_supported(
        version=version,
        flavor=flavor,
        arch=arch,
        codename=codename,
        build_date=build_date,
    )

    # cache response as a bool/None before returning
    cache_supported = None
    if supported == LivepatchSupport.SUPPORTED:
        cache_supported = True
    elif supported == LivepatchSupport.UNSUPPORTED:
        cache_supported = False
    state_files.livepatch_support_cache.write(
        state_files.LivepatchSupportCacheData(
            version=version,
            flavor=flavor,
            arch=arch,
            codename=codename,
            supported=cache_supported,
            cached_at=datetime.datetime.now(datetime.timezone.utc),
        )
    )

    if supported is None:
        LOG.warning("livepatch kernel support API response was ambiguous")
    return supported


@lru_cache(maxsize=None)
def on_supported_kernel() -> LivepatchSupport:
    """
    Checks CLI, local cache, and API in that order for kernel support
    If all checks fail to return an authoritative answer, we return None
    """

    # first check cli
    cli_says = _on_supported_kernel_cli()
    if cli_says is not None:
        LOG.debug("using livepatch cli for support")
        return cli_says

    # gather required system info to query support
    kernel_info = system.get_kernel_info()
    if (
        kernel_info.flavor is None
        or kernel_info.major is None
        or kernel_info.minor is None
    ):
        LOG.warning(
            "unable to determine enough kernel information to "
            "check livepatch support"
        )
        return LivepatchSupport.UNKNOWN

    arch = util.standardize_arch_name(kernel_info.uname_machine_arch)
    codename = system.get_release_info().series

    lp_api_kernel_ver = "{major}.{minor}".format(
        major=kernel_info.major, minor=kernel_info.minor
    )

    # second check cache
    is_cache_valid, cache_says = _on_supported_kernel_cache(
        lp_api_kernel_ver, kernel_info.flavor, arch, codename
    )
    if is_cache_valid:
        LOG.debug("using livepatch support cache")
        if cache_says is None:
            return LivepatchSupport.UNKNOWN
        if cache_says:
            return LivepatchSupport.SUPPORTED
        if not cache_says:
            return LivepatchSupport.UNSUPPORTED

    # finally check api
    LOG.debug("using livepatch support api")
    api_says = _on_supported_kernel_api(
        lp_api_kernel_ver,
        kernel_info.flavor,
        arch,
        codename,
        kernel_info.build_date,
    )
    if api_says is None:
        return LivepatchSupport.UNKNOWN
    return api_says


def unconfigure_livepatch_proxy(
    protocol_type: str, retry_sleeps: Optional[List[float]] = None
) -> None:
    """
    Unset livepatch configuration settings for http and https proxies.

    :param protocol_type: String either http or https
    :param retry_sleeps: Optional list of sleep lengths to apply between
        retries. Specifying a list of [0.5, 1] tells subp to retry twice
        on failure; sleeping half a second before the first retry and 1 second
        before the second retry.
    """
    if not is_livepatch_installed():
        return
    system.subp(
        [LIVEPATCH_CMD, "config", "{}-proxy=".format(protocol_type)],
        retry_sleeps=retry_sleeps,
    )


def configure_livepatch_proxy(
    http_proxy: Optional[str] = None,
    https_proxy: Optional[str] = None,
    retry_sleeps: Optional[List[float]] = None,
) -> None:
    """
    Configure livepatch to use http and https proxies.

    :param http_proxy: http proxy to be used by livepatch. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by livepatch. If None, it will
                        not be configured
    :@param retry_sleeps: Optional list of sleep lengths to apply between
                               snap calls
    """
    from uaclient.entitlements import LivepatchEntitlement

    if http_proxy or https_proxy:
        event.info(
            messages.SETTING_SERVICE_PROXY.format(
                service=LivepatchEntitlement.title
            )
        )

    if http_proxy:
        system.subp(
            [LIVEPATCH_CMD, "config", "http-proxy={}".format(http_proxy)],
            retry_sleeps=retry_sleeps,
        )

    if https_proxy:
        system.subp(
            [LIVEPATCH_CMD, "config", "https-proxy={}".format(https_proxy)],
            retry_sleeps=retry_sleeps,
        )


def get_config_option_value(key: str) -> Optional[str]:
    """
    Gets the config value from livepatch.
    :param key: can be any valid livepatch config option
    :return: the value of the livepatch config option, or None if not set
    """
    out, _ = system.subp([LIVEPATCH_CMD, "config"])
    match = re.search("^{}: (.*)$".format(key), out, re.MULTILINE)
    value = match.group(1) if match else None
    if value:
        # remove quotes if present
        value = re.sub(r"\"(.*)\"", r"\g<1>", value)
    return value.strip() if value else None


def is_livepatch_installed() -> bool:
    return system.which(LIVEPATCH_CMD) is not None
