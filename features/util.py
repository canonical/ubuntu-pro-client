import datetime
import glob
import hashlib
import hmac
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from base64 import b64encode
from dataclasses import dataclass
from enum import Enum
from typing import (  # noqa: F401
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
)
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

from uaclient.system import get_dpkg_arch

SUT = "sut"  # system under test
BUILDER_NAME_PREFIX = "builder-"
UA_TMP_DIR = os.path.join(tempfile.gettempdir(), "uaclient-behave")
SOURCE_PR_TGZ = os.path.join(UA_TMP_DIR, "pr_source.tar.gz")
SOURCE_PR_UNTAR_DIR = os.path.join(UA_TMP_DIR, "behave-ua-src")
SBUILD_DIR = os.path.join(UA_TMP_DIR, "sbuild")
UA_DEB_BUILD_CACHE = os.path.join(UA_TMP_DIR, "deb-cache")


ALL_BINARY_PACKAGE_NAMES = [
    "ubuntu-pro-client",
    "ubuntu-pro-client-l10n",
    "ubuntu-pro-auto-attach",
    "ubuntu-advantage-tools",
    "ubuntu-advantage-pro",
]
NORMAL_BINARY_PACKAGE_NAMES = [
    "ubuntu-pro-client",
    "ubuntu-pro-client-l10n",
    "ubuntu-advantage-tools",
]


@dataclass
class ProDebPaths:
    ubuntu_pro_client: str
    ubuntu_pro_image_auto_attach: str
    ubuntu_pro_client_l10n: str
    ubuntu_advantage_tools: str
    ubuntu_advantage_pro: str

    def non_cloud_pro_image_debs(self, series: str) -> List[Tuple[str, str]]:
        if series in ("xenial", "bionic", "focal", "jammy"):
            return [
                ("ubuntu-pro-client", self.ubuntu_pro_client),
                ("ubuntu-advantage-tools", self.ubuntu_advantage_tools),
                ("ubuntu-pro-client-l10n", self.ubuntu_pro_client_l10n),
            ]
        else:
            return [
                ("ubuntu-pro-client", self.ubuntu_pro_client),
                ("ubuntu-pro-client-l10n", self.ubuntu_pro_client_l10n),
            ]

    def cloud_pro_image_debs(self) -> List[Tuple[str, str]]:
        return [
            (
                "ubuntu-pro-auto-attach",
                self.ubuntu_pro_image_auto_attach,
            ),
            ("ubuntu-advantage-pro", self.ubuntu_advantage_pro),
        ]

    def all_debs(self, series: str) -> List[Tuple[str, str]]:
        return (
            self.non_cloud_pro_image_debs(series) + self.cloud_pro_image_debs()
        )


class InstallationSource(Enum):
    ARCHIVE = "archive"
    PREBUILT = "prebuilt"
    LOCAL = "local"
    DAILY = "daily"
    STAGING = "staging"
    STABLE = "stable"
    PROPOSED = "proposed"
    CUSTOM = "custom"


def repo_state_hash(
    exclude_dirs: Iterable[str] = (
        ".github",
        "demo",
        "features",
        "sru",
        "tools",
        "docs",
        "dev-docs",
        "keyrings",
    )
):
    """
    Generate a string that represents the current local state of
    the git repository.

    This takes (1) the latest commit hash, which represents the committed
    state, (2) the `git diff`, which includes all local changes, and (3)
    the contents of new files not yet committed, and concatenates them.
    Then it generates the md5 hash of the concatenated result.

    By doing so, the result is a unique-enough string that shouldn't
    collide with any other local state in our lifetimes. We can then
    include this string in the name of a build and reuse that build if
    the repo state doesn't change.

    :param exclude_dirs: When non-empty, we exclude all folders in the list
        from the git diff and from the new_file_content. With the default
        value, we don't include any changes to integration tests or other
        unrelated scripts and files in the git repo when generating our local
        state hash. This is useful when iterating on an integration test or
        manual test script because you won't have to re-sbuild if you don't
        change the actual source code of the package.

    :return: A unique string representing the current local state of the
        git repository
    """
    git_rev_cmd = ["git", "rev-parse", "HEAD"]
    rev_out = subprocess.check_output(git_rev_cmd)

    git_diff_cmd = ["git", "diff"]
    exclude_set = set(exclude_dirs)
    if len(exclude_set) > 0:
        files_and_folders_set = set(os.listdir("."))
        filtered_files_and_folders = files_and_folders_set - exclude_set
        git_diff_cmd += ["--", *filtered_files_and_folders]
    diff_out = subprocess.check_output(git_diff_cmd)

    git_status_cmd = ["git", "status", "--porcelain"]
    status_out = subprocess.check_output(git_status_cmd).decode("utf-8")
    status_lines = status_out.split("\n")
    new_files = [name[3:] for name in status_lines if name.startswith("?? ")]
    new_file_content = ""
    for fname in new_files:
        exclude = False
        for exclude_dir in exclude_dirs:
            if fname.startswith(exclude_dir):
                exclude = True
                break
        if exclude:
            continue
        if os.path.isdir(fname):
            continue
        with open(fname) as f:
            new_file_content += f.read()

    output_to_hash = rev_out + diff_out + new_file_content.encode("utf-8")
    return hashlib.md5(output_to_hash).hexdigest()


def get_debs_for_series(debs_path: str, series: str) -> ProDebPaths:
    ubuntu_pro_client = ""
    ubuntu_pro_client_l10n = ""
    ubuntu_pro_image_auto_attach = ""
    ubuntu_advantage_tools = ""
    ubuntu_advantage_pro = ""
    for deb_file in os.listdir(debs_path):
        if series in deb_file:
            full_path = os.path.join(debs_path, deb_file)
            if "ubuntu-pro-client-l10n" in deb_file:
                ubuntu_pro_client_l10n = full_path
            elif "ubuntu-pro-client" in deb_file:
                ubuntu_pro_client = full_path
            elif "ubuntu-pro-auto-attach" in deb_file:
                ubuntu_pro_image_auto_attach = full_path
            elif "ubuntu-advantage-tools" in deb_file:
                ubuntu_advantage_tools = full_path
            elif "ubuntu-advantage-pro" in deb_file:
                ubuntu_advantage_pro = full_path
    return ProDebPaths(
        ubuntu_pro_client=ubuntu_pro_client,
        ubuntu_pro_client_l10n=ubuntu_pro_client_l10n,
        ubuntu_pro_image_auto_attach=ubuntu_pro_image_auto_attach,
        ubuntu_advantage_tools=ubuntu_advantage_tools,
        ubuntu_advantage_pro=ubuntu_advantage_pro,
    )


def _create_deb_path(prefix: str, name: str):
    return os.path.join(UA_DEB_BUILD_CACHE, "{}{}.deb".format(prefix, name))


def build_debs(
    series: str,
    architecture: Optional[str] = None,
    chroot: Optional[str] = None,
    sbuild_output_to_terminal: bool = False,
) -> ProDebPaths:
    """
    Build the package through sbuild and store the debs into
    output_deb_dir

    :param series: The target series to build the package for
    :param output_deb_dir: the target directory in which to copy deb artifacts

    :return: A list of file paths to debs created by the build.
    """
    if architecture is None:
        architecture = get_dpkg_arch()

    deb_prefix = "{}-{}-{}-".format(series, architecture, repo_state_hash())
    deb_paths = ProDebPaths(
        ubuntu_pro_client=_create_deb_path(deb_prefix, "ubuntu-pro-client"),
        ubuntu_pro_image_auto_attach=_create_deb_path(
            deb_prefix, "ubuntu-pro-auto-attach"
        ),
        ubuntu_pro_client_l10n=_create_deb_path(
            deb_prefix, "ubuntu-pro-client-l10n"
        ),
        ubuntu_advantage_tools=_create_deb_path(
            deb_prefix, "ubuntu-advantage-tools"
        ),
        ubuntu_advantage_pro=_create_deb_path(
            deb_prefix, "ubuntu-advantage-pro"
        ),
    )

    if not os.path.exists(UA_DEB_BUILD_CACHE):
        os.makedirs(UA_DEB_BUILD_CACHE)

    if os.path.exists(deb_paths.ubuntu_pro_client):
        logging.info("--- Using debs in cache")
        return deb_paths

    logging.info("--- Creating: {}".format(SOURCE_PR_TGZ))

    cwd = os.getcwd()
    os.chdir("..")
    subprocess.run(
        [
            "tar",
            "-zcf",
            SOURCE_PR_TGZ,
            "--exclude-vcs",
            "--exclude-vcs-ignores",
            os.path.basename(cwd),
        ],
        check=True,
    )
    os.chdir(cwd)

    logging.info("--- Creating: {}".format(SOURCE_PR_UNTAR_DIR))

    # Delete cached folder for pro code
    if os.path.exists(SOURCE_PR_UNTAR_DIR):
        shutil.rmtree(SOURCE_PR_UNTAR_DIR)

    os.makedirs(SOURCE_PR_UNTAR_DIR)
    subprocess.run(
        [
            "tar",
            "-xvf",
            SOURCE_PR_TGZ,
            "-C",
            SOURCE_PR_UNTAR_DIR,
            "--strip-components=1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    if os.path.exists(SBUILD_DIR):
        shutil.rmtree(SBUILD_DIR)
    os.makedirs(SBUILD_DIR)

    sbuild_cmd = [
        "sbuild",
        "--chroot-mode",
        "schroot",
        "--no-run-lintian",
        "--resolve-alternatives",
        "--no-clean-source",
        "--build-dir",
        SBUILD_DIR,
        "--arch",
        architecture,
        "-d",
        series,
        SOURCE_PR_UNTAR_DIR,
    ]
    if chroot is not None:
        sbuild_cmd += ["--chroot", chroot]
    else:
        # use ua-series-arch chroot if present
        ua_chroot = "ua-{}-{}".format(series, architecture)
        proc = subprocess.run(
            ["schroot", "--info", "--chroot", ua_chroot],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            sbuild_cmd += ["--chroot", ua_chroot]

    # disable unit-test during sbuild
    env = os.environ.copy()
    env["DEB_BUILD_OPTIONS"] = env.get("DEB_BUILD_OPTIONS", "") + " nocheck"

    logging.info('--- Running "{}"'.format(" ".join(sbuild_cmd)))
    sbuild_out = subprocess.DEVNULL  # type: Optional[int]
    if sbuild_output_to_terminal:
        sbuild_out = sys.stderr.fileno()

    try:
        subprocess.run(
            sbuild_cmd,
            env=env,
            stdout=sbuild_out,
            stderr=sbuild_out,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error("--- Error running sbuild")
        pattern = os.path.join(
            SBUILD_DIR, "ubuntu-advantage-tools_*_amd64.build"
        )
        sbuild_log = [f for f in glob.glob(pattern)]

        if sbuild_log:
            with open(sbuild_log[0], "r") as sbuild_log_file:
                logging.error("%s", sbuild_log_file.read())

        raise e

    logging.info("--- Successfully ran sbuild")

    for f in os.listdir(SBUILD_DIR):
        if f.endswith(".deb"):
            if "ubuntu-pro-client-l10n" in f:
                dest = deb_paths.ubuntu_pro_client_l10n
            elif "ubuntu-pro-client" in f:
                dest = deb_paths.ubuntu_pro_client
            elif "ubuntu-pro-auto-attach" in f:
                dest = deb_paths.ubuntu_pro_image_auto_attach
            elif "ubuntu-advantage-tools" in f:
                dest = deb_paths.ubuntu_advantage_tools
            elif "ubuntu-advantage-pro" in f:
                dest = deb_paths.ubuntu_advantage_pro
            else:
                continue
            shutil.copy(os.path.join(SBUILD_DIR, f), dest)

    return deb_paths


class SafeLoaderWithoutDatetime(yaml.SafeLoader):
    yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


REDACTED = "<REDACTED>"


def redaction_markers(
    secrets: Mapping[str, Optional[str]],
) -> List[Tuple[str, str]]:
    """Pair each set secret value with the marker that replaces it.

    ``secrets`` maps option names to values. The marker names every option
    that holds the value, e.g. ``<REDACTED:contract_token>``. Longer values
    come first, so a value that contains another is replaced whole.
    """
    names_by_value = {}  # type: Dict[str, List[str]]
    for name, value in secrets.items():
        if value:
            names_by_value.setdefault(value, []).append(name)
    markers = [
        (value, "<REDACTED:{}>".format(",".join(sorted(names))))
        for value, names in names_by_value.items()
    ]
    return sorted(markers, key=lambda marker: len(marker[0]), reverse=True)


def redact(text: str, markers: Iterable[Tuple[str, str]]) -> str:
    """Return text with each secret value replaced by its marker."""
    for value, marker in markers:
        text = text.replace(value, marker)
    return text


class RedactingRecordFactory:
    """Log record factory that replaces secret values with markers.

    It wraps the previous factory and redacts each record as it is made,
    before any filter or handler sees it. This covers every logger and
    every handler, including handlers added later, such as behave's log
    capture.

    Every handler gets the changed record:

    - ``msg`` is the formatted, redacted message, and ``args`` is empty.
    - ``exc_text`` is the redacted traceback, and ``exc_info`` is None.
      ``logging.Formatter`` prints ``exc_text``. A formatter that renders
      ``exc_info`` itself prints no traceback.
    - ``stack_info`` is redacted.

    Dropping ``args`` and ``exc_info`` is a deliberate compromise: they
    hold the unredacted values, so any handler or formatter that read them
    could log a secret. Handlers lose the raw values and the exception
    object in exchange.

    Attributes passed with ``extra=`` are not redacted. If the args don't
    match the format string, ``msg`` is the format string followed by the
    args.
    """

    def __init__(
        self, make_record: Callable, markers: List[Tuple[str, str]]
    ) -> None:
        self.make_record = make_record
        self.markers = markers

    def __call__(self, *args, **kwargs) -> logging.LogRecord:
        record = self.make_record(*args, **kwargs)
        try:
            message = record.getMessage()
        except Exception:
            message = "{} {}".format(record.msg, record.args)
        record.msg = redact(message, self.markers)
        record.args = ()
        if record.exc_info:
            record.exc_text = redact(
                logging.Formatter().formatException(record.exc_info),
                self.markers,
            )
            record.exc_info = None
        if record.stack_info:
            record.stack_info = redact(record.stack_info, self.markers)
        return record


def install_log_redaction(secrets: Mapping[str, Optional[str]]) -> None:
    """Redact secrets from every log record made after this call.

    ``secrets`` maps option names to values. If no value is set, the
    record factory is left as it is.
    """
    markers = redaction_markers(secrets)
    if markers:
        logging.setLogRecordFactory(
            RedactingRecordFactory(logging.getLogRecordFactory(), markers)
        )


def _replace_and_log(s, old, new, logger_fn):
    logger_fn('replacing "{}" with "{}"'.format(old, new))
    return s.replace(old, new)


def process_template_vars(
    context, template: str, logger_fn: Optional[Callable] = None, shown=False
) -> str:
    if logger_fn is None:
        logger_fn = logging.info

    processed_template = template

    for match in re.finditer(r"\$behave_var{([\w\s\-\+]*)}", template):
        args = match.group(1).split()
        function_name = args[0]
        if function_name == "version":
            if context.pro_config.check_version:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.pro_config.check_version,
                    logger_fn,
                )
        elif function_name == "machine-ip":
            if args[1] in context.machines:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.machines[args[1]].instance.ip,
                    logger_fn,
                )
        elif function_name == "machine-name":
            if args[1] in context.machines:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.machines[args[1]].instance.name,
                    logger_fn,
                )
        elif function_name == "cloud":
            if args[1] in context.machines:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.machines[args[1]].cloud,
                    logger_fn,
                )
        elif function_name == "today":
            dt = datetime.datetime.utcnow()
            if len(args) == 2:
                offset = int(args[1])
                dt = dt + datetime.timedelta(days=offset)
            dt_str = dt.strftime("%Y-%m-%dT00:00:00Z")
            processed_template = _replace_and_log(
                processed_template,
                match.group(0),
                dt_str,
                logger_fn,
            )
        elif function_name == "contract_token_staging":
            if not shown:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.pro_config.contract_token_staging,
                    logger_fn,
                )
        elif function_name == "contract_token":
            if not shown:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.pro_config.contract_token,
                    logger_fn,
                )
        elif function_name == "config":
            item = args[1]
            if not shown or item not in context.pro_config.redact_options:
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    getattr(context.pro_config, item),
                    logger_fn,
                )
        elif function_name == "stored_var":
            if context.stored_vars.get(args[1]):
                processed_template = _replace_and_log(
                    processed_template,
                    match.group(0),
                    context.stored_vars.get(args[1]),
                    logger_fn,
                )

    return processed_template


def _landscape_api_request(access_key, secret_key, action, action_params):
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    params = {
        "action": action,
        "access_key_id": access_key,
        "signature_method": "HmacSHA256",
        "signature_version": "2",
        "timestamp": timestamp,
        "version": "2011-08-01",
        **action_params,
    }
    method = "GET"
    host = "landscape.canonical.com"
    path = "/api/"

    formatted_params = "&".join(
        quote(k, safe="~") + "=" + quote(v, safe="~")
        for k, v in sorted(params.items())
    )

    to_sign = "{method}\n{host}\n{path}\n{formatted_params}".format(
        method=method,
        host=host,
        path=path,
        formatted_params=formatted_params,
    )
    digest = hmac.new(
        secret_key.encode(), to_sign.encode(), hashlib.sha256
    ).digest()
    signature = b64encode(digest)
    formatted_params += "&signature=" + quote(signature)

    uri = "https://{host}{path}?{params}".format(
        host=host, path=path, params=formatted_params
    )
    request = Request(
        uri,
        headers={"Host": host},
        method=method,
    )
    response = urlopen(request)

    return response.code, json.load(response)


def landscape_reject_all_pending_computers(context):
    access_key = context.pro_config.landscape_api_access_key
    secret_key = context.pro_config.landscape_api_secret_key
    code, pending_computers = _landscape_api_request(
        access_key, secret_key, "GetPendingComputers", {}
    )
    assert code == 200
    if len(pending_computers) > 0:
        reject_params = {
            "computer_ids.{}".format(i + 1): str(computer["id"])
            for i, computer in enumerate(pending_computers)
        }
        code, _resp = _landscape_api_request(
            access_key, secret_key, "RejectPendingComputers", reject_params
        )
        assert code == 200
