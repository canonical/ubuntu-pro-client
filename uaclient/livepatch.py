import re
from typing import List, Optional

from uaclient import util

LIVEPATCH_RETRIES = [0.5, 1.0]
HTTP_PROXY_OPTION = "http-proxy"
HTTPS_PROXY_OPTION = "https-proxy"


def is_installed() -> bool:
    """Returns whether or not livepatch is installed"""
    return True if util.which("/snap/bin/canonical-livepatch") else False


def configure_livepatch_proxy(
    http_proxy: "Optional[str]",
    https_proxy: "Optional[str]",
    livepatch_retries: "Optional[List[float]]" = None,
) -> None:
    """
    Configure livepatch to use http and https proxies.

    :param http_proxy: http proxy to be used by livepatch. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by livepatch. If None, it will
                        not be configured
    :@param livepatch_retries: Optional list of sleep lengths to apply between
                               snap calls
    """
    if http_proxy:
        util.subp(
            [
                "canonical-livepatch",
                "config",
                "http-proxy={}".format(http_proxy),
            ],
            retry_sleeps=livepatch_retries,
        )

    if https_proxy:
        util.subp(
            [
                "canonical-livepatch",
                "config",
                "https-proxy={}".format(https_proxy),
            ],
            retry_sleeps=livepatch_retries,
        )


def get_config_option_value(key: str) -> Optional[str]:
    """
    Gets the config value from livepatch.

    :param protocol: can be any valid livepatch config option
    :return: the value of the livepatch config option, or None if not set
    """
    out, _ = util.subp(["canonical-livepatch", "config"])
    match = re.search("^{}: (.*)$".format(key), out, re.MULTILINE)
    value = match.group(1) if match else None
    if value:
        # remove quotes if present
        value = re.sub(r"\"(.*)\"", r"\g<1>", value)
    return value.strip() if value else None


def configure_livepatch_proxy_with_prompts(
    http_proxy: Optional[str] = None,
    https_proxy: Optional[str] = None,
    livepatch_retries: Optional[List[float]] = None,
    assume_yes: bool = False,
) -> None:
    """
    First checks existing values of livepatch proxies. Then prompts if provied
    args are different. Then configures livepatch to use proxies, if prompts
    are passed.

    :param http_proxy: http proxy to be used by livepatch. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by livepatch. If None, it will
                        not be configured
    :param livepatch_retries: Optional list of sleep lengths to apply between
                               livepatch calls
    :param assume_yes: if True, will skip prompts if necessary
    :return: None
    """
    http_proxy_to_set, https_proxy_to_set = util.prompt_for_proxy_changes(
        "livepatch",
        curr_http_proxy=get_config_option_value(HTTP_PROXY_OPTION),
        curr_https_proxy=get_config_option_value(HTTPS_PROXY_OPTION),
        new_http_proxy=http_proxy,
        new_https_proxy=https_proxy,
        assume_yes=assume_yes,
    )
    configure_livepatch_proxy(
        http_proxy_to_set,
        https_proxy_to_set,
        livepatch_retries=livepatch_retries,
    )
