import json
import logging
import os
import socket
from http.client import HTTPMessage
from typing import Any, Dict, Mapping, Optional, Tuple, Union
from urllib import error, request
from urllib.parse import urlparse

from uaclient import exceptions, messages, util

UA_NO_PROXY_URLS = ("169.254.169.254", "metadata", "[fd00:ec2::254]")
PROXY_VALIDATION_APT_HTTP_URL = "http://archive.ubuntu.com"
PROXY_VALIDATION_APT_HTTPS_URL = "https://esm.ubuntu.com"
PROXY_VALIDATION_SNAP_HTTP_URL = "http://api.snapcraft.io"
PROXY_VALIDATION_SNAP_HTTPS_URL = "https://api.snapcraft.io"


def is_service_url(url: str) -> bool:
    try:
        parsed_url = urlparse(url)
    except ValueError:
        return False

    if parsed_url.scheme not in ("https", "http"):
        return False

    try:
        parsed_url.port
    except ValueError:
        return False

    return True


def validate_proxy(
    protocol: str, proxy: Optional[str], test_url: str
) -> Optional[str]:
    if not proxy:
        return None

    if not is_service_url(proxy):
        raise exceptions.ProxyInvalidUrl(proxy)

    req = request.Request(test_url, method="HEAD")
    proxy_handler = request.ProxyHandler({protocol: proxy})
    opener = request.build_opener(proxy_handler)

    try:
        opener.open(req)
        return proxy
    except (socket.timeout, error.URLError) as e:
        with util.disable_log_to_console():
            msg = getattr(e, "reason", str(e))
            logging.error(
                messages.ERROR_USING_PROXY.format(
                    proxy=proxy, test_url=test_url, error=msg
                )
            )
        raise exceptions.ProxyNotWorkingError(proxy)


def configure_web_proxy(
    http_proxy: Optional[str], https_proxy: Optional[str]
) -> None:
    """
    Configure urllib to use http and https proxies.

    :param http_proxy: http proxy to be used by urllib. If None, it will
                       not be configured
    :param https_proxy: https proxy to be used by urllib. If None, it will
                        not be configured
    """
    proxy_dict = {}

    if http_proxy:
        proxy_dict["http"] = http_proxy

    if https_proxy:
        proxy_dict["https"] = https_proxy

    # Default no_proxy if absense of NO_PROXY, no_proxy environment vars.
    no_proxy = ",".join(sorted(UA_NO_PROXY_URLS))
    for env_var in ("no_proxy", "NO_PROXY"):
        proxy_value = os.environ.get(env_var)
        if proxy_value:
            # Honor no proxy values and extend UA-specific where absent
            no_proxy = ",".join(
                sorted(
                    set(proxy_value.split(",")).union(set(UA_NO_PROXY_URLS))
                )
            )
    logging.debug("Setting no_proxy: %s", no_proxy)
    os.environ["no_proxy"] = no_proxy
    os.environ["NO_PROXY"] = no_proxy
    if proxy_dict:
        proxy_handler = request.ProxyHandler(proxy_dict)
        opener = request.build_opener(proxy_handler)
        request.install_opener(opener)


def readurl(
    url: str,
    data: Optional[bytes] = None,
    headers: Dict[str, str] = {},
    method: Optional[str] = None,
    timeout: Optional[int] = None,
    log_response_body: bool = True,
) -> Tuple[Any, Union[HTTPMessage, Mapping[str, str]]]:
    if data and not method:
        method = "POST"
    req = request.Request(url, data=data, headers=headers, method=method)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, headers[k]) for k in sorted(headers)]
    )
    logging.debug(
        "URL [{}]: {}, headers: {{{}}}, data: {}".format(
            method or "GET",
            url,
            sorted_header_str,
            data.decode("utf-8") if data else None,
        )
    )
    http_error_found = False
    try:
        resp = request.urlopen(req, timeout=timeout)
        http_error_found = False
    except error.HTTPError as e:
        resp = e
        http_error_found = True
    setattr(resp, "body", resp.read().decode("utf-8"))
    content = resp.body
    if "application/json" in str(resp.headers.get("Content-type", "")):
        content = json.loads(content, cls=util.DatetimeAwareJSONDecoder)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, resp.headers[k]) for k in sorted(resp.headers)]
    )
    debug_msg = "URL [{}] response: {}, headers: {{{}}}".format(
        method or "GET", url, sorted_header_str
    )
    if log_response_body:
        # Due to implicit logging redaction, large responses might take longer
        debug_msg += ", data: {}".format(content)

    logging.debug(debug_msg)
    if http_error_found:
        raise resp
    return content, resp.headers
