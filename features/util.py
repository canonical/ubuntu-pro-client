import datetime
import hashlib
import logging
import os
import re
import shutil
import subprocess
import tempfile
from enum import Enum
from typing import Callable, Iterable, List, Optional

import yaml

SUT = "system-under-test"
LXC_PROPERTY_MAP = {
    "image": {"series": "properties.release", "machine_type": "Type"},
    "container": {"series": "image.release", "machine_type": "image.type"},
}
UA_TMP_DIR = os.path.join(tempfile.gettempdir(), "uaclient-behave")
SOURCE_PR_TGZ = os.path.join(UA_TMP_DIR, "pr_source.tar.gz")
SOURCE_PR_UNTAR_DIR = os.path.join(UA_TMP_DIR, "behave-ua-src")
SBUILD_DIR = os.path.join(UA_TMP_DIR, "sbuild")
UA_DEB_BUILD_CACHE = os.path.join(UA_TMP_DIR, "deb-cache")


class InstallationSource(Enum):
    ARCHIVE = "archive"
    PREBUILT = "prebuilt"
    LOCAL = "local"
    DAILY = "daily"
    STAGING = "staging"
    STABLE = "stable"
    PROPOSED = "proposed"
    CUSTOM = "custom"


def lxc_get_property(name: str, property_name: str, image: bool = False):
    """Check series name of either an image or a container.

    :param name:
        The name of the container or the image to check its series.
    :param property_name:
        The name of the property to return.
    :param image:
        If image==True will check image properties
        If image==False it will check container configuration to get
        properties.

    :return:
        The value of the container or image property.
       `None` if it could not detect it (
           some images don't have this field in properties).
    """
    if not image:
        property_name = LXC_PROPERTY_MAP["container"][property_name]
        output = subprocess.check_output(
            ["lxc", "config", "get", name, property_name],
            universal_newlines=True,
        )
        return output.rstrip()
    else:
        property_keys = LXC_PROPERTY_MAP["image"][property_name].split(".")
        output = subprocess.check_output(
            ["lxc", "image", "show", name], universal_newlines=True
        )
        image_config = yaml.safe_load(output)
        logging.info("--- `lxc image show` output: ", image_config)
        value = image_config
        for key_name in property_keys:
            value = image_config.get(value, {})
        if not value:
            logging.info(
                "--- Could not detect image property {name}."
                " Add it via `lxc image edit`".format(
                    name=".".join(property_keys)
                )
            )
            return None
        return value


def repo_state_hash(
    exclude_dirs: Iterable[str] = (
        ".github",
        "demo",
        "features",
        "sru",
        "tools",
        "docs",
        "dev-docs",
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


def build_debs(series: str, chroot: Optional[str] = None) -> List[str]:
    """
    Build the package through sbuild and store the debs into
    output_deb_dir

    :param series: The target series to build the package for
    :param output_deb_dir: the target directory in which to copy deb artifacts

    :return: A list of file paths to debs created by the build.
    """
    deb_prefix = "{}-{}-".format(series, repo_state_hash())
    tools_deb_name = "{}ubuntu-advantage-tools.deb".format(deb_prefix)
    pro_deb_name = "{}ubuntu-advantage-pro.deb".format(deb_prefix)
    tools_deb_cache_path = os.path.join(UA_DEB_BUILD_CACHE, tools_deb_name)
    pro_deb_cache_path = os.path.join(UA_DEB_BUILD_CACHE, pro_deb_name)

    if not os.path.exists(UA_DEB_BUILD_CACHE):
        os.makedirs(UA_DEB_BUILD_CACHE)

    if os.path.exists(tools_deb_cache_path) and os.path.exists(
        pro_deb_cache_path
    ):
        logging.info(
            "--- Using debs in cache: {} and {}".format(
                tools_deb_cache_path, pro_deb_cache_path
            )
        )
        return [tools_deb_cache_path, pro_deb_cache_path]

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

    curr_dir = os.getcwd()
    os.chdir(SBUILD_DIR)

    sbuild_cmd = [
        "sbuild",
        "--no-run-lintian",
        "--resolve-alternatives",
        "--no-clean-source",
        "--arch",
        "amd64",
        "-d",
        series,
        SOURCE_PR_UNTAR_DIR,
    ]
    if chroot is not None:
        sbuild_cmd += ["--chroot", chroot]
    else:
        # use ua-series-arch chroot if present
        ua_chroot = "ua-{}-amd64".format(series)
        proc = subprocess.run(
            ["schroot", "--info", "--chroot", ua_chroot],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            sbuild_cmd += ["--chroot", ua_chroot]

    logging.info('--- Running "{}"'.format(" ".join(sbuild_cmd)))
    subprocess.run(
        sbuild_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    logging.info("--- Successfully ran sbuild")
    os.chdir(curr_dir)

    for f in os.listdir(SBUILD_DIR):
        if f.endswith(".deb"):
            if "pro" in f:
                dest = pro_deb_cache_path
            elif "tools" in f:
                dest = tools_deb_cache_path
            else:
                continue
            shutil.copy(os.path.join(SBUILD_DIR, f), dest)

    return [tools_deb_cache_path, pro_deb_cache_path]


class SafeLoaderWithoutDatetime(yaml.SafeLoader):
    yaml_implicit_resolvers = {
        k: [r for r in v if r[0] != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


def _replace_and_log(s, old, new, logger_fn):
    logger_fn('replacing "{}" with "{}"'.format(old, new))
    return s.replace(old, new)


def process_template_vars(
    context, template: str, logger_fn: Optional[Callable] = None
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
        elif function_name == "cloud":
            processed_template = _replace_and_log(
                processed_template,
                match.group(0),
                context.pro_config.cloud,
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
            processed_template = _replace_and_log(
                processed_template,
                match.group(0),
                context.pro_config.contract_token_staging,
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
