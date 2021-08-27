import logging
import multiprocessing
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
from contextlib import contextmanager
from typing import List

import yaml

LXC_PROPERTY_MAP = {
    "image": {"series": "properties.release", "machine_type": "Type"},
    "container": {"series": "image.release", "machine_type": "image.type"},
}
SLOW_CMDS = ["do-release-upgrade"]  # Commands which will emit dots on travis
SOURCE_PR_TGZ = os.path.join(tempfile.gettempdir(), "pr_source.tar.gz")
SOURCE_PR_UNTAR_DIR = os.path.join(tempfile.gettempdir(), "behave-ua")
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


def build_debs(
    series: str, output_deb_dir: str, cache_source: bool
) -> List[str]:
    """
    Build the package through sbuild and store the debs into
    output_deb_dir

    :param series: The target series to build the package for
    :param output_deb_dir: the target directory in which to copy deb artifacts
    :param cache_source: If False, we will always rebuild the source environemt
                         for sbuild

    :return: A list of file paths to debs created by the build.
    """
    logging.info("--- Creating: {}".format(SOURCE_PR_TGZ))
    temp_dir = tempfile.gettempdir()
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
            ]
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
        )

    curr_dir = os.getcwd()
    os.chdir(temp_dir)
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
    )
    logging.info("--- Successfully run sbuild")
    os.chdir(curr_dir)

    if not os.path.exists(output_deb_dir):
        os.makedirs(output_deb_dir)

    for tmp_file in os.listdir(os.path.dirname(SOURCE_PR_TGZ)):
        if tmp_file.endswith(".deb"):
            shutil.copy(os.path.join(temp_dir, tmp_file), output_deb_dir)

    return [
        os.path.join(output_deb_dir, deb_file)
        for deb_file in os.listdir(output_deb_dir)
    ]


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
