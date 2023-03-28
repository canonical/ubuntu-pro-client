import datetime
import json
import logging
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from uaclient import (
    event_logger,
    exceptions,
    messages,
    serviceclient,
    system,
    util,
)
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IncorrectTypeError,
    StringDataValue,
    data_list,
)
from uaclient.files import state_files

HTTP_PROXY_OPTION = "http-proxy"
HTTPS_PROXY_OPTION = "https-proxy"

LIVEPATCH_CMD = "/snap/bin/canonical-livepatch"

LIVEPATCH_API_V1_KERNELS_SUPPORTED = "/v1/api/kernels/supported"

event = event_logger.get_event_logger()


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
    ]

    def __init__(
        self,
        state: Optional[str],
        fixes: Optional[List[LivepatchPatchFixStatus]],
    ):
        self.state = state
        self.fixes = fixes


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
        logging.debug("canonical-livepatch is not installed")
        return None

    try:
        out, _ = system.subp([LIVEPATCH_CMD, "status", "--format", "json"])
    except exceptions.ProcessExecutionError:
        with util.disable_log_to_console():
            logging.warning(
                "canonical-livepatch returned error when checking status"
            )
        return None

    try:
        status_json = json.loads(out)
    except json.JSONDecodeError:
        with util.disable_log_to_console():
            logging.warning(
                "canonical-livepatch status returned invalid json: {}".format(
                    out
                )
            )
        return None

    try:
        status_root = LivepatchStatus.from_dict(status_json)
    except IncorrectTypeError:
        with util.disable_log_to_console():
            logging.warning(
                "canonical-livepatch status returned unexpected "
                "structure: {}".format(out)
            )
        return None

    if status_root.status is None or len(status_root.status) < 1:
        logging.debug("canonical-livepatch has no status")
        return None

    return status_root.status[0]


class UALivepatchClient(serviceclient.UAServiceClient):

    cfg_url_base_attr = "livepatch_url"
    api_error_cls = exceptions.UrlError

    def is_kernel_supported(
        self, version: str, flavor: str, arch: str, codename: str
    ) -> Optional[bool]:
        """
        :returns: True if supported
                  False if unsupported
                  None if API returns error or ambiguous response
        """
        query_params = {
            "kernel-version": version,
            "flavour": flavor,
            "architecture": arch,
            "codename": codename,
        }
        headers = self.headers()
        try:
            result, _headers = self.request_url(
                LIVEPATCH_API_V1_KERNELS_SUPPORTED,
                query_params=query_params,
                headers=headers,
            )
        except Exception as e:
            with util.disable_log_to_console():
                logging.warning(
                    "error while checking livepatch supported kernels API"
                )
                logging.warning(e)
            return None

        if not isinstance(result, dict):
            logging.warning(
                "livepatch api returned something that isn't a dict"
            )
            return None

        return bool(result.get("Supported", False))


def _on_supported_kernel_cli() -> Optional[bool]:
    lp_status = status()
    if lp_status is None:
        return None
    if lp_status.supported == "supported":
        return True
    if lp_status.supported == "unsupported":
        return False
    return None


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
                with util.disable_log_to_console():
                    logging.warning(
                        "livepatch kernel support cache has None value"
                    )
            return (True, cache_data.supported)
    return (False, None)


def _on_supported_kernel_api(
    version: str, flavor: str, arch: str, codename: str
) -> Optional[bool]:
    supported = UALivepatchClient().is_kernel_supported(
        version=version,
        flavor=flavor,
        arch=arch,
        codename=codename,
    )

    # cache response before returning
    state_files.livepatch_support_cache.write(
        state_files.LivepatchSupportCacheData(
            version=version,
            flavor=flavor,
            arch=arch,
            codename=codename,
            supported=supported,
            cached_at=datetime.datetime.now(datetime.timezone.utc),
        )
    )

    if supported is None:
        with util.disable_log_to_console():
            logging.warning(
                "livepatch kernel support API response was ambiguous"
            )
    return supported


@lru_cache(maxsize=None)
def on_supported_kernel() -> Optional[bool]:
    """
    Checks CLI, local cache, and API in that order for kernel support
    If all checks fail to return an authoritative answer, we return None
    """

    # first check cli
    cli_says = _on_supported_kernel_cli()
    if cli_says is not None:
        logging.debug("using livepatch cli for support")
        return cli_says

    # gather required system info to query support
    kernel_info = system.get_kernel_info()
    if (
        kernel_info.flavor is None
        or kernel_info.major is None
        or kernel_info.minor is None
    ):
        logging.warning(
            "unable to determine enough kernel information to "
            "check livepatch support"
        )
        return None

    arch = util.standardize_arch_name(system.get_dpkg_arch())
    codename = system.get_platform_info()["series"]

    lp_api_kernel_ver = "{major}.{minor}".format(
        major=kernel_info.major, minor=kernel_info.minor
    )

    # second check cache
    is_cache_valid, cache_says = _on_supported_kernel_cache(
        lp_api_kernel_ver, kernel_info.flavor, arch, codename
    )
    if is_cache_valid:
        logging.debug("using livepatch support cache")
        return cache_says

    # finally check api
    logging.debug("using livepatch support api")
    return _on_supported_kernel_api(
        lp_api_kernel_ver, kernel_info.flavor, arch, codename
    )


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
