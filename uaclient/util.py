from errno import ENOENT
import json
import logging
import os
import re
import subprocess
from urllib import request
import uuid


SENSITIVE_KEYS = ['caveat_id', 'password', 'resourceToken', 'machineToken']

ETC_MACHINE_ID = '/etc/machine-id'
DBUS_MACHINE_ID = '/var/lib/dbus/machine-id'
DROPPED_KEY = object()


class UrlError(IOError):

    def __init__(self, cause, code=None, headers=None, url=None):
        super().__init__(str(cause))
        self.cause = cause
        self.code = code
        self.headers = headers
        if self.headers is None:
            self.headers = {}
        self.url = url


class ProcessExecutionError(IOError):

    ERR_TMPL = (
        "Failed running command '{cmd}' [exit({exit_code})]. Message {stderr}")

    def __init__(self, cmd, exit_code=None, stdout='', stderr=''):
        self.cmd = cmd
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        if not exit_code:
            message_tmpl = "Invalid command specified '{cmd}'."
        else:
            message_tmpl = (
                "Failed running command '{cmd}' [exit({exit_code})]."
                " Message: {stderr}")
        super().__init__(
            message_tmpl.format(cmd=cmd, stderr=stderr, exit_code=exit_code))


def del_file(path):
    try:
        os.unlink(path)
    except OSError as e:
        if e.errno != ENOENT:
            raise e


def encode_text(text, encoding='utf-8'):
    """Convert a text string into a binary type using given encoding."""
    if isinstance(text, bytes):
        return text
    return text.encode(encoding)


def get_dict_deltas(orig_dict, new_dict, path=''):
    """Return a dictionary of delta between orig_dict and new_dict."""
    deltas = {}
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


def is_container(run_path='/run'):
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


def is_exe(path):
    # return boolean indicating if path exists and is executable.
    return os.path.isfile(path) and os.access(path, os.X_OK)


def load_file(filename, decode=True):
    """Read filename and decode content."""
    with open(filename, 'rb') as stream:
        content = stream.read()
    return content.decode('utf-8')


def maybe_parse_json(content):
    """Attempt to parse json content.

    @return: Structured content on success and None on failure.
    """
    try:
        return json.loads(content)
    except ValueError:
        return None


def readurl(url, data=None, headers=None, method=None):
    if data and not method:
        method = 'POST'
    req = request.Request(url, data=data, headers=headers)
    if method:
        req.get_method = lambda: method
    if data:
        redacted_data = maybe_parse_json(data.decode('utf-8'))
        for key in SENSITIVE_KEYS:
            if key in redacted_data:
                redacted_data[key] = '<REDACTED>'
        redacted_data = json.dumps(redacted_data)
    else:
        redacted_data = data
    logging.debug(
        'URL [%s]: %s, headers: %s, data: %s',
        method or 'GET', url, headers, redacted_data)
    resp = request.urlopen(req)
    content = resp.read().decode('utf-8')
    if 'application/json' in resp.headers.get('Content-type', ''):
        content = json.loads(content)
    logging.debug(
        'URL [%s] response: %s, headers: %s, data: %s',
        method or 'GET', url, resp.headers, content)
    return content, resp.headers


def subp(args, rcs=None, capture=False):
    """Run a command and return a tuple of decoded stdout, stderr.

    @param subp: A list of arguments to feed to subprocess.Popen
    @param rcs: A list of allowed return_codes. If returncode not in rcs
        raise a ProcessExecutionError.
    @param capture: Boolean set True to log the command and response.

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    """
    bytes_args = [x if isinstance(x, bytes) else x.encode("utf-8")
                  for x in args]
    if rcs is None:
        rcs = [0]
    try:
        proc = subprocess.Popen(
            bytes_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate()
    except OSError:
        try:
            if capture:
                logging.error('Failed running cmd: %s, rc: %s stderr: %s',
                              ' '.join(args), proc.returncode, err)
        except UnboundLocalError:
            pass
        raise ProcessExecutionError(cmd=' '.join(args))
    if proc.returncode not in rcs:
        if capture:
            logging.error('Failed running cmd: %s, rc: %s stderr: %s',
                          ' '.join(args), proc.returncode, err)
        raise ProcessExecutionError(
            cmd=' '.join(args), exit_code=proc.returncode, stdout=out,
            stderr=err)
    if capture:
        logging.debug('Ran cmd: %s, rc: %s stderr: %s',
                      ' '.join(args), proc.returncode, err)
    return out.decode('utf-8'), err.decode('utf-8')


def which(program):
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


def write_file(filename, content, mode=0o644, omode='wb'):
    """Write content to the provided filename encoding it if necessary.

    @param filename: The full path of the file to write.
    @param content: The content to write to the file.
    @param mode: The filesystem mode to set on the file.
    @param omode: The open mode used when opening the file (w, wb, a, etc.)
    """
    logging.debug('Writing file: %s', filename)
    if 'b' in omode.lower():
        content = encode_text(content)
    with open(filename, omode) as fh:
        fh.write(content)
        fh.flush()
    os.chmod(filename, mode)


def parse_os_release(release_file=None):
    if not release_file:
        release_file = '/etc/os-release'
    data = {}
    for line in load_file(release_file).splitlines():
        key, value = line.split('=', 1)
        if value:
            data[key] = value.strip().strip('"')
    return data


REGEX_OS_RELEASE_VERSION_1 = (  # Precise, Trusty
    r'(?P<version>\d+\.\d+)(\.\d)? (?P<lts>LTS,?) ?(?P<series>\w+).*')
REGEX_OS_RELEASE_VERSION_2 = (  # >= Disco
    r'(?P<version>\d+\.\d+)(\.\d)? (?P<lts>LTS )?\((?P<series>\w+).*')


def get_platform_info(key=None):
    os_release = parse_os_release()
    platform_info = {
        'distribution': os_release.get('NAME', 'UNKNOWN'),
        'type': 'Linux'}

    if key in (None, 'release', 'series'):
        version = os_release['VERSION']
        match = re.match(REGEX_OS_RELEASE_VERSION_1, version)
        if not match:
            match = re.match(REGEX_OS_RELEASE_VERSION_2, version)
        if not match:
            raise RuntimeError(
                'Could not parse /etc/os-release VERSION: %s' %
                os_release['VERSION'])
        match_dict = match.groupdict()
        platform_info.update({'release': match_dict['version'],
                              'series': match_dict['series'].lower()})
    if key in (None, 'kernel'):
        kernel_ver_out, _err = subp(['uname', '-r'])
        platform_info['kernel'] = kernel_ver_out.strip()
    if key in (None, 'arch'):
        arch, _err = subp(['uname', '-i'])
        platform_info['arch'] = arch.strip()
    return platform_info if not key else platform_info[key]


def get_machine_id(data_dir):
    """Get system's unique machine-id or create our own in data_dir."""
    if os.path.exists(ETC_MACHINE_ID):
        return load_file(ETC_MACHINE_ID).rstrip('\n')
    if os.path.exists(DBUS_MACHINE_ID):  # Trusty
        return load_file(DBUS_MACHINE_ID).rstrip('\n')
    fallback_machine_id_file = os.path.join(data_dir, 'machine-id')
    if os.path.exists(fallback_machine_id_file):  # Gen our own if needed
        return load_file(fallback_machine_id_file).rstrip('\n')
    machine_id = uuid.uuid4()
    write_file(fallback_machine_id_file, machine_id)
    return machine_id


def redact_sensitive(content):
    """Redact security-sensitive content from content dict."""
    redacted = {}
    for key, value in content.items():
        if key in SENSITIVE_KEYS:
            redacted[key] = '<REDACTED>'
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted
