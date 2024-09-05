import datetime
import glob
import logging
import os
import pathlib
import re
import stat
import subprocess  # nosec B404
import tempfile
import time
import uuid
from functools import lru_cache
from shutil import rmtree
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

from uaclient import defaults, exceptions, util

REBOOT_FILE_CHECK_PATH = "/var/run/reboot-required"
REBOOT_PKGS_FILE_PATH = "/var/run/reboot-required.pkgs"
ETC_MACHINE_ID = "/etc/machine-id"
DBUS_MACHINE_ID = "/var/lib/dbus/machine-id"
DISTRO_INFO_CSV = "/usr/share/distro-info/ubuntu.csv"

CPU_VENDOR_MAP = {"GenuineIntel": "intel"}
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

# N.B. this relies on the version normalisation we perform in get_release_info
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
    "DistroInfo",
    [
        ("eol", datetime.date),
        ("eol_esm", datetime.date),
        ("series", str),
        ("release", str),
        ("series_codename", str),
    ],
)

KernelInfo = NamedTuple(
    "KernelInfo",
    [
        ("uname_machine_arch", str),
        ("uname_release", str),
        ("build_date", Optional[datetime.datetime]),
        ("proc_version_signature_version", Optional[str]),
        ("major", Optional[int]),
        ("minor", Optional[int]),
        ("patch", Optional[int]),
        ("abi", Optional[str]),
        ("flavor", Optional[str]),
    ],
)

ReleaseInfo = NamedTuple(
    "ReleaseInfo",
    [
        ("distribution", str),
        ("release", str),
        ("series", str),
        ("pretty_version", str),
    ],
)

CpuInfo = NamedTuple(
    "CpuInfo",
    [
        ("vendor_id", str),
        ("model", Optional[int]),
        ("stepping", Optional[int]),
    ],
)

RebootRequiredPkgs = NamedTuple(
    "RebootRequiredPkgs",
    [
        ("standard_packages", Optional[List[str]]),
        ("kernel_packages", Optional[List[str]]),
    ],
)


RE_KERNEL_EXTRACT_BUILD_DATE = r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun).*"


def _get_kernel_changelog_timestamp(
    uname: os.uname_result,
) -> Optional[datetime.datetime]:
    if is_container():
        LOG.warning(
            "Not attempting to use timestamp of kernel "
            "changelog because we're in a container"
        )
        return None

    LOG.warning("Falling back to using timestamp of kernel changelog")

    try:
        stat_result = os.stat(
            "/usr/share/doc/linux-image-{}/changelog.Debian.gz".format(
                uname.release
            )
        )
        return datetime.datetime.fromtimestamp(
            stat_result.st_mtime, datetime.timezone.utc
        )
    except Exception:
        LOG.warning("Unable to stat kernel changelog")
        return None


def _get_kernel_build_date(
    uname: os.uname_result,
) -> Optional[datetime.datetime]:
    date_match = re.search(RE_KERNEL_EXTRACT_BUILD_DATE, uname.version)
    if date_match is None:
        LOG.warning("Unable to find build date in uname version")
        return _get_kernel_changelog_timestamp(uname)
    date_str = date_match.group(0)
    try:
        dt = datetime.datetime.strptime(date_str, "%a %b %d %H:%M:%S %Z %Y")
    except ValueError:
        LOG.warning("Unable to parse build date from uname version")
        return _get_kernel_changelog_timestamp(uname)
    if dt.tzinfo is None:
        # Give it a default timezone if it didn't get one from strptime
        # The Livepatch API requires a timezone
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


@lru_cache(maxsize=None)
def get_kernel_info() -> KernelInfo:
    proc_version_signature_version = None
    try:
        proc_version_signature_full = load_file("/proc/version_signature")
        proc_version_signature_version = proc_version_signature_full.split()[1]
    except Exception:
        LOG.warning("failed to process /proc/version_signature.")

    uname = os.uname()
    uname_machine_arch = uname.machine.strip()
    build_date = _get_kernel_build_date(uname)

    uname_release = uname.release.strip()
    uname_match = re.match(RE_KERNEL_UNAME, uname_release)
    if uname_match is None:
        LOG.warning("Failed to parse kernel: %s", uname_release)
        return KernelInfo(
            uname_machine_arch=uname_machine_arch,
            uname_release=uname_release,
            build_date=build_date,
            proc_version_signature_version=proc_version_signature_version,
            major=None,
            minor=None,
            patch=None,
            abi=None,
            flavor=None,
        )
    else:
        return KernelInfo(
            uname_machine_arch=uname_machine_arch,
            uname_release=uname_release,
            build_date=build_date,
            proc_version_signature_version=proc_version_signature_version,
            major=int(uname_match.group("major")),
            minor=int(uname_match.group("minor")),
            patch=int(uname_match.group("patch")),
            abi=uname_match.group("abi"),
            flavor=uname_match.group("flavor"),
        )


# This only works if we are root (because of permissions to 'file' the kernels
# in /boot), but can't assert_root here due to circular imports.
def get_installed_ubuntu_kernels():
    # cursed circular import
    from uaclient.apt import get_installed_packages_names

    if not util.we_are_currently_root():
        raise RuntimeError(
            "get_installed_ubuntu_kernels needs to be executed as root"
        )

    linux_image = [
        package
        for package in get_installed_packages_names()
        if "linux-image-" in package
    ]
    vmlinux_kernel_files = [
        file
        for file in glob.glob("/boot/vmlinu[x|z]-*")
        if "Linux kernel" in subp(["file", file])[0]
    ]

    linux_image_versions = [
        package_name[len("linux-image-") :] for package_name in linux_image
    ]
    vmlinuz_versions = [
        file_name[len("/boot/vmlinu?-") :]
        for file_name in vmlinux_kernel_files
    ]

    return [
        version
        for version in vmlinuz_versions
        if version in linux_image_versions
    ]


@lru_cache(maxsize=None)
def get_dpkg_arch() -> str:
    out, _err = subp(["dpkg", "--print-architecture"])
    return out.strip()


@lru_cache(maxsize=None)
def get_virt_type() -> str:
    try:
        out, _ = subp(["systemd-detect-virt"])
        return out.strip()
    except exceptions.ProcessExecutionError:
        # The main known place where that will fail is in a docker/podman
        # container that doesn't have it installed. So we look for hints
        # of that situation to report it accurately.
        try:
            proc_1_cgroup = load_file("/proc/1/cgroup")
            if "docker" in proc_1_cgroup or "buildkit" in proc_1_cgroup:
                return "docker"
            elif "buildah" in proc_1_cgroup:
                return "podman"
            else:
                return ""
        except Exception:
            return ""


@lru_cache(maxsize=None)
def get_cpu_info() -> CpuInfo:
    cpu_info_content = load_file("/proc/cpuinfo")
    cpu_info_values = {}
    for field in ["vendor_id", "model", "stepping"]:
        cpu_match = re.search(
            r"^{}\s*:\s*(?P<info>\w*)".format(field),
            cpu_info_content,
            re.MULTILINE,
        )
        if cpu_match:
            value = cpu_match.group("info")
            cpu_info_values[field] = value

    vendor_id_base = cpu_info_values.get("vendor_id", "")
    model = cpu_info_values.get("model")
    stepping = cpu_info_values.get("stepping")
    return CpuInfo(
        vendor_id=CPU_VENDOR_MAP.get(vendor_id_base, vendor_id_base),
        model=int(model) if model else None,
        stepping=int(stepping) if stepping else None,
    )


@lru_cache(maxsize=None)
def get_machine_id(cfg) -> str:
    """
    Get system's unique machine-id or create our own in data_dir.
    We first check for the machine-id in machine-token.json before
    looking at the system file.
    """
    from uaclient.files import machine_token
    from uaclient.files.state_files import machine_id_file

    machine_token_file = machine_token.get_machine_token_file()
    if machine_token_file.machine_token:
        machine_id = machine_token_file.machine_token.get(
            "machineTokenInfo", {}
        ).get("machineId")
        if machine_id:
            return machine_id

    fallback_machine_id = machine_id_file.read()

    for path in [ETC_MACHINE_ID, DBUS_MACHINE_ID]:
        if os.path.exists(path):
            content = load_file(path).rstrip("\n")
            if content:
                return content

    if fallback_machine_id:
        return fallback_machine_id

    machine_id = str(uuid.uuid4())
    machine_id_file.write(machine_id)
    return machine_id


@lru_cache(maxsize=None)
def get_release_info() -> ReleaseInfo:
    os_release = _parse_os_release()
    distribution = os_release.get("NAME", "UNKNOWN")
    pretty_version = re.sub(r"\.\d LTS", " LTS", os_release.get("VERSION", ""))
    series = os_release.get("VERSION_CODENAME", "")
    release = os_release.get("VERSION_ID", "")

    if not series or not release:
        match = re.match(REGEX_OS_RELEASE_VERSION, pretty_version)
        if not match:
            raise exceptions.ParsingErrorOnOSReleaseFile(
                orig_ver=os_release.get("VERSION", ""), mod_ver=pretty_version
            )

        match_dict = match.groupdict()
        series = series or match_dict.get("series", "")
        if not series:
            raise exceptions.MissingSeriesOnOSReleaseFile(
                version=pretty_version
            )

        release = release or match_dict.get("release", "")

    return ReleaseInfo(
        distribution=distribution,
        release=release,
        series=series.lower(),
        pretty_version=pretty_version,
    )


@lru_cache(maxsize=None)
def is_lts(series: str) -> bool:
    out, _err = subp(["/usr/bin/ubuntu-distro-info", "--supported-esm"])
    return series in out


@lru_cache(maxsize=None)
def is_current_series_lts() -> bool:
    return is_lts(get_release_info().series)


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
    return is_active_esm(get_release_info().series)


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
def is_desktop() -> bool:
    """Returns True if any package installed has "ubuntu-desktop" in the name.

    This includes ubuntu-desktop, ubuntu-desktop-minimal, kubuntu-desktop, etc.
    """
    from uaclient import apt

    for package in apt.get_installed_packages():
        if "ubuntu-desktop" in package.name:
            return True
    return False


@lru_cache(maxsize=None)
def _parse_os_release() -> Dict[str, str]:
    try:
        file_contents = load_file("/etc/os-release")
    except FileNotFoundError:
        file_contents = load_file("/usr/lib/os-release")
    data = {}
    for line in file_contents.splitlines():
        key, value = line.split("=", 1)
        if value:
            data[key] = value.strip().strip('"')
    return data


@lru_cache(maxsize=None)
def get_distro_info(series: str) -> DistroInfo:
    try:
        lines = load_file(DISTRO_INFO_CSV).splitlines()
    except FileNotFoundError:
        raise exceptions.MissingDistroInfoFile()
    for line in lines:
        values = line.split(",")
        if values[2] == series:
            if series == "xenial":
                eol_esm = "2026-04-23"
            else:
                eol_esm = values[7] if "LTS" in values[0] else values[5]
            return DistroInfo(
                release=values[0],
                series_codename=values[1],
                series=values[2],
                eol=datetime.datetime.strptime(values[5], "%Y-%m-%d").date(),
                eol_esm=datetime.datetime.strptime(eol_esm, "%Y-%m-%d").date(),
            )

    raise exceptions.MissingSeriesInDistroInfoFile(series=series)


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


def load_file(filename: str) -> str:
    """Read filename and decode content."""
    with open(filename, "rb") as stream:
        LOG.debug("Reading file: %s", filename)
        content = stream.read()
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise exceptions.InvalidFileEncodingError(
            file_name=filename, file_encoding="utf-8"
        )


def create_file(filename: str, mode: int = 0o644) -> None:
    LOG.debug("Creating file: %s", filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    pathlib.Path(filename).touch()
    os.chmod(filename, mode)


def write_file(
    filename: str, content: str, mode: Optional[int] = None
) -> None:
    """Write content to the provided filename encoding it if necessary.

    We preserve the file ownership and permissions if the file is present
    and no mode argument is provided.

    @param filename: The full path of the file to write.
    @param content: The content to write to the file.
    @param mode: The filesystem mode to set on the file.
    """
    tmpf = None
    is_file_present = os.path.isfile(filename)
    if is_file_present:
        file_stat = pathlib.Path(filename).stat()
        f_mode = stat.S_IMODE(file_stat.st_mode)
        if mode is None:
            mode = f_mode

    elif mode is None:
        mode = 0o644
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        tmpf = tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=os.path.dirname(filename)
        )
        LOG.debug(
            "Writing file %s atomically via tempfile %s", filename, tmpf.name
        )
        tmpf.write(content.encode("utf-8"))
        tmpf.flush()
        tmpf.close()
        os.chmod(tmpf.name, mode)
        if is_file_present:
            os.chown(tmpf.name, file_stat.st_uid, file_stat.st_gid)
        os.rename(tmpf.name, filename)
    except Exception as e:
        if tmpf is not None:
            os.unlink(tmpf.name)
        raise e


def ensure_file_absent(file_path: str) -> None:
    """Remove a file if it exists, logging a message about removal."""
    try:
        os.unlink(file_path)
        LOG.debug("Removed file: %s", file_path)
    except FileNotFoundError:
        LOG.debug("Tried to remove %s but file does not exist", file_path)


def _subp(
    args: Sequence[str],
    rcs: Optional[List[int]] = None,
    capture: bool = False,
    timeout: Optional[float] = None,
    override_env_vars: Optional[Dict[str, str]] = None,
    pipe_stdouterr: bool = True,
) -> Tuple[str, str]:
    """Run a command and return a tuple of decoded stdout, stderr.

    @param args: A list of arguments to feed to subprocess.Popen
    @param rcs: A list of allowed return_codes. If returncode not in rcs
        raise a ProcessExecutionError.
    @param capture: Boolean set True to log the command and response.
    @param timeout: Optional float indicating number of seconds to wait for
        subp to return.
    @param override_env_vars: Optional dictionary of environment variables.
        If None, the current os.environ is used for the subprocess.
        If defined, these env vars get merged with the current process'
        os.environ for the subprocess, overriding any values that already
        existed in os.environ.

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    @raises subprocess.TimeoutError when timeout specified and the command
        exceeds that number of seconds.
    """
    bytes_args = [
        x if isinstance(x, bytes) else x.encode("utf-8") for x in args
    ]

    stdout = None
    stderr = None
    set_lang = {}

    if pipe_stdouterr:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
        # Set LANG to avoid non-utf8 when we pipe the handlers
        set_lang = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}

    if override_env_vars is None:
        override_env_vars = {}
    merged_env = {**os.environ, **set_lang, **override_env_vars}

    if rcs is None:
        rcs = [0]
    redacted_cmd = util.redact_sensitive_logs(" ".join(args))
    try:
        proc = subprocess.Popen(  # nosec B603
            bytes_args,
            stdout=stdout,
            stderr=stderr,
            env=merged_env,
        )
        (out, err) = proc.communicate(timeout=timeout)
    except OSError:
        try:
            out_result = out.decode("utf-8", errors="ignore") if out else ""
            err_result = err.decode("utf-8", errors="ignore") if err else ""
            raise exceptions.ProcessExecutionError(
                cmd=redacted_cmd,
                exit_code=proc.returncode,
                stdout=out_result,
                stderr=err_result,
            )
        except UnboundLocalError:
            raise exceptions.ProcessExecutionError(cmd=redacted_cmd)

    out_result = out.decode("utf-8", errors="ignore") if out else ""
    err_result = err.decode("utf-8", errors="ignore") if err else ""
    if proc.returncode not in rcs:
        raise exceptions.ProcessExecutionError(
            cmd=redacted_cmd,
            exit_code=proc.returncode,
            stdout=out_result,
            stderr=err_result,
        )
    if capture:
        LOG.debug(
            "Ran cmd: %s, rc: %s stderr: %s",
            redacted_cmd,
            proc.returncode,
            err,
        )
    return out_result, err_result


def subp(
    args: Sequence[str],
    rcs: Optional[List[int]] = None,
    capture: bool = False,
    timeout: Optional[float] = None,
    retry_sleeps: Optional[List[float]] = None,
    override_env_vars: Optional[Dict[str, str]] = None,
    pipe_stdouterr: bool = True,
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
     @param override_env_vars: Optional dictionary of environment variables.
        If None, the current os.environ is used for the subprocess.
        If defined, these env vars get merged with the current process'
        os.environ for the subprocess, overriding any values that already
        existed in os.environ.

    @return: Tuple of utf-8 decoded stdout, stderr
    @raises ProcessExecutionError on invalid command or returncode not in rcs.
    @raises subprocess.TimeoutError when timeout specified and the command
        exceeds that number of seconds.
    """
    retry_sleeps = retry_sleeps.copy() if retry_sleeps is not None else None
    while True:
        try:
            out, err = _subp(
                args,
                rcs,
                capture,
                timeout,
                override_env_vars=override_env_vars,
                pipe_stdouterr=pipe_stdouterr,
            )
            break
        except exceptions.ProcessExecutionError as e:
            if capture:
                LOG.debug(str(e))
                LOG.warning("Stderr: %s\nStdout: %s", e.stderr, e.stdout)
            if not retry_sleeps:
                raise
            LOG.debug(str(e))
            LOG.debug("Retrying %d more times.", len(retry_sleeps))
            time.sleep(retry_sleeps.pop(0))
    return out, err


def ensure_folder_absent(folder_path: str) -> None:
    try:
        rmtree(folder_path)
        LOG.debug("Removed folder: %s", folder_path)
    except FileNotFoundError:
        LOG.debug("Tried to remove %s but folder does not exist", folder_path)


def is_systemd_unit_active(service_name: str) -> bool:
    """
    Get if the systemd job is active in the system. Note that any status
    different from "active" will make this function return False.
    Additionally, if the system doesn't exist we will also return False
    here.

    @param service_name: Name of the systemd job to look at

    @return: A Boolean specifying if the job is active or not
    """
    try:
        subp(["systemctl", "is-active", "--quiet", service_name])
    except exceptions.ProcessExecutionError:
        return False
    return True


def get_systemd_unit_active_state(service_name: str) -> Optional[str]:
    try:
        out, _ = subp(
            [
                "systemctl",
                "show",
                "--property=ActiveState",
                "--no-pager",
                service_name,
            ]
        )
        if out and out.startswith("ActiveState="):
            return out.split("=")[1].strip()
        else:
            LOG.warning(
                "Couldn't find ActiveState in systemctl show output for %s",
                service_name,
            )
    except exceptions.ProcessExecutionError as e:
        LOG.warning(
            "Failed to get ActiveState for systemd unit %s",
            service_name,
            exc_info=e,
        )
    return None


def get_user_cache_dir() -> str:
    if util.we_are_currently_root():
        return defaults.UAC_RUN_PATH

    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        return os.path.join(xdg_cache_home, defaults.USER_CACHE_SUBDIR)

    return os.path.join(
        os.path.expanduser("~"), ".cache", defaults.USER_CACHE_SUBDIR
    )


def get_reboot_required_pkgs() -> Optional[RebootRequiredPkgs]:
    try:
        pkg_list_str = load_file(REBOOT_PKGS_FILE_PATH)
    except FileNotFoundError:
        return None

    standard_packages = []
    kernel_packages = []
    kernel_regex = "^(linux-image|linux-base).*"

    for pkg in pkg_list_str.split():
        if re.match(kernel_regex, pkg):
            kernel_packages.append(pkg)
        else:
            standard_packages.append(pkg)

    return RebootRequiredPkgs(
        standard_packages=sorted(standard_packages),
        kernel_packages=sorted(kernel_packages),
    )
