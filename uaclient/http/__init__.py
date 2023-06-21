import json
import logging
import os
import socket
from typing import Any, Dict, List, NamedTuple, Optional
from urllib import error, request
from urllib.parse import urlparse

from uaclient import exceptions, messages, util

UA_NO_PROXY_URLS = ("169.254.169.254", "metadata", "[fd00:ec2::254]")
PROXY_VALIDATION_APT_HTTP_URL = "http://archive.ubuntu.com"
PROXY_VALIDATION_APT_HTTPS_URL = "https://esm.ubuntu.com"
PROXY_VALIDATION_SNAP_HTTP_URL = "http://api.snapcraft.io"
PROXY_VALIDATION_SNAP_HTTPS_URL = "https://api.snapcraft.io"

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

UnparsedHTTPResponse = NamedTuple(
    "UnparsedHTTPResponse",
    [
        ("code", int),
        ("headers", Dict[str, str]),
        ("body", str),
    ],
)
HTTPResponse = NamedTuple(
    "HTTPResponse",
    [
        ("code", int),
        ("headers", Dict[str, str]),
        ("body", str),
        ("json_dict", Dict[str, Any]),
        ("json_list", List[Any]),
    ],
)


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
            LOG.error(
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
    LOG.debug("Setting no_proxy: %s", no_proxy)
    os.environ["no_proxy"] = no_proxy
    os.environ["NO_PROXY"] = no_proxy
    if proxy_dict:
        proxy_handler = request.ProxyHandler(proxy_dict)
        opener = request.build_opener(proxy_handler)
        request.install_opener(opener)


def _readurl_urllib(
    req: request.Request, timeout: Optional[int] = None
) -> UnparsedHTTPResponse:
    try:
        resp = request.urlopen(req, timeout=timeout)
    except error.HTTPError as e:
        resp = e
    except error.URLError as e:
        raise exceptions.UrlError(e, url=req.full_url)

    body = resp.read().decode("utf-8")

    # convert EmailMessage header object to dict with lowercase keys
    headers = {k.lower(): v for k, v, in resp.headers.items()}

    return UnparsedHTTPResponse(
        code=resp.code,
        headers=headers,
        body=body,
    )


def readurl(
    url: str,
    data: Optional[bytes] = None,
    headers: Dict[str, str] = {},
    method: Optional[str] = None,
    timeout: Optional[int] = None,
    log_response_body: bool = True,
) -> HTTPResponse:
    if data and not method:
        method = "POST"
    req = request.Request(url, data=data, headers=headers, method=method)

    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, headers[k]) for k in sorted(headers)]
    )
    LOG.debug(
        "URL [{}]: {}, headers: {{{}}}, data: {}".format(
            method or "GET",
            url,
            sorted_header_str,
            data.decode("utf-8") if data else None,
        )
    )

    resp = _readurl_urllib(req, timeout=timeout)

    json_dict = {}
    json_list = []
    if "application/json" in resp.headers.get("content-type", ""):
        json_body = json.loads(resp.body, cls=util.DatetimeAwareJSONDecoder)
        if isinstance(json_body, dict):
            json_dict = json_body
        elif isinstance(json_body, list):
            json_list = json_body

    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, resp.headers[k]) for k in sorted(resp.headers)]
    )
    debug_msg = "URL [{}] response: {}, headers: {{{}}}".format(
        method or "GET", url, sorted_header_str
    )
    if log_response_body:
        # Due to implicit logging redaction, large responses might take longer
        body_to_log = resp.body  # type: Any
        if json_dict:
            body_to_log = json_dict
        elif json_list:
            body_to_log = json_list
        debug_msg += ", data: {}".format(body_to_log)
    LOG.debug(debug_msg)

    return HTTPResponse(
        code=resp.code,
        headers=resp.headers,
        body=resp.body,
        json_dict=json_dict,
        json_list=json_list,
    )
