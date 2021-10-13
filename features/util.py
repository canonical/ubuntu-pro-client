import hashlib
import logging
import multiprocessing
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
from contextlib import contextmanager
from typing import Iterable, List

import yaml

LXC_PROPERTY_MAP = {
    "image": {"series": "properties.release", "machine_type": "Type"},
    "container": {"series": "image.release", "machine_type": "image.type"},
}
SLOW_CMDS = ["do-release-upgrade"]  # Commands which will emit dots on travis
UA_TMP_DIR = os.path.join(tempfile.gettempdir(), "uaclient-behave")
SOURCE_PR_TGZ = os.path.join(UA_TMP_DIR, "pr_source.tar.gz")
SOURCE_PR_UNTAR_DIR = os.path.join(UA_TMP_DIR, "behave-ua-src")
SBUILD_DIR = os.path.join(UA_TMP_DIR, "sbuild")
UA_DEB_BUILD_CACHE = os.path.join(UA_TMP_DIR, "deb-cache")
UA_DEBS = frozenset({"ubuntu-advantage-tools.deb", "ubuntu-advantage-pro.deb"})


BUILD_FROM_TGZ = textwrap.dedent(
    """\
   #!/bin/bash
   set -o xtrace
   apt-get update
   apt-get install make
   cd /tmp
   tar -zxf *gz
   cd *ubuntu-advantage-client*
   make deps
   dpkg-buildpackage -us -uc
   # Copy and rename versioned debs to /tmp/ubuntu-advantage-(tools|pro).deb
   cp /tmp/ubuntu-advantage-tools*.deb /tmp/ubuntu-advantage-tools.deb
   cp /tmp/ubuntu-advantage-pro*.deb /tmp/ubuntu-advantage-pro.deb
   """
)


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
        with open(fname) as f:
            new_file_content += f.read()

    output_to_hash = rev_out + diff_out + new_file_content.encode("utf-8")
    return hashlib.md5(output_to_hash).hexdigest()


def build_debs(series: str, cache_source: bool = False) -> List[str]:
    """
    Build the package through sbuild and store the debs into
    output_deb_dir

    :param series: The target series to build the package for
    :param output_deb_dir: the target directory in which to copy deb artifacts
    :param cache_source: If False, we will always rebuild the source environemt
                         for sbuild

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
    if not os.path.exists(os.path.dirname(SOURCE_PR_TGZ)):
        os.makedirs(os.path.dirname(SOURCE_PR_TGZ))

    if not os.path.exists(SOURCE_PR_TGZ) or not cache_source:
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
    if not os.path.exists(SOURCE_PR_UNTAR_DIR) or not cache_source:
        # Delete cached folder for ua code
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
    logging.info("--- Running sbuild")
    subprocess.run(
        [
            "sbuild",
            "--no-run-lintian",
            "--resolve-alternatives",
            "--no-clean-source",
            "--arch",
            "amd64",
            "-d",
            series,
            SOURCE_PR_UNTAR_DIR,
        ],
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


# Support for python 3.6 or earlier
@contextmanager
def nullcontext(enter_result=None):
    yield enter_result


def spinning_cursor():
    while True:
        for cursor in "|/-\\":
            yield cursor


@contextmanager
def emit_spinner_on_travis(msg: str = " "):
    """
    A context manager that emits a spinner updating 5 seconds if running on
    Travis.

    Travis will kill jobs that don't emit output for a certain amount of time.
    This context manager spins up a background process which will emit a char
    to stdout every 10 seconds to avoid being killed.

    It should be wrapped selectively around operations that are known to take a
    long time
    """
    if os.environ.get("TRAVIS") != "true":
        # If we aren't on Travis, don't do anything.
        yield
        return

    def emit_spinner():
        print(msg, end="", flush=True)
        spinner = spinning_cursor()
        while True:
            time.sleep(5)
            print("\b%s" % next(spinner), end="", flush=True)

    dot_process = multiprocessing.Process(target=emit_spinner)
    dot_process.start()
    try:
        yield
    finally:
        print()
        dot_process.terminate()
