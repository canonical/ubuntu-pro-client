import io
import json
import logging
import os
import socket
from typing import Any, Dict, List, NamedTuple, Optional
from urllib import error, request
from urllib.parse import ParseResult, urlparse

from uaclient import defaults, exceptions, util

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
        raise exceptions.ProxyInvalidUrl(proxy=proxy)

    req = request.Request(test_url, method="HEAD")

    if protocol == "https" and urlparse(proxy).scheme == "https":
        try:
            response = _readurl_pycurl_https_in_https(req, https_proxy=proxy)
        except exceptions.PycurlRequiredError:
            raise
        except exceptions.ProxyAuthenticationFailed:
            raise
        except exceptions.PycurlCACertificatesError:
            raise
        except Exception as e:
            LOG.error(
                'Error trying to use "%s" as pycurl proxy to reach "%s": %s',
                proxy,
                test_url,
                str(e),
            )
            raise exceptions.ProxyNotWorkingError(proxy=proxy)

        if response.code == 200:
            return proxy
        else:
            raise exceptions.ProxyNotWorkingError(proxy=proxy)

    proxy_handler = request.ProxyHandler({protocol: proxy})
    opener = request.build_opener(proxy_handler)

    try:
        opener.open(req)
        return proxy
    except (socket.timeout, error.URLError) as e:
        LOG.error(
            'Error trying to use "%s" as urllib proxy to reach "%s": %s',
            proxy,
            test_url,
            getattr(e, "reason", str(e)),
        )
        raise exceptions.ProxyNotWorkingError(proxy=proxy)


_global_proxy_dict = {}


def configure_web_proxy(
    http_proxy: Optional[str], https_proxy: Optional[str]
) -> None:
    """
    Globally configure pro-client to use http and https proxies.

    - sets global proxy configuration for urllib
    - sets the no_proxy environment variable for the current process
      which gets inherited for all subprocesses
    - sets module variable for use in https-in-https pycurl requests
      this is retrieved later using get_configured_web_proxy

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

    LOG.debug("Setting global proxy dict", extra={"extra": proxy_dict})
    global _global_proxy_dict
    _global_proxy_dict = proxy_dict


def get_configured_web_proxy() -> Dict[str, str]:
    return _global_proxy_dict


def _readurl_urllib(
    req: request.Request, timeout: Optional[int] = None
) -> UnparsedHTTPResponse:
    try:
        resp = request.urlopen(req, timeout=timeout)
    except error.HTTPError as e:
        resp = e
    except error.URLError as e:
        LOG.exception(str(e.reason))
        raise exceptions.ConnectivityError(cause=e, url=req.full_url)

    body = resp.read().decode("utf-8")

    # convert EmailMessage header object to dict with lowercase keys
    headers = {k.lower(): v for k, v, in resp.headers.items()}

    return UnparsedHTTPResponse(
        code=resp.code,
        headers=headers,
        body=body,
    )


def should_use_pycurl(https_proxy, target_url):
    """
    We only want to use pycurl if all of the following are true

    - The target url scheme is https
    - The target host is not in no_proxy
    - An https_proxy is configured either via pro's config or via environment
    - The https_proxy url scheme is https

    urllib.request provides some helpful functions that we re-use here.

    This function also returns the https_proxy to use, since it is calculated
    here anyway.
    """
    parsed_target_url = urlparse(target_url)
    parsed_https_proxy = _parse_https_proxy(https_proxy)
    ret = (
        parsed_target_url.scheme == "https"
        and not request.proxy_bypass(parsed_target_url.hostname)
        and parsed_https_proxy is not None
        and parsed_https_proxy.scheme == "https"
    )
    LOG.debug("Should use pycurl: %r", ret)
    return ret


def _handle_pycurl_error(
    error, url, authentication_error_code, ca_certificates_error_code
):
    code = None
    msg = None
    if len(error.args) > 0:
        code = error.args[0]
    if len(error.args) > 1:
        msg = error.args[1]
    if (
        code == authentication_error_code
        and msg
        and "HTTP code 407 from proxy" in msg
    ):
        raise exceptions.ProxyAuthenticationFailed()
    elif code == ca_certificates_error_code:
        raise exceptions.PycurlCACertificatesError(url=url)
    else:
        raise exceptions.PycurlError(e=error)


def _readurl_pycurl_https_in_https(
    req: request.Request,
    timeout: Optional[int] = None,
    https_proxy: Optional[str] = None,
) -> UnparsedHTTPResponse:
    try:
        import pycurl
    except ImportError:
        raise exceptions.PycurlRequiredError()

    c = pycurl.Curl()

    # Method
    method = req.get_method().upper()
    if method == "GET":
        c.setopt(pycurl.HTTPGET, True)
    elif method == "HEAD":
        c.setopt(pycurl.NOBODY, True)
    elif method == "POST":
        c.setopt(pycurl.POST, True)
        if req.data:
            c.setopt(pycurl.COPYPOSTFIELDS, req.data)
    else:
        raise ValueError(
            'HTTP method "{}" not supported in HTTPS-in-HTTPS mode'.format(
                method
            )
        )

    # Location
    c.setopt(pycurl.URL, req.get_full_url())

    # Headers
    header_str_list = [
        "{}: {}".format(name, val) for name, val in req.header_items()
    ]
    if len(header_str_list) > 0:
        c.setopt(pycurl.HTTPHEADER, header_str_list)

    # Behavior
    c.setopt(pycurl.FOLLOWLOCATION, True)
    c.setopt(pycurl.CAINFO, defaults.SSL_CERTS_PATH)
    if timeout:
        c.setopt(pycurl.TIMEOUT, timeout)

    # Proxy
    if https_proxy:
        parsed_https_proxy = _parse_https_proxy(https_proxy)
        https_proxy = (
            parsed_https_proxy.geturl() if parsed_https_proxy else None
        )
        c.setopt(pycurl.PROXY, https_proxy)
        c.setopt(pycurl.PROXYTYPE, 2)  # 2 == HTTPS
    else:
        LOG.warning("in pycurl request function without an https proxy")

    # Response handling
    body_output = io.BytesIO()
    c.setopt(pycurl.WRITEDATA, body_output)
    headers = {}

    def save_header(header_line):
        header_line = header_line.decode("iso-8859-1")
        if ":" not in header_line:
            return
        name_raw, value_raw = header_line.split(":", 1)
        name = name_raw.strip().lower()
        value = value_raw.strip()
        headers[name] = value

    c.setopt(pycurl.HEADERFUNCTION, save_header)

    # Do it
    try:
        c.perform()
    except pycurl.error as e:
        _handle_pycurl_error(
            e,
            url=req.get_full_url(),
            authentication_error_code=pycurl.E_RECV_ERROR,
            ca_certificates_error_code=pycurl.E_SSL_CACERT_BADFILE,
        )

    code = int(c.getinfo(pycurl.RESPONSE_CODE))
    body = body_output.getvalue().decode("utf-8")

    c.close()

    return UnparsedHTTPResponse(
        code=code,
        headers=headers,
        body=body,
    )


def _parse_https_proxy(https_proxy) -> Optional[ParseResult]:
    if not https_proxy:
        https_proxy = request.getproxies().get("https")
    return urlparse(https_proxy) if https_proxy else None


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

    https_proxy = get_configured_web_proxy().get("https")
    if should_use_pycurl(https_proxy, url):
        resp = _readurl_pycurl_https_in_https(
            req, timeout=timeout, https_proxy=https_proxy
        )
    else:
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
