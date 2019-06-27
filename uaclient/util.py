from errno import ENOENT
import json
import logging
import os
import re
import subprocess
import time
from urllib import error, request
from urllib.parse import urlparse
import uuid
from contextlib import contextmanager
from http.client import HTTPMessage  # noqa: F401

try:
    from typing import (  # noqa: F401
        Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union,
    )
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


ETC_MACHINE_ID = '/etc/machine-id'
DBUS_MACHINE_ID = '/var/lib/dbus/machine-id'
DROPPED_KEY = object()


class LogFormatter(logging.Formatter):

    FORMATS = {
        logging.ERROR: 'ERROR: %(message)s',
        logging.DEBUG: 'DEBUG: %(message)s',
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, '%(message)s')
        return logging.Formatter(log_fmt).format(record)


class UrlError(IOError):

    def __init__(self, cause: error.URLError, code: 'Optional[int]' = None,
                 headers: 'Optional[Dict[str, str]]' = None,
                 url: 'Optional[str]' = None):
        super().__init__(str(cause))
        self.code = code
        self.headers = headers
        if self.headers is None:
            self.headers = {}
        self.url = url


class ProcessExecutionError(IOError):

    def __init__(self, cmd: str, exit_code: 'Optional[int]' = None,
                 stdout: str = '', stderr: str = '') -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        if not exit_code:
            message_tmpl = "Invalid command specified '{cmd}'."
        else:
            message_tmpl = (
                "Failed running command '{cmd}' [exit({exit_code})]."
                " Message: {stderr}")
        super().__init__(
            message_tmpl.format(cmd=cmd, stderr=stderr, exit_code=exit_code))


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
    codebase piece-wise.  (Once the conversion is complete, we should have no
    further use for it and it can be removed.)

    (Note that the @contextmanager decorator also allows this function to be
    used as a decorator.)
    """
    potential_handlers = [handler for handler in logging.getLogger().handlers
                          if handler.name == 'console']
    if not potential_handlers:
        # We didn't find a handler, so execute the body as normal then end
        # execution
        logging.debug('disable_log_to_console: no console handler found')
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


def get_dict_deltas(orig_dict: 'Dict[str, Any]', new_dict: 'Dict[str, Any]',
                    path: str = '') -> 'Dict[str, Any]':
    """Return a dictionary of delta between orig_dict and new_dict."""
    deltas = {}  # type: Dict[str, Any]
    for key, value in orig_dict.items():
        new_value = new_dict.get(key, DROPPED_KEY)
        key_path = key if not path else path + '.' + key
        if isinstance(value, dict):
            if key in new_dict:
                sub_delta = get_dict_deltas(
                    value, new_dict[key], path=key_path)
                if sub_delta:
                    deltas[key] = sub_delta
            else:
                deltas[key] = DROPPED_KEY
        elif value != new_value:
            logging.debug(
                "Contract value for '%s' changed to '%s'", key_path, new_value)
            deltas[key] = new_value
    for key, value in new_dict.items():
        if key not in orig_dict:
            deltas[key] = value
    return deltas


def is_container(run_path: str = '/run') -> bool:
    """Checks to see if this code running in a container of some sort"""
    try:
        subp(['systemd-detect-virt', '--quiet', '--container'])
        return True
    except (IOError, OSError):
        pass
    for filename in ('container_type', 'systemd/container'):
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
    if parsed_url.scheme not in ('https', 'http'):
        return False
    return True


def load_file(filename: str, decode: bool = True) -> str:
    """Read filename and decode content."""
    logging.debug('Reading file: %s', filename)
    with open(filename, 'rb') as stream:
        content = stream.read()
    return content.decode('utf-8')


def maybe_parse_json(content: str) -> 'Optional[Any]':
    """Attempt to parse json content.

    @return: Structured content on success and None on failure.
    """
    try:
        return json.loads(content)
    except ValueError:
        return None


def readurl(url: str, data: 'Optional[bytes]' = None,
            headers: 'Dict[str, str]' = {}, method: 'Optional[str]' = None
            ) -> 'Tuple[Any, Union[HTTPMessage, Mapping[str, str]]]':
    if data and not method:
        method = 'POST'
    req = request.Request(url, data=data, headers=headers, method=method)
    if data:
        data = maybe_parse_json(data.decode('utf-8'))
    logging.debug(
        'URL [%s]: %s, headers: %s, data: %s',
        method or 'GET', url, headers, data)
    resp = request.urlopen(req)
    content = resp.read().decode('utf-8')
    if 'application/json' in str(resp.headers.get('Content-type', '')):
        content = json.loads(content)
    logging.debug(
        'URL [%s] response: %s, headers: %s, data: %s',
        method or 'GET', url, resp.headers, content)
    return content, resp.headers


def _subp(args: 'Sequence[str]',
          rcs: 'Optional[List[int]]' = None,
          capture: bool = False,
          timeout: 'Optional[float]' = None) -> 'Tuple[str, str]':
    """Run a command and return a tuple of decoded stdout, stderr.

    @param args: A list of arguments to feed to subprocess.Popen
    @param rcs: A list of allowed return_codes. If returncode not in rcs
        raise a ProcessExecutionError.
    @param capture: Boolean set True to log the command and response.
    @param timeout: Optional float indicating number of seconds to wait for
        subp to return.

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    @raises subprocess.TimeoutError when timeout specified and the command
        exceeds that number of seconds.
    """
    bytes_args = [x if isinstance(x, bytes) else x.encode("utf-8")
                  for x in args]
    if rcs is None:
        rcs = [0]
    try:
        proc = subprocess.Popen(
            bytes_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate(timeout=timeout)
    except OSError:
        try:
            raise ProcessExecutionError(
                cmd=' '.join(args), exit_code=proc.returncode,
                stdout=out.decode('utf-8'), stderr=err.decode('utf-8'))
        except UnboundLocalError:
            raise ProcessExecutionError(cmd=' '.join(args))
    if proc.returncode not in rcs:
        raise ProcessExecutionError(
            cmd=' '.join(args), exit_code=proc.returncode,
            stdout=out.decode('utf-8'), stderr=err.decode('utf-8'))
    if capture:
        logging.debug('Ran cmd: %s, rc: %s stderr: %s',
                      ' '.join(args), proc.returncode, err)
    return out.decode('utf-8'), err.decode('utf-8')


def subp(args: 'Sequence[str]', rcs: 'Optional[List[int]]' = None,
         capture: bool = False, timeout: 'Optional[float]' = None,
         retry_sleeps: 'Optional[List[float]]' = None) -> 'Tuple[str, str]':
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

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    @raises subprocess.TimeoutError when timeout specified and the command
        exceeds that number of seconds.
    """
    retry_sleeps = retry_sleeps.copy() if retry_sleeps is not None else None
    while True:
        try:
            out, err = _subp(args, rcs, capture, timeout)
            break
        except ProcessExecutionError as e:
            if capture:
                logging.debug(str(e))
            if not retry_sleeps:
                raise
            logging.debug(
                str(e) + " Retrying %d more times.", len(retry_sleeps))
            time.sleep(retry_sleeps.pop(0))
    return out, err


def which(program: str) -> 'Optional[str]':
    """Find whether the provided program is executable in our PATH"""
    if os.path.sep in program:
        # if program had a '/' in it, then do not search PATH
        if is_exe(program):
            return program
    paths = [p.strip('"') for p in
             os.environ.get("PATH", "").split(os.pathsep)]
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
    @param omode: The open mode used when opening the file (w, wb, a, etc.)
    """
    logging.debug('Writing file: %s', filename)
    with open(filename, 'wb') as fh:
        fh.write(content.encode('utf-8'))
        fh.flush()
    os.chmod(filename, mode)


def parse_os_release(release_file: 'Optional[str]' = None) -> 'Dict[str, str]':
    if not release_file:
        release_file = '/etc/os-release'
    data = {}
    for line in load_file(release_file).splitlines():
        key, value = line.split('=', 1)
        if value:
            data[key] = value.strip().strip('"')
    return data


# N.B. this relies on the version normalisation we perform in get_platform_info
REGEX_OS_RELEASE_VERSION = r'(?P<release>\d+\.\d+) (LTS )?\((?P<series>\w+).*'


def get_platform_info() -> 'Dict[str, str]':
    """
    Returns a dict of platform information.

    N.B. This dict is sent to the contract server, which requires the
    distribution, type and release keys.
    """
    os_release = parse_os_release()
    platform_info = {
        'distribution': os_release.get('NAME', 'UNKNOWN'),
        'type': 'Linux'}

    version = os_release['VERSION']
    if ', ' in version:
        # Fix up trusty's version formatting
        version = '{} ({})'.format(*version.split(', '))
    # Strip off an LTS point release (14.04.1 LTS -> 14.04 LTS)
    version = re.sub(r'\.\d LTS', ' LTS', version)
    platform_info['version'] = version

    match = re.match(REGEX_OS_RELEASE_VERSION, version)
    if not match:
        raise RuntimeError(
            'Could not parse /etc/os-release VERSION: %s (modified to %s)' %
            (os_release['VERSION'], version))
    match_dict = match.groupdict()
    platform_info.update({'release': match_dict['release'],
                          'series': match_dict['series'].lower()})

    uname = os.uname()
    platform_info['kernel'] = uname.release
    platform_info['arch'] = uname.machine

    return platform_info


def apply_series_overrides(orig_access: 'Dict[str, Any]') -> None:
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
    if not all([isinstance(orig_access, dict), 'entitlement' in orig_access]):
        raise RuntimeError(
            'Expected entitlement access dict. Missing "entitlement" key: %s'
            % orig_access)
    series_name = get_platform_info()['series']
    orig_entitlement = orig_access.get('entitlement', {})
    overrides = orig_entitlement.pop('series', {}).pop(series_name, {})
    for key, value in overrides.items():
        current = orig_access['entitlement'].get(key)
        if isinstance(current, dict):
            # If the key already exists and is a dict, update that dict using
            # the override
            current.update(value)
        else:
            # Otherwise, replace it wholesale
            orig_access['entitlement'][key] = value


def get_machine_id(data_dir: str) -> str:
    """Get system's unique machine-id or create our own in data_dir."""
    if os.path.exists(ETC_MACHINE_ID):
        return load_file(ETC_MACHINE_ID).rstrip('\n')
    if os.path.exists(DBUS_MACHINE_ID):  # Trusty
        return load_file(DBUS_MACHINE_ID).rstrip('\n')
    fallback_machine_id_file = os.path.join(data_dir, 'machine-id')
    # Generate, cache our own uuid if not present on the system
    # Docker images do not define ETC_MACHINE_ID or DBUS_MACHINE_ID on trusty
    # per Issue: #489
    if os.path.exists(fallback_machine_id_file):  # Use our generated uuid
        return load_file(fallback_machine_id_file).rstrip('\n')
    machine_id = str(uuid.uuid4())
    write_file(fallback_machine_id_file, machine_id)
    return machine_id
