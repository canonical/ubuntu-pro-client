import glob
import logging
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Optional

from uaclient import event_logger, exceptions, gpg, messages, util

APT_HELPER_TIMEOUT = 60.0  # 60 second timeout used for apt-helper call
APT_AUTH_COMMENT = "  # ubuntu-advantage-tools"
APT_CONFIG_AUTH_FILE = "Dir::Etc::netrc/"
APT_CONFIG_AUTH_PARTS_DIR = "Dir::Etc::netrcparts/"
APT_CONFIG_LISTS_DIR = "Dir::State::lists/"
APT_CONFIG_PROXY_HTTP = """Acquire::http::Proxy "{proxy_url}";\n"""
APT_CONFIG_PROXY_HTTPS = """Acquire::https::Proxy "{proxy_url}";\n"""
APT_KEYS_DIR = "/etc/apt/trusted.gpg.d"
KEYRINGS_DIR = "/usr/share/keyrings"
APT_METHOD_HTTPS_FILE = "/usr/lib/apt/methods/https"
CA_CERTIFICATES_FILE = "/usr/sbin/update-ca-certificates"
APT_PROXY_CONF_FILE = "/etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy"

# Since we generally have a person at the command line prompt. Don't loop
# for 5 minutes like charmhelpers because we expect the human to notice and
# resolve to apt conflict or try again.
# Hope for an optimal first try.
APT_RETRIES = [1.0, 5.0, 10.0]

event = event_logger.get_event_logger()


def assert_valid_apt_credentials(repo_url, username, password):
    """Validate apt credentials for a PPA.

    @param repo_url: private-ppa url path
    @param username: PPA login username.
    @param password: PPA login password or resource token.

    @raises: UserFacingError for invalid credentials, timeout or unexpected
        errors.
    """
    protocol, repo_path = repo_url.split("://")
    if not os.path.exists("/usr/lib/apt/apt-helper"):
        return
    try:
        with tempfile.TemporaryDirectory() as tmpd:
            util.subp(
                [
                    "/usr/lib/apt/apt-helper",
                    "download-file",
                    "{}://{}:{}@{}/ubuntu/pool/".format(
                        protocol, username, password, repo_path
                    ),
                    os.path.join(tmpd, "apt-helper-output"),
                ],
                timeout=APT_HELPER_TIMEOUT,
                retry_sleeps=APT_RETRIES,
            )
    except exceptions.ProcessExecutionError as e:
        if e.exit_code == 100:
            stderr = str(e.stderr).lower()
            if re.search(r"401\s+unauthorized|httperror401", stderr):
                raise exceptions.UserFacingError(
                    "Invalid APT credentials provided for {}".format(repo_url)
                )
            elif re.search(r"connection timed out", stderr):
                raise exceptions.UserFacingError(
                    "Timeout trying to access APT repository at {}".format(
                        repo_url
                    )
                )
        raise exceptions.UserFacingError(
            "Unexpected APT error. See /var/log/ubuntu-advantage.log"
        )
    except subprocess.TimeoutExpired:
        raise exceptions.UserFacingError(
            "Cannot validate credentials for APT repo."
            " Timeout after {} seconds trying to reach {}.".format(
                APT_HELPER_TIMEOUT, repo_path
            )
        )


def _parse_apt_update_for_invalid_apt_config(
    apt_error: str
) -> Optional[messages.NamedMessage]:
    """Parse apt update errors for invalid apt config in user machine.

    This functions parses apt update errors regarding the presence of
    invalid apt config in the system, for example, a ppa that cannot be
    reached, for example.

    In that scenario, apt will output a message in the following formats:

    The repository 'ppa 404 Release' ...
    Failed to fetch ppa 404 ...

    On some releases, both of these errors will be present in the apt error
    message.

    :param apt_error: The apt error string
    :return: a NamedMessage containing the error message
    """
    error_msg = None
    failed_repos = set()

    for line in apt_error.strip().split("\n"):
        if line:
            pattern_match = re.search(
                r"(Failed to fetch |The repository .)(?P<url>[^\s]+)", line
            )

            if pattern_match:
                repo_url_match = (
                    "- " + pattern_match.groupdict()["url"].split("/dists")[0]
                )

                failed_repos.add(repo_url_match)

    if failed_repos:
        error_msg = messages.APT_UPDATE_INVALID_URL_CONFIG.format(
            plural="s" if len(failed_repos) > 1 else "",
            failed_repos="\n".join(sorted(failed_repos)),
        )

    return error_msg


def run_apt_command(
    cmd: List[str],
    error_msg: Optional[str] = None,
    env: Optional[Dict[str, str]] = {},
) -> str:
    """Run an apt command, retrying upon failure APT_RETRIES times.

    :param cmd: List containing the apt command to run, passed to subp.
    :param error_msg: The string to raise as UserFacingError when all retries
       are exhausted in failure.
    :param env: Optional dictionary of environment variables to pass to subp.

    :return: stdout from successful run of the apt command.
    :raise UserFacingError: on issues running apt-cache policy.
    """
    try:
        out, _err = util.subp(
            cmd, capture=True, retry_sleeps=APT_RETRIES, env=env
        )
    except exceptions.ProcessExecutionError as e:
        if "Could not get lock /var/lib/dpkg/lock" in str(e.stderr):
            raise exceptions.APTProcessConflictError()
        else:
            """
            Treat errors where one of the APT repositories
            is invalid or unreachable. In that situation, we alert
            which repository is causing the error
            """
            repo_error_msg = _parse_apt_update_for_invalid_apt_config(e.stderr)
            if repo_error_msg:
                raise exceptions.APTInvalidRepoError(
                    error_msg=repo_error_msg.msg
                )

        msg = error_msg if error_msg else str(e)
        raise exceptions.UserFacingError(msg)
    return out


def run_apt_update_command(env: Optional[Dict[str, str]] = {}) -> str:
    try:
        out = run_apt_command(cmd=["apt-get", "update"], env=env)
    except exceptions.APTProcessConflictError:
        raise exceptions.APTUpdateProcessConflictError()
    except exceptions.APTInvalidRepoError as e:
        raise exceptions.APTUpdateInvalidRepoError(repo_msg=e.msg)
    except exceptions.UserFacingError as e:
        raise exceptions.UserFacingError(
            msg=messages.APT_UPDATE_FAILED.msg + "\n" + e.msg,
            msg_code=messages.APT_UPDATE_FAILED.name,
        )

    return out


def run_apt_install_command(
    packages: List[str],
    apt_options: Optional[List[str]] = None,
    error_msg: Optional[str] = None,
    env: Optional[Dict[str, str]] = {},
) -> str:
    if apt_options is None:
        apt_options = []

    try:
        out = run_apt_command(
            cmd=["apt-get", "install", "--assume-yes"]
            + apt_options
            + packages,
            error_msg=error_msg,
            env=env,
        )
    except exceptions.APTProcessConflictError:
        raise exceptions.APTInstallProcessConflictError(header_msg=error_msg)
    except exceptions.APTInvalidRepoError as e:
        raise exceptions.APTInstallInvalidRepoError(
            repo_msg=e.msg, header_msg=error_msg
        )

    return out


def add_auth_apt_repo(
    repo_filename: str,
    repo_url: str,
    credentials: str,
    suites: List[str],
    keyring_file: str,
) -> None:
    """Add an authenticated apt repo and credentials to the system.

    @raises: InvalidAPTCredentialsError when the token provided can't access
        the repo PPA.
    """
    try:
        username, password = credentials.split(":")
    except ValueError:  # Then we have a bearer token
        username = "bearer"
        password = credentials
    series = util.get_platform_info()["series"]
    if repo_url.endswith("/"):
        repo_url = repo_url[:-1]
    assert_valid_apt_credentials(repo_url, username, password)

    # Does this system have updates suite enabled?
    updates_enabled = False
    policy = run_apt_command(
        ["apt-cache", "policy"], messages.APT_POLICY_FAILED.msg
    )
    for line in policy.splitlines():
        # We only care about $suite-updates lines
        if "a={}-updates".format(series) not in line:
            continue
        # We only care about $suite-updates from the Ubuntu archive
        if "o=Ubuntu," not in line:
            continue
        updates_enabled = True
        break

    content = ""
    for suite in suites:
        if series not in suite:
            continue  # Only enable suites matching this current series
        maybe_comment = ""
        if "-updates" in suite and not updates_enabled:
            logging.debug(
                'Not enabling apt suite "%s" because "%s-updates" is not'
                " enabled",
                suite,
                series,
            )
            maybe_comment = "# "
        content += (
            "{maybe_comment}deb {url}/ubuntu {suite} main\n"
            "# deb-src {url}/ubuntu {suite} main\n".format(
                maybe_comment=maybe_comment, url=repo_url, suite=suite
            )
        )
    util.write_file(repo_filename, content)
    add_apt_auth_conf_entry(repo_url, username, password)
    source_keyring_file = os.path.join(KEYRINGS_DIR, keyring_file)
    destination_keyring_file = os.path.join(APT_KEYS_DIR, keyring_file)
    gpg.export_gpg_key(source_keyring_file, destination_keyring_file)


def add_apt_auth_conf_entry(repo_url, login, password):
    """Add or replace an apt auth line in apt's auth.conf file or conf.d."""
    apt_auth_file = get_apt_auth_file_from_apt_config()
    _protocol, repo_path = repo_url.split("://")
    if repo_path.endswith("/"):  # strip trailing slash
        repo_path = repo_path[:-1]
    if os.path.exists(apt_auth_file):
        orig_content = util.load_file(apt_auth_file)
    else:
        orig_content = ""
    repo_auth_line = (
        "machine {repo_path}/ login {login} password {password}"
        "{cmt}".format(
            repo_path=repo_path,
            login=login,
            password=password,
            cmt=APT_AUTH_COMMENT,
        )
    )
    added_new_auth = False
    new_lines = []
    for line in orig_content.splitlines():
        machine_match = re.match(r"machine\s+(?P<repo_url>[.\-\w]+)/?.*", line)
        if machine_match:
            matched_repo = machine_match.group("repo_url")
            if matched_repo == repo_path:
                # Replace old auth with new auth at same line
                new_lines.append(repo_auth_line)
                added_new_auth = True
                continue
            if matched_repo in repo_path:
                # Insert our repo before. We are a more specific apt repo match
                new_lines.append(repo_auth_line)
                added_new_auth = True
        new_lines.append(line)
    if not added_new_auth:
        new_lines.append(repo_auth_line)
    new_lines.append("")
    util.write_file(apt_auth_file, "\n".join(new_lines), mode=0o600)


def remove_repo_from_apt_auth_file(repo_url):
    """Remove a repo from the shared apt auth file"""
    _protocol, repo_path = repo_url.split("://")
    if repo_path.endswith("/"):  # strip trailing slash
        repo_path = repo_path[:-1]
    apt_auth_file = get_apt_auth_file_from_apt_config()
    if os.path.exists(apt_auth_file):
        apt_auth = util.load_file(apt_auth_file)
        auth_prefix = "machine {repo_path}/ login".format(repo_path=repo_path)
        content = "\n".join(
            [line for line in apt_auth.splitlines() if auth_prefix not in line]
        )
        if not content:
            os.unlink(apt_auth_file)
        else:
            util.write_file(apt_auth_file, content, mode=0o600)


def remove_auth_apt_repo(
    repo_filename: str, repo_url: str, keyring_file: str = None
) -> None:
    """Remove an authenticated apt repo and credentials to the system"""
    util.del_file(repo_filename)
    if keyring_file:
        keyring_file = os.path.join(APT_KEYS_DIR, keyring_file)
        util.del_file(keyring_file)
    remove_repo_from_apt_auth_file(repo_url)


def restore_commented_apt_list_file(filename: str) -> None:
    """Uncomment commented deb lines in the given file."""
    if os.path.exists(filename):
        file_content = util.load_file(filename)
        file_content = file_content.replace("# deb ", "deb ")
        util.write_file(filename, file_content)


def add_ppa_pinning(apt_preference_file, repo_url, origin, priority):
    """Add an apt preferences file and pin for a PPA."""
    series = util.get_platform_info()["series"]
    _protocol, repo_path = repo_url.split("://")
    if repo_path.endswith("/"):  # strip trailing slash
        repo_path = repo_path[:-1]
    content = (
        "Package: *\n"
        "Pin: release o={origin}, n={series}\n"
        "Pin-Priority: {priority}\n".format(
            origin=origin, priority=priority, series=series
        )
    )
    util.write_file(apt_preference_file, content)


def get_apt_auth_file_from_apt_config():
    """Return to patch to the system configured APT auth file."""
    out, _err = util.subp(
        ["apt-config", "shell", "key", APT_CONFIG_AUTH_PARTS_DIR]
    )
    if out:  # then auth.conf.d parts is present
        return out.split("'")[1] + "90ubuntu-advantage"
    else:  # then use configured /etc/apt/auth.conf
        out, _err = util.subp(
            ["apt-config", "shell", "key", APT_CONFIG_AUTH_FILE]
        )
        return out.split("'")[1].rstrip("/")


def find_apt_list_files(repo_url, series):
    """List any apt files in APT_CONFIG_LISTS_DIR given repo_url and series."""
    _protocol, repo_path = repo_url.split("://")
    if repo_path.endswith("/"):  # strip trailing slash
        repo_path = repo_path[:-1]
    lists_dir = "/var/lib/apt/lists"
    out, _err = util.subp(["apt-config", "shell", "key", APT_CONFIG_LISTS_DIR])
    if out:  # then lists dir is present in config
        lists_dir = out.split("'")[1]

    aptlist_filename = repo_path.replace("/", "_")
    return sorted(
        glob.glob(
            os.path.join(
                lists_dir, aptlist_filename + "_dists_{}*".format(series)
            )
        )
    )


def remove_apt_list_files(repo_url, series):
    """Remove any apt list files present for this repo_url and series."""
    for path in find_apt_list_files(repo_url, series):
        if os.path.exists(path):
            os.unlink(path)


def clean_apt_files(*, _entitlements=None):
    """
    Clean apt files written by uaclient

    :param _entitlements:
        The uaclient.entitlements module to use, defaults to
        uaclient.entitlements. (This is only present for testing, because the
        import happens within the function to avoid circular imports.)
    """
    from uaclient.entitlements.repo import RepoEntitlement

    if _entitlements is None:
        from uaclient import entitlements as _entitlements

    for ent_cls in _entitlements.ENTITLEMENT_CLASSES:
        if not issubclass(ent_cls, RepoEntitlement):
            continue
        repo_file = ent_cls.repo_list_file_tmpl.format(name=ent_cls.name)
        pref_file = ent_cls.repo_pref_file_tmpl.format(name=ent_cls.name)

        if os.path.exists(repo_file):
            logging.info("Removing apt source file: %s", repo_file)
            os.unlink(repo_file)

        if os.path.exists(pref_file):
            logging.info("Removing apt preferences file: %s", pref_file)
            os.unlink(pref_file)


def get_installed_packages() -> List[str]:
    out, _ = util.subp(["dpkg-query", "-W", "--showformat=${Package}\\n"])
    return out.splitlines()


def setup_apt_proxy(
    http_proxy: Optional[str] = None, https_proxy: Optional[str] = None
) -> None:
    """
    Writes an apt conf file that configures apt to use the proxies provided as
    args.
    If both args are None, then no apt conf file is written. If this function
    previously wrote a conf file, and was run again with both args as None,
    the existing file is removed.

    :param http_proxy: the url of the http proxy apt should use, or None
    :param https_proxy: the url of the https proxy apt should use, or None
    :return: None
    """
    if http_proxy or https_proxy:
        event.info(messages.SETTING_SERVICE_PROXY.format(service="APT"))

    apt_proxy_config = ""
    if http_proxy:
        apt_proxy_config += APT_CONFIG_PROXY_HTTP.format(proxy_url=http_proxy)
    if https_proxy:
        apt_proxy_config += APT_CONFIG_PROXY_HTTPS.format(
            proxy_url=https_proxy
        )
    if apt_proxy_config != "":
        apt_proxy_config = messages.APT_PROXY_CONFIG_HEADER + apt_proxy_config

    if apt_proxy_config == "":
        util.remove_file(APT_PROXY_CONF_FILE)
    else:
        util.write_file(APT_PROXY_CONF_FILE, apt_proxy_config)
