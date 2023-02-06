import datetime
import logging
import os
import pathlib
import re
import subprocess
import tempfile
import time
import uuid
from functools import lru_cache
from shutil import rmtree
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from uaclient import exceptions, messages, util

REBOOT_FILE_CHECK_PATH = "/var/run/reboot-required"
REBOOT_PKGS_FILE_PATH = "/var/run/reboot-required.pkgs"
ETC_MACHINE_ID = "/etc/machine-id"
DBUS_MACHINE_ID = "/var/lib/dbus/machine-id"
DISTRO_INFO_CSV = "/usr/share/distro-info/ubuntu.csv"

# N.B. this relies on the version normalisation we perform in get_platform_info
REGEX_OS_RELEASE_VERSION = (
    r"(?P<release>\d+\.\d+) (LTS\s*)?(\((?P<series>\w+))?.*"
)

RE_KERNEL_UNAME = (
    r"^"
    r"(?P<major>[\d]+)"
    r"[.-]"
    r"(?P<minor>[\d]+)"
    r"[.-]"
    r"(?P<patch>[\d]+)"
    r"-"
    r"(?P<abi>[\d]+)"
    r"-"
    r"(?P<flavor>[A-Za-z0-9_-]+)"
    r"$"
)

DistroInfo = NamedTuple(
    "DistroInfo", [("eol", datetime.date), ("eol_esm", datetime.date)]
)

KernelInfo = NamedTuple(
    "KernelInfo",
    [
        ("uname_release", str),
        ("proc_version_signature_version", Optional[str]),
        ("major", Optional[int]),
        ("minor", Optional[int]),
        ("patch", Optional[int]),
        ("abi", Optional[str]),
        ("flavor", Optional[str]),
    ],
)


@lru_cache(maxsize=None)
def get_kernel_info() -> KernelInfo:
    proc_version_signature_version = None
    try:
        proc_version_signature_full = load_file("/proc/version_signature")
        proc_version_signature_version = proc_version_signature_full.split()[1]
    except Exception:
        logging.warning("failed to process /proc/version_signature.")

    uname_release = os.uname().release.strip()
    uname_match = re.match(RE_KERNEL_UNAME, uname_release)
    if uname_match is None:
        logging.warning(
            messages.KERNEL_PARSE_ERROR.format(kernel=uname_release)
        )
        return KernelInfo(
            uname_release=uname_release,
            proc_version_signature_version=proc_version_signature_version,
            major=None,
            minor=None,
            patch=None,
            abi=None,
            flavor=None,
        )
    else:
        return KernelInfo(
            uname_release=uname_release,
            proc_version_signature_version=proc_version_signature_version,
            major=int(uname_match.group("major")),
            minor=int(uname_match.group("minor")),
            patch=int(uname_match.group("patch")),
            abi=uname_match.group("abi"),
            flavor=uname_match.group("flavor"),
        )


@lru_cache(maxsize=None)
def get_lscpu_arch() -> str:
    """used for livepatch"""
    out, _err = subp(["lscpu"])
    for line in out.splitlines():
        if line.strip().startswith("Architecture:"):
            arch = line.split(":")[1].strip()
            if arch:
                return arch
            else:
                break
    error_msg = messages.LSCPU_ARCH_PARSE_ERROR
    raise exceptions.UserFacingError(
        msg=error_msg.msg, msg_code=error_msg.name
    )


@lru_cache(maxsize=None)
def get_dpkg_arch() -> str:
    out, _err = subp(["dpkg", "--print-architecture"])
    return out.strip()


@lru_cache(maxsize=None)
def get_machine_id(cfg) -> str:
    """
    Get system's unique machine-id or create our own in data_dir.
    We first check for the machine-id in machine-token.json before
    looking at the system file.
    """

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
    cfg.write_cache("machine-id", machine_id)
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

    version = re.sub(r"\.\d LTS", " LTS", os_release.get("VERSION", ""))
    platform_info["version"] = version
    series = os_release.get("VERSION_CODENAME", "")
    release = os_release.get("VERSION_ID", "")

    if not series or not release:
        match = re.match(REGEX_OS_RELEASE_VERSION, version)
        if not match:
            raise exceptions.ParsingErrorOnOSReleaseFile(
                orig_ver=os_release.get("VERSION", ""), mod_ver=version
            )

        match_dict = match.groupdict()
        series = series or match_dict.get("series", "")
        if not series:
            raise exceptions.MissingSeriesOnOSReleaseFile(version=version)

        release = release or match_dict.get("release", "")

    platform_info.update(
        {
            "release": release,
            "series": series.lower(),
            "kernel": get_kernel_info().uname_release,
            "arch": get_dpkg_arch(),
        }
    )
    return platform_info


@lru_cache(maxsize=None)
def is_lts(series: str) -> bool:
    out, _err = subp(["/usr/bin/ubuntu-distro-info", "--supported-esm"])
    return series in out


@lru_cache(maxsize=None)
def is_current_series_lts() -> bool:
    return is_lts(get_platform_info()["series"])


@lru_cache(maxsize=None)
def is_supported(series: str) -> bool:
    out, _err = subp(["/usr/bin/ubuntu-distro-info", "--supported"])
    return series in out


@lru_cache(maxsize=None)
def is_active_esm(series: str) -> bool:
    """Return True when Ubuntu series supports ESM and is actively in ESM."""
    if not is_lts(series):
        return False
    out, _err = subp(
        ["/usr/bin/ubuntu-distro-info", "--series", series, "-yeol"]
    )
    return int(out) <= 0


@lru_cache(maxsize=None)
def is_current_series_active_esm() -> bool:
    return is_active_esm(get_platform_info()["series"])


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


@lru_cache(maxsize=None)
def get_distro_info(series: str) -> DistroInfo:
    try:
        lines = load_file(DISTRO_INFO_CSV).splitlines()
    except FileNotFoundError:
        raise exceptions.UserFacingError(messages.MISSING_DISTRO_INFO_FILE)
    for line in lines:
        values = line.split(",")
        if values[2] == series:
            if series == "xenial":
                eol_esm = "2026-04-23"
            else:
                eol_esm = values[7] if "LTS" in values[0] else values[5]
            return DistroInfo(
                eol=datetime.datetime.strptime(values[5], "%Y-%m-%d").date(),
                eol_esm=datetime.datetime.strptime(eol_esm, "%Y-%m-%d").date(),
            )

    raise exceptions.UserFacingError(
        messages.MISSING_SERIES_IN_DISTRO_INFO_FILE.format(series)
    )


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


def is_exe(path: str) -> bool:
    # return boolean indicating if path exists and is executable.
    return os.path.isfile(path) and os.access(path, os.X_OK)


def load_file(filename: str, decode: bool = True) -> str:
    """Read filename and decode content."""
    logging.debug("Reading file: %s", filename)
    with open(filename, "rb") as stream:
        content = stream.read()
    return content.decode("utf-8")


def create_file(filename: str, mode: int = 0o644) -> None:
    logging.debug("Creating file: %s", filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    pathlib.Path(filename).touch()
    os.chmod(filename, mode)


def write_file(filename: str, content: str, mode: int = 0o644) -> None:
    """Write content to the provided filename encoding it if necessary.

    @param filename: The full path of the file to write.
    @param content: The content to write to the file.
    @param mode: The filesystem mode to set on the file.
    """
    tmpf = None
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        tmpf = tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=os.path.dirname(filename)
        )
        logging.debug(
            "Writing file %s atomically via tempfile %s", filename, tmpf.name
        )
        tmpf.write(content.encode("utf-8"))
        tmpf.flush()
        tmpf.close()
        os.chmod(tmpf.name, mode)
        os.rename(tmpf.name, filename)
    except Exception as e:
        if tmpf is not None:
            os.unlink(tmpf.name)
        raise e


def ensure_file_absent(file_path: str) -> None:
    """Remove a file if it exists, logging a message about removal."""
    if os.path.exists(file_path):
        logging.debug("Removing file: %s", file_path)
        os.unlink(file_path)


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
    redacted_cmd = util.redact_sensitive_logs(" ".join(args))
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
                logging.debug(util.redact_sensitive_logs(str(e)))
                msg = "Stderr: {}\nStdout: {}".format(e.stderr, e.stdout)
                logging.warning(util.redact_sensitive_logs(msg))
            if not retry_sleeps:
                raise
            retry_msg = " Retrying %d more times." % len(retry_sleeps)
            logging.debug(util.redact_sensitive_logs(str(e) + retry_msg))
            time.sleep(retry_sleeps.pop(0))
    return out, err


def ensure_folder_absent(folder_path: str) -> None:
    if os.path.exists(folder_path):
        logging.debug("Removing folder: %s", folder_path)
        rmtree(folder_path)
