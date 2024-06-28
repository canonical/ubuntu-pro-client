import datetime
import json
import logging
import os
import re
import sys
import textwrap
import time
from functools import wraps
from typing import Any, Dict, List, Optional, Union  # noqa: F401

from uaclient import exceptions, messages
from uaclient.defaults import CONFIG_FIELD_ENVVAR_ALLOWLIST
from uaclient.types import MessagingOperations

DROPPED_KEY = object()


def replace_top_level_logger_name(name: str) -> str:
    """Replace the name of the root logger from __name__"""
    if name == "":
        return ""
    names = name.split(".")
    names[0] = "ubuntupro"
    return ".".join(names)


LOG = logging.getLogger(replace_top_level_logger_name(__name__))


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
                    new_value = parse_rfc3339_date(
                        value
                    )  # type: Union[str, datetime.datetime]
                except ValueError:
                    # This isn't a string containing a valid ISO 8601 datetime
                    new_value = value
                o[key] = new_value
        return o


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
                    LOG.debug(
                        "%s: Retrying %d more times.", str(e), len(sleeps)
                    )
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
            LOG.debug(
                "Contract value for '%s' changed to '%s'",
                key_path,
                str(new_value),
            )
            deltas[key] = new_value
    for key, value in new_dict.items():
        if key not in orig_dict:
            deltas[key] = value
    return deltas


def prompt_choices(msg: str = "", valid_choices: List[str] = []) -> str:
    """Interactive prompt message, returning a valid choice from msg.

    Expects a structured msg which designates choices with square brackets []
    around the characters which indicate a valid choice.

    Uppercase and lowercase responses are allowed. Loop on invalid choices.

    :return: Valid response character chosen.
    """
    from uaclient import event_logger

    event = event_logger.get_event_logger()
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
        msg = messages.PROMPT_YES_NO
    value = input(msg).lower().strip()
    if value == "":
        return default
    if value in ["y", "yes"]:
        return True
    return False


def is_config_value_true(config: Dict[str, Any], path_to_value: str) -> bool:
    """Check if value parameter can be translated into a boolean 'True' value.

    @param config: A config dict representing
                   /etc/ubuntu-advantange/uaclient.conf
    @param path_to_value: The path from where the value parameter was
                          extracted.
    @return: A boolean value indicating if the value paramater corresponds
             to a 'True' boolean value.
    @raises exceptions.UbuntuProError when the value provide by the
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
        raise exceptions.InvalidBooleanConfigValue(
            path_to_value=path_to_value,
            expected_value="boolean string: true or false",
            value=value_str,
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
    r"(\'token\': \')[^\']+",
    r"(\'userCode\': \')[^\']+",
    r"(\'magic_token=)[^\']+",
    r"(--registration-key=\")[^\"]+",
    r"(--registration-key=\')[^\']+",
    r"(--registration-key=)[^ ]+",
    r"(--registration-key \")[^\"]+",
    r"(--registration-key \')[^\']+",
    r"(--registration-key )[^\s]+",
    r"(-p \")[^\"]+",
    r"(-p \')[^\']+",
    r"(-p )[^\s]+",
]


def redact_sensitive_logs(
    log, redact_regexs: List[str] = REDACT_SENSITIVE_LOGS
) -> str:
    """Redact known sensitive information from log content."""
    redacted_log = log
    for redact_regex in redact_regexs:
        redacted_log = re.sub(redact_regex, r"\g<1><REDACTED>", redacted_log)
    return redacted_log


def handle_message_operations(
    msg_ops: Optional[MessagingOperations], assume_yes: bool
) -> bool:
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
            print(msg_op)
        else:  # Then we are a callable and dict of args
            functor, args = msg_op
            args["assume_yes"] = assume_yes
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
        # https://github.com/canonical/ubuntu-pro-client/issues/859
        message = message.replace("\u2014", "-")

        # Remove our unicode success/failure marks if we aren't going to be
        # writing to a utf-8 output; see
        # https://github.com/canonical/ubuntu-pro-client/issues/1463
        message = message.replace(messages.OKGREEN_CHECK + " ", "")
        message = message.replace(messages.FAIL_X + " ", "")

        # Now we remove any remaining unicode characters from the string
        message = message.encode("ascii", "ignore").decode()

    return message


def get_pro_environment():
    return {
        k: v
        for k, v in os.environ.items()
        if k.lower() in CONFIG_FIELD_ENVVAR_ALLOWLIST
        or k.startswith("UA_FEATURES")
        or k == "UA_CONFIG_FILE"
    }


def depth_first_merge_overlay_dict(base_dict, overlay_dict):
    """Merge the contents of overlay dict into base_dict not only on top-level
    keys, but on all on the depths of the overlay_dict object. For example,
    using these values as entries for the function:

    base_dict = {"a": 1, "b": {"c": 2, "d": 3}}
    overlay_dict = {"b": {"c": 10}}

    Should update base_dict into:

    {"a": 1, "b": {"c": 10, "d": 3}}

    @param base_dict: The dict to be updated
    @param overlay_dict: The dict with information to be added into base_dict
    """

    def update_dict_list(base_values, overlay_values, key):
        merge_id_key_map = {
            "availableResources": "name",
            "resourceEntitlements": "type",
            "overrides": "selector",
        }
        values_to_append = []
        id_key = merge_id_key_map.get(key)
        for overlay_value in overlay_values:
            was_replaced = False
            for base_value_idx, base_value in enumerate(base_values):
                if base_value.get(id_key) == overlay_value.get(id_key):
                    depth_first_merge_overlay_dict(base_value, overlay_value)
                    was_replaced = True

            if not was_replaced:
                values_to_append.append(overlay_value)

        base_values.extend(values_to_append)

    for key, value in overlay_dict.items():
        base_value = base_dict.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            depth_first_merge_overlay_dict(base_dict[key], value)
        elif isinstance(base_value, list) and isinstance(value, list):
            if len(base_value) and isinstance(base_value[0], dict):
                update_dict_list(base_dict[key], value, key=key)
            else:
                """
                Most other lists which aren't lists of dicts are lists of
                strs. Replace that list # with the overlay value."""
                base_dict[key] = value
        else:
            base_dict[key] = value


ARCH_ALIASES = {
    "x86_64": "amd64",
    "i686": "i386",
    "ppc64le": "ppc64el",
    "aarch64": "arm64",
    "armv7l": "armhf",
}


def standardize_arch_name(arch: str) -> str:
    arch_lower = arch.lower()
    return ARCH_ALIASES.get(arch_lower, arch_lower)


def deduplicate_arches(arches: List[str]) -> List[str]:
    deduplicated_arches = set()
    for arch in arches:
        deduplicated_arches.add(standardize_arch_name(arch))
    return sorted(list(deduplicated_arches))


def we_are_currently_root() -> bool:
    return os.getuid() == 0


def set_filename_extension(filename: str, new_extension: str) -> str:
    name, _extension = os.path.splitext(filename)
    return name + "." + new_extension


def create_package_list_str(
    package_list: List[str],
):
    return (
        "\n".join(
            textwrap.wrap(
                " ".join(package_list),
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
                initial_indent="  ",
                subsequent_indent="  ",
            )
        )
        + "\n"
    )
