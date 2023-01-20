import logging
import json
from http.client import HTTPMessage
from typing import Optional, Dict, Tuple, Any, Union, Mapping
from urllib import error, request
from uaclient.config import UAConfig

def libcurl(
    url: str,
    data: Optional[bytes] = None,
    headers: Dict[str, str] = {},
    method: Optional[str] = None,
    timeout: Optional[int] = None,
    potentially_sensitive: bool = True,
) -> Tuple[Any, Union[HTTPMessage, Mapping[str, str]]]:
    from uaclient.util import redact_sensitive_logs, DatetimeAwareJSONDecoder

    if data and not method:
        method = "POST"
    req = request.Request(url, data=data, headers=headers, method=method)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, headers[k]) for k in sorted(headers)]
    )
    logging.debug(
        redact_sensitive_logs(
            "URL [{}]: {}, headers: {{{}}}, data: {}".format(
                method or "GET",
                url,
                sorted_header_str,
                data.decode("utf-8") if data else None,
            )
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
        content = json.loads(content, cls=DatetimeAwareJSONDecoder)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, resp.headers[k]) for k in sorted(resp.headers)]
    )
    debug_msg = "URL [{}] response: {}, headers: {{{}}}, data: {}".format(
        method or "GET", url, sorted_header_str, content
    )
    if potentially_sensitive:
        # For large responses, this is very slow (several minutes)
        debug_msg = redact_sensitive_logs(debug_msg)
    logging.debug(debug_msg)
    if http_error_found:
        raise resp
    return content, resp.headers


def custom(
    url: str,
    data: Optional[bytes] = None,
    headers: Dict[str, str] = {},
    method: Optional[str] = None,
    timeout: Optional[int] = None,
    potentially_sensitive: bool = True,
) -> Tuple[Any, Union[HTTPMessage, Mapping[str, str]]]:
    from uaclient.util import redact_sensitive_logs, DatetimeAwareJSONDecoder
    cfg = UAConfig()

    if data and not method:
        method = "POST"
    req = request.Request(url, data=data, headers=headers, method=method)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, headers[k]) for k in sorted(headers)]
    )
    logging.debug(
        redact_sensitive_logs(
            "URL [{}]: {}, headers: {{{}}}, data: {}".format(
                method or "GET",
                url,
                sorted_header_str,
                data.decode("utf-8") if data else None,
            )
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
        content = json.loads(content, cls=DatetimeAwareJSONDecoder)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, resp.headers[k]) for k in sorted(resp.headers)]
    )
    debug_msg = "URL [{}] response: {}, headers: {{{}}}, data: {}".format(
        method or "GET", url, sorted_header_str, content
    )
    if potentially_sensitive:
        # For large responses, this is very slow (several minutes)
        debug_msg = redact_sensitive_logs(debug_msg)
    logging.debug(debug_msg)
    if http_error_found:
        raise resp
    return content, resp.headers
