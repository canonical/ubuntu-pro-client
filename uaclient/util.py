import datetime
import json
import logging
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from errno import ENOENT
from functools import lru_cache, wraps
from http.client import HTTPMessage
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
from urllib import error, request
from urllib.parse import urlparse

from uaclient import event_logger, exceptions, messages, status
from uaclient.types import MessagingOperations

REBOOT_FILE_CHECK_PATH = "/var/run/reboot-required"
REBOOT_PKGS_FILE_PATH = "/var/run/reboot-required.pkgs"
ETC_MACHINE_ID = "/etc/machine-id"
DBUS_MACHINE_ID = "/var/lib/dbus/machine-id"
DROPPED_KEY = object()

# N.B. this relies on the version normalisation we perform in get_platform_info
REGEX_OS_RELEASE_VERSION = r"(?P<release>\d+\.\d+) (LTS )?\((?P<series>\w+).*"

UA_NO_PROXY_URLS = ("169.254.169.254", "metadata", "[fd00:ec2::254]")
PROXY_VALIDATION_APT_HTTP_URL = "http://archive.ubuntu.com"
PROXY_VALIDATION_APT_HTTPS_URL = "https://esm.ubuntu.com"
PROXY_VALIDATION_SNAP_HTTP_URL = "http://api.snapcraft.io"
PROXY_VALIDATION_SNAP_HTTPS_URL = "https://api.snapcraft.io"

OVERRIDE_SELECTOR_WEIGHTS = {"series_overrides": 1, "series": 2, "cloud": 3}

event = event_logger.get_event_logger()


class LogFormatter(logging.Formatter):

    FORMATS = {
        logging.ERROR: "ERROR: %(message)s",
        logging.DEBUG: "DEBUG: %(message)s",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        return logging.Formatter(log_fmt).format(record)


class DatetimeAwareJSONEncoder(json.JSONEncoder):
    """A json.JSONEncoder subclass that writes out isoformat'd datetimes."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)


class DatetimeAwareJSONDecoder(json.JSONDecoder):
    """
    A JSONDecoder that parses some ISO datetime strings to datetime objects.

    Important note: the "some" is because we seem to only be able extend
    Python's json library in a way that lets us convert string values within
    JSON objects (e.g. '{"lastModified": "2019-07-25T14:35:51"}'). Strings
    outside of JSON objects (e.g. '"2019-07-25T14:35:51"') will not be passed
    through our decoder.

    (N.B. This will override any object_hook specified using arguments to it,
    or used in load or loads calls that specify this as the cls.)
    """

    def __init__(self, *args, **kwargs):
        if "object_hook" in kwargs:
            kwargs.pop("object_hook")
        super().__init__(*args, object_hook=self.object_hook, **kwargs)

    @staticmethod
    def object_hook(o):
        for key, value in o.items():
            if isinstance(value, str):
                try:
                    new_value = parse_rfc3339_date(value)
                except ValueError:
                    # This isn't a string containing a valid ISO 8601 datetime
                    new_value = value
                o[key] = new_value
        return o


def _get_override_weight(
    override_selector: Dict[str, str], selector_values: Dict[str, str]
) -> int:
    override_weight = 0
    for selector, value in override_selector.items():
        if (selector, value) not in selector_values.items():
            return 0
        override_weight += OVERRIDE_SELECTOR_WEIGHTS[selector]

    return override_weight


def _select_overrides(
    entitlement: Dict[str, Any], series_name: str, cloud_type: str
) -> Dict[int, Dict[str, Any]]:
    overrides = {}

    selector_values = {"series": series_name, "cloud": cloud_type}

    series_overrides = entitlement.pop("series", {}).pop(series_name, {})
    if series_overrides:
        overrides[
            OVERRIDE_SELECTOR_WEIGHTS["series_overrides"]
        ] = series_overrides

    general_overrides = entitlement.pop("overrides", [])
    for override in general_overrides:
        weight = _get_override_weight(
            override.pop("selector"), selector_values
        )
        if weight:
            overrides[weight] = override

    return overrides


def apply_contract_overrides(
    orig_access: Dict[str, Any], series: str = None
) -> None:
    """Apply series-specific overrides to an entitlement dict.

    This function mutates orig_access dict by applying any series-overrides to
    the top-level keys under 'entitlement'. The series-overrides are sparse
    and intended to supplement existing top-level dict values. So, sub-keys
    under the top-level directives, obligations and affordance sub-key values
    will be preserved if unspecified in series-overrides.

    To more clearly indicate that orig_access in memory has already had
    the overrides applied, the 'series' key is also removed from the
    orig_access dict.

    :param orig_access: Dict with original entitlement access details
    """
    from uaclient.clouds.identity import get_cloud_type

    if not all([isinstance(orig_access, dict), "entitlement" in orig_access]):
        raise RuntimeError(
            'Expected entitlement access dict. Missing "entitlement" key:'
            " {}".format(orig_access)
        )

    series_name = get_platform_info()["series"] if series is None else series
    cloud_type, _ = get_cloud_type()
    orig_entitlement = orig_access.get("entitlement", {})

    overrides = _select_overrides(orig_entitlement, series_name, cloud_type)

    for _weight, overrides_to_apply in sorted(overrides.items()):
        for key, value in overrides_to_apply.items():
            current = orig_access["entitlement"].get(key)
            if isinstance(current, dict):
                # If the key already exists and is a dict,
                # update that dict using the override
                current.update(value)
            else:
                # Otherwise, replace it wholesale
                orig_access["entitlement"][key] = value


def del_file(path: str) -> None:
    try:
        os.unlink(path)
    except OSError as e:
        if e.errno != ENOENT:
            raise e


@contextmanager
def disable_log_to_console():
    """
    A context manager that disables logging to console in its body

    N.B. This _will not_ disable console logging if it finds the console
    handler is configured at DEBUG level; the assumption is that this means we
    want as much output as possible, even if it risks duplication.

    This context manager will allow us to gradually move away from using the
    logging framework for user-facing output, by applying it to parts of the
    codebase piece-wise. (Once the conversion is complete, we should have no
    further use for it and it can be removed.)

    (Note that the @contextmanager decorator also allows this function to be
    used as a decorator.)
    """
    potential_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if handler.name == "ua-console"
    ]
    if not potential_handlers:
        # We didn't find a handler, so execute the body as normal then end
        # execution
        logging.debug("disable_log_to_console: no console handler found")
        yield
        return

    console_handler = potential_handlers[0]
    old_level = console_handler.level
    if old_level == logging.DEBUG:
        yield
        return

    console_handler.setLevel(1000)
    try:
        yield
    finally:
        console_handler.setLevel(old_level)


def retry(exception, retry_sleeps):
    """Decorator to retry on exception for retry_sleeps.

    @param retry_sleeps: List of sleep lengths to apply between
       retries. Specifying a list of [0.5, 1] tells subp to retry twice
       on failure; sleeping half a second before the first retry and 1 second
       before the second retry.
    @param exception: The exception class to catch and retry for the provided
       retry_sleeps. Any other exception types will not be caught by the
       decorator.
    """

    def wrapper(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            sleeps = retry_sleeps.copy()
            while True:
                try:
                    return f(*args, **kwargs)
                except exception as e:
                    if not sleeps:
                        raise e
                    retry_msg = " Retrying %d more times." % len(sleeps)
                    logging.debug(str(e) + retry_msg)
                    time.sleep(sleeps.pop(0))

        return decorator

    return wrapper


def get_dict_deltas(
    orig_dict: Dict[str, Any], new_dict: Dict[str, Any], path: str = ""
) -> Dict[str, Any]:
    """Return a dictionary of delta between orig_dict and new_dict."""
    deltas = {}  # type: Dict[str, Any]
    for key, value in orig_dict.items():
        new_value = new_dict.get(key, DROPPED_KEY)
        key_path = key if not path else path + "." + key
        if isinstance(value, dict):
            if key in new_dict:
                sub_delta = get_dict_deltas(
                    value, new_dict[key], path=key_path
                )
                if sub_delta:
                    deltas[key] = sub_delta
            else:
                deltas[key] = DROPPED_KEY
        elif value != new_value:
            log = (
                "Contract value for '"
                + key_path
                + "' changed to '"
                + str(new_value)
                + "'"
            )
            logging.debug(redact_sensitive_logs(log))
            deltas[key] = new_value
    for key, value in new_dict.items():
        if key not in orig_dict:
            deltas[key] = value
    return deltas


@lru_cache(maxsize=None)
def get_machine_id(cfg) -> str:
    """Get system's unique machine-id or create our own in data_dir."""
    # Generate, cache our own uuid if not present in config or on the system
    # Docker images do not define ETC_MACHINE_ID or DBUS_MACHINE_ID on trusty
    # per Issue: #489

    if cfg.machine_token:
        cfg_machine_id = cfg.machine_token.get("machineTokenInfo", {}).get(
            "machineId"
        )
        if cfg_machine_id:
            return cfg_machine_id

    fallback_machine_id_file = cfg.data_path("machine-id")

    for path in [ETC_MACHINE_ID, DBUS_MACHINE_ID, fallback_machine_id_file]:
        if os.path.exists(path):
            content = load_file(path).rstrip("\n")
            if content:
                return content
    machine_id = str(uuid.uuid4())
    write_file(fallback_machine_id_file, machine_id)
    return machine_id


@lru_cache(maxsize=None)
def get_platform_info() -> Dict[str, str]:
    """
    Returns a dict of platform information.

    N.B. This dict is sent to the contract server, which requires the
    distribution, type and release keys.
    """
    os_release = parse_os_release()
    platform_info = {
        "distribution": os_release.get("NAME", "UNKNOWN"),
        "type": "Linux",
    }

    version = os_release["VERSION"]
    if ", " in version:
        # Fix up trusty's version formatting
        version = "{} ({})".format(*version.split(", "))
    # Strip off an LTS point release (14.04.1 LTS -> 14.04 LTS)
    version = re.sub(r"\.\d LTS", " LTS", version)
    platform_info["version"] = version

    match = re.match(REGEX_OS_RELEASE_VERSION, version)
    if not match:
        raise RuntimeError(
            "Could not parse /etc/os-release VERSION: {} (modified to"
            " {})".format(os_release["VERSION"], version)
        )
    match_dict = match.groupdict()
    platform_info.update(
        {
            "release": match_dict["release"],
            "series": match_dict["series"].lower(),
        }
    )

    uname = os.uname()
    platform_info["kernel"] = uname.release
    out, _err = subp(["dpkg", "--print-architecture"])
    platform_info["arch"] = out.strip()

    return platform_info


@lru_cache(maxsize=None)
def is_lts(series: str) -> bool:
    out, _err = subp(["/usr/bin/ubuntu-distro-info", "--supported-esm"])
    return series in out


@lru_cache(maxsize=None)
def is_active_esm(series: str) -> bool:
    """Return True when Ubuntu series supports ESM and is actively in ESM."""
    if not is_lts(series):
        return False
    if series == "trusty":
        return True  # Trusty doesn't have a --series param
    out, _err = subp(
        ["/usr/bin/ubuntu-distro-info", "--series", series, "-yeol"]
    )
    return int(out) <= 0


@lru_cache(maxsize=None)
def is_container(run_path: str = "/run") -> bool:
    """Checks to see if this code running in a container of some sort"""

    # We may mistake schroot environments for containers by just relying
    # in the other checks present in that function. To guarantee that
    # we do not identify a schroot as a container, we are explicitly
    # using the 'ischroot' command here.
    try:
        subp(["ischroot"])
        return False
    except exceptions.ProcessExecutionError:
        pass

    try:
        subp(["systemd-detect-virt", "--quiet", "--container"])
        return True
    except (IOError, OSError):
        pass

    for filename in ("container_type", "systemd/container"):
        path = os.path.join(run_path, filename)
        if os.path.exists(path):
            return True
    return False


def is_exe(path: str) -> bool:
    # return boolean indicating if path exists and is executable.
    return os.path.isfile(path) and os.access(path, os.X_OK)


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


def load_file(filename: str, decode: bool = True) -> str:
    """Read filename and decode content."""
    logging.debug("Reading file: %s", filename)
    with open(filename, "rb") as stream:
        content = stream.read()
    return content.decode("utf-8")


@lru_cache(maxsize=None)
def parse_os_release(release_file: Optional[str] = None) -> Dict[str, str]:
    if not release_file:
        release_file = "/etc/os-release"
    data = {}
    for line in load_file(release_file).splitlines():
        key, value = line.split("=", 1)
        if value:
            data[key] = value.strip().strip('"')
    return data


def prompt_choices(msg: str = "", valid_choices: List[str] = []) -> str:
    """Interactive prompt message, returning a valid choice from msg.

    Expects a structured msg which designates choices with square brackets []
    around the characters which indicate a valid choice.

    Uppercase and lowercase responses are allowed. Loop on invalid choices.

    :return: Valid response character chosen.
    """
    value = ""
    error_msg = "{} is not one of: {}".format(
        value, ", ".join([choice.upper() for choice in valid_choices])
    )
    while True:
        event.info(msg)
        value = input("> ").lower()
        if value in valid_choices:
            break
        event.info(error_msg)
    return value


def prompt_for_confirmation(
    msg: str = "", assume_yes: bool = False, default: bool = False
) -> bool:
    """
    Display a confirmation prompt, returning a bool indicating the response

    :param msg: String custom prompt text to emit from input call.
    :param assume_yes: Boolean set True to skip confirmation input and return
        True.
    :param default: Boolean to return when user doesn't enter any text

    This function will only prompt a single time, and defaults to "no" (i.e. it
    returns False).
    """
    if assume_yes:
        return True
    if not msg:
        msg = status.PROMPT_YES_NO
    value = input(msg).lower().strip()
    if value == "":
        return default
    if value in ["y", "yes"]:
        return True
    return False


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
) -> Tuple[Any, Union[HTTPMessage, Mapping[str, str]]]:
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
        content = json.loads(content)
    sorted_header_str = ", ".join(
        ["'{}': '{}'".format(k, resp.headers[k]) for k in sorted(resp.headers)]
    )
    logging.debug(
        redact_sensitive_logs(
            "URL [{}] response: {}, headers: {{{}}}, data: {}".format(
                method or "GET", url, sorted_header_str, content
            )
        )
    )
    if http_error_found:
        raise resp
    return content, resp.headers


def _subp(
    args: Sequence[str],
    rcs: Optional[List[int]] = None,
    capture: bool = False,
    timeout: Optional[float] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[str, str]:
    """Run a command and return a tuple of decoded stdout, stderr.

    @param args: A list of arguments to feed to subprocess.Popen
    @param rcs: A list of allowed return_codes. If returncode not in rcs
        raise a ProcessExecutionError.
    @param capture: Boolean set True to log the command and response.
    @param timeout: Optional float indicating number of seconds to wait for
        subp to return.
    @param env: Optional dictionary of environment variable to pass to Popen.

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    @raises subprocess.TimeoutError when timeout specified and the command
        exceeds that number of seconds.
    """
    bytes_args = [
        x if isinstance(x, bytes) else x.encode("utf-8") for x in args
    ]
    if env:
        env.update(os.environ)
    if rcs is None:
        rcs = [0]
    redacted_cmd = redact_sensitive_logs(" ".join(args))
    try:
        proc = subprocess.Popen(
            bytes_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
        )
        (out, err) = proc.communicate(timeout=timeout)
    except OSError:
        try:
            raise exceptions.ProcessExecutionError(
                cmd=redacted_cmd,
                exit_code=proc.returncode,
                stdout=out.decode("utf-8"),
                stderr=err.decode("utf-8"),
            )
        except UnboundLocalError:
            raise exceptions.ProcessExecutionError(cmd=redacted_cmd)
    if proc.returncode not in rcs:
        raise exceptions.ProcessExecutionError(
            cmd=redacted_cmd,
            exit_code=proc.returncode,
            stdout=out.decode("utf-8"),
            stderr=err.decode("utf-8"),
        )
    if capture:
        logging.debug(
            "Ran cmd: %s, rc: %s stderr: %s",
            redacted_cmd,
            proc.returncode,
            err,
        )
    return out.decode("utf-8"), err.decode("utf-8")


def subp(
    args: Sequence[str],
    rcs: Optional[List[int]] = None,
    capture: bool = False,
    timeout: Optional[float] = None,
    retry_sleeps: Optional[List[float]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[str, str]:
    """Run a command and return a tuple of decoded stdout, stderr.

     @param subp: A list of arguments to feed to subprocess.Popen
     @param rcs: A list of allowed return_codes. If returncode not in rcs
         raise a ProcessExecutionError.
     @param capture: Boolean set True to log the command and response.
     @param timeout: Optional float indicating number of seconds to wait for a
         subp call to return.
     @param retry_sleeps: Optional list of sleep lengths to apply between
        retries. Specifying a list of [0.5, 1] instructs subp to retry twice
        on failure; sleeping half a second before the first retry and 1 second
        before the next retry.
     @param env: Optional dictionary of environment variables to provide to
        subp.

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    @raises subprocess.TimeoutError when timeout specified and the command
        exceeds that number of seconds.
    """
    retry_sleeps = retry_sleeps.copy() if retry_sleeps is not None else None
    while True:
        try:
            out, err = _subp(args, rcs, capture, timeout, env=env)
            break
        except exceptions.ProcessExecutionError as e:
            if capture:
                logging.debug(redact_sensitive_logs(str(e)))
                msg = "Stderr: {}\nStdout: {}".format(e.stderr, e.stdout)
                logging.warning(redact_sensitive_logs(msg))
            if not retry_sleeps:
                raise
            retry_msg = " Retrying %d more times." % len(retry_sleeps)
            logging.debug(redact_sensitive_logs(str(e) + retry_msg))
            time.sleep(retry_sleeps.pop(0))
    return out, err


def which(program: str) -> Optional[str]:
    """Find whether the provided program is executable in our PATH"""
    if os.path.sep in program:
        # if program had a '/' in it, then do not search PATH
        if is_exe(program):
            return program
    paths = [
        p.strip('"') for p in os.environ.get("PATH", "").split(os.pathsep)
    ]
    normalized_paths = [os.path.abspath(p) for p in paths]
    for path in normalized_paths:
        program_path = os.path.join(path, program)
        if is_exe(program_path):
            return program_path
    return None


def write_file(filename: str, content: str, mode: int = 0o644) -> None:
    """Write content to the provided filename encoding it if necessary.

    @param filename: The full path of the file to write.
    @param content: The content to write to the file.
    @param mode: The filesystem mode to set on the file.
    """
    logging.debug("Writing file: %s", filename)
    with open(filename, "wb") as fh:
        fh.write(content.encode("utf-8"))
        fh.flush()
    os.chmod(filename, mode)


def remove_file(file_path: str) -> None:
    """Remove a file if it exists, logging a message about removal."""
    if os.path.exists(file_path):
        logging.debug("Removing file: %s", file_path)
        os.unlink(file_path)


def is_config_value_true(config: Dict[str, Any], path_to_value: str):
    """Check if value parameter can be translated into a boolean 'True' value.

    @param config: A config dict representing
                   /etc/ubuntu-advantange/uaclient.conf
    @param path_to_value: The path from where the value parameter was
                          extracted.
    @return: A boolean value indicating if the value paramater corresponds
             to a 'True' boolean value.
    @raises exceptions.UserFacingError when the value provide by the
            path_to_value parameter can not be translated into either
            a 'False' or 'True' boolean value.
    """
    value = config
    default_value = {}  # type: Any
    paths = path_to_value.split(".")
    leaf_value = paths[-1]
    for key in paths:
        if key == leaf_value:
            default_value = "false"

        if isinstance(value, dict):
            value = value.get(key, default_value)
        else:
            return False

    value_str = str(value)
    if value_str.lower() == "true":
        return True
    elif value_str.lower() == "false":
        return False
    else:
        raise exceptions.UserFacingError(
            messages.ERROR_INVALID_CONFIG_VALUE.format(
                path_to_value=path_to_value,
                expected_value="boolean string: true or false",
                value=value_str,
            )
        )


REDACT_SENSITIVE_LOGS = [
    r"(Bearer )[^\']+",
    r"(\'attach\', \')[^\']+",
    r"(\'machineToken\': \')[^\']+",
    r"(\'token\': \')[^\']+",
    r"(\'X-aws-ec2-metadata-token\': \')[^\']+",
    r"(.*\[PUT\] response.*api/token,.*data: ).*",
    r"(https://bearer:)[^\@]+",
    r"(/snap/bin/canonical-livepatch\s+enable\s+)[^\s]+",
    r"(Contract\s+value\s+for\s+'resourceToken'\s+changed\s+to\s+).*",
    r"(\'resourceToken\': \')[^\']+",
    r"(\'contractToken\': \')[^\']+",
    r"(https://contracts.canonical.com/v1/resources/livepatch\?token=)[^\s]+",
    r"(\"identityToken\": \")[^\"]+",
    r"(response:\s+http://metadata/computeMetadata/v1/instance/"
    "service-accounts.*data: ).*",
]


def redact_sensitive_logs(
    log, redact_regexs: List[str] = REDACT_SENSITIVE_LOGS
) -> str:
    """Redact known sensitive information from log content."""
    redacted_log = log
    for redact_regex in redact_regexs:
        redacted_log = re.sub(redact_regex, r"\g<1><REDACTED>", redacted_log)
    return redacted_log


def should_reboot(
    installed_pkgs: Optional[Set[str]] = None,
    installed_pkgs_regex: Optional[Set[str]] = None,
) -> bool:
    """Check if the system needs to be rebooted.

    :param installed_pkgs: If provided, verify if the any packages in
        the list are present on /var/run/reboot-required.pkgs. If that
        param is provided, we will only return true if we have the
        reboot-required marker file and any package in reboot-required.pkgs
        file. When both installed_pkgs and installed_pkgs_regex are
        provided, they act as an OR, so only one of the two lists must have
        a match to return True.
    :param installed_pkgs_regex: If provided, verify if the any regex in
        the list matches any line in /var/run/reboot-required.pkgs. If that
        param is provided, we will only return true if we have the
        reboot-required marker file and any match in reboot-required.pkgs
        file. When both installed_pkgs and installed_pkgs_regex are
        provided, they act as an OR, so only one of the two lists must have
        a match to return True.
    """

    # If the reboot marker file doesn't exist, we don't even
    # need to look at the installed_pkgs param
    if not os.path.exists(REBOOT_FILE_CHECK_PATH):
        return False

    # If there is no installed_pkgs to check, we will rely only
    # on the existence of the reboot marker file
    if installed_pkgs is None and installed_pkgs_regex is None:
        return True

    try:
        reboot_required_pkgs = set(
            load_file(REBOOT_PKGS_FILE_PATH).split("\n")
        )
    except FileNotFoundError:
        # If the file doesn't exist, we will default to the
        # reboot  marker file
        return True

    if installed_pkgs is not None:
        if len(installed_pkgs.intersection(reboot_required_pkgs)) != 0:
            return True

    if installed_pkgs_regex is not None:
        for pkg_name in reboot_required_pkgs:
            for pkg_regex in installed_pkgs_regex:
                if re.search(pkg_regex, pkg_name):
                    return True

    return False


def is_installed(package_name: str) -> bool:
    try:
        out, _ = subp(["dpkg", "-l", package_name])
        return "ii  {} ".format(package_name) in out
    except exceptions.ProcessExecutionError:
        return False


def handle_message_operations(msg_ops: Optional[MessagingOperations],) -> bool:
    """Emit messages to the console for user interaction

    :param msg_op: A list of strings or tuples. Any string items are printed.
        Any tuples will contain a callable and a dict of args to pass to the
        callable. Callables are expected to return True on success and
        False upon failure.

    :return: True upon success, False on failure.
    """
    if not msg_ops:
        return True

    for msg_op in msg_ops:
        if isinstance(msg_op, str):
            event.info(msg_op)
        else:  # Then we are a callable and dict of args
            functor, args = msg_op
            if not functor(**args):
                return False
    return True


def parse_rfc3339_date(dt_str: str) -> datetime.datetime:
    """
    Parse a datestring in rfc3339 format. Originally written for compatibility
    with golang's time.MarshalJSON function. Also handles output of pythons
    isoformat datetime method.

    This drops subseconds.

    :param dt_str: a date string in rfc3339 format

    :return: datetime.datetime object of time represented by dt_str
    """
    # remove sub-seconds
    # Examples:
    #   Before: "2001-02-03T04:05:06.123456"
    #   After: "2001-02-03T04:05:06"
    #   Before: "2001-02-03T04:05:06.123456Z"
    #   After: "2001-02-03T04:05:06Z"
    #   Before: "2001-02-03T04:05:06.123456+09:00"
    #   After: "2001-02-03T04:05:06+09:00"
    dt_str_without_subseconds = re.sub(
        r"(\d{2}:\d{2}:\d{2})\.\d+", r"\g<1>", dt_str
    )
    # if there is no timezone info, assume UTC
    # Examples:
    #   Before: "2001-02-03T04:05:06"
    #   After: "2001-02-03T04:05:06Z"
    #   Before: "2001-02-03T04:05:06Z"
    #   After: "2001-02-03T04:05:06Z"
    #   Before: "2001-02-03T04:05:06+09:00"
    #   After: "2001-02-03T04:05:06+09:00"
    dt_str_with_z = re.sub(
        r"(\d{2}:\d{2}:\d{2})$", r"\g<1>Z", dt_str_without_subseconds
    )
    # replace Z with offset for UTC
    # Examples:
    #   Before: "2001-02-03T04:05:06Z"
    #   After: "2001-02-03T04:05:06+00:00"
    #   Before: "2001-02-03T04:05:06+09:00"
    #   After: "2001-02-03T04:05:06+09:00"
    dt_str_without_z = dt_str_with_z.replace("Z", "+00:00")
    # change offset format to not include colon `:`
    # Examples:
    #   Before: "2001-02-03T04:05:06+00:00"
    #   After: "2001-02-03T04:05:06+0000"
    #   Before: "2001-02-03T04:05:06+09:00"
    #   After: "2001-02-03T04:05:06+0900"
    dt_str_with_pythonish_tz = re.sub(
        r"(-|\+)(\d{2}):(\d{2})$", r"\g<1>\g<2>\g<3>", dt_str_without_z
    )
    return datetime.datetime.strptime(
        dt_str_with_pythonish_tz, "%Y-%m-%dT%H:%M:%S%z"
    )


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
        with disable_log_to_console():
            msg = getattr(e, "reason", str(e))
            logging.error(
                messages.ERROR_USING_PROXY.format(
                    proxy=proxy, test_url=test_url, error=msg
                )
            )
        raise exceptions.ProxyNotWorkingError(proxy)


def handle_unicode_characters(message: str) -> str:
    """
    Verify if the system can output unicode characters and if not,
    remove those characters from the message string.
    """
    if (
        sys.stdout.encoding is None
        or "UTF-8" not in sys.stdout.encoding.upper()
    ):
        # Replace our Unicode dash with an ASCII dash if we aren't going to be
        # writing to a utf-8 output; see
        # https://github.com/CanonicalLtd/ubuntu-advantage-client/issues/859
        message = message.replace("\u2014", "-")

        # Remove our unicode success/failure marks if we aren't going to be
        # writing to a utf-8 output; see
        # https://github.com/CanonicalLtd/ubuntu-advantage-client/issues/1463
        message = message.replace(messages.OKGREEN_CHECK + " ", "")
        message = message.replace(messages.FAIL_X + " ", "")

    return message
