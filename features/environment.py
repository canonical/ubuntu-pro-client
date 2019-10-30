import datetime
import os
import subprocess
from typing import Dict, Union

from behave.runner import Context

from features.util import launch_lxd_container, lxc_exec


class UAClientBehaveConfig:
    """Store config options for UA client behave test runs.

    This captures the configuration in one place, so that we have a single
    source of truth for test configuration (rather than having environment
    variable handling throughout the test code).

    :param image_clean:
        This indicates whether the image created for this test run should be
        cleaned up when all tests are complete.
    """

    prefix = "UACLIENT_BEHAVE_"

    # These variables are used in .from_environ() to convert the string
    # environment variable input to the appropriate Python types for use within
    # the test framework
    boolean_options = ["image_clean"]

    # This variable is used in .from_environ() but also to emit the "Config
    # options" stanza in __init__
    all_options = boolean_options

    def __init__(self, *, image_clean: bool = True) -> None:
        self.image_clean = image_clean

        print("Config options:")
        for option in self.all_options:
            print("  {}".format(option), "=", getattr(self, option, "ERROR"))

    @classmethod
    def from_environ(cls) -> "UAClientBehaveConfig":
        """Gather config options from os.environ and return a config object"""
        # First, gather all known options
        kwargs: Dict[str, Union[str, bool]] = {}
        for key, value in os.environ.items():
            if not key.startswith(cls.prefix):
                continue
            our_key = key[len(cls.prefix) :].lower()
            if our_key not in cls.all_options:
                print("Unknown config environment variable:", key)
                continue
            kwargs[our_key] = value

        # Next, sanitise the non-string options to Python types
        for key in cls.boolean_options:
            bool_value = True  # Default to True
            if key in kwargs:
                if kwargs[key] == "0":
                    bool_value = False
                kwargs[key] = bool_value
        return cls(**kwargs)  # type: ignore


def before_all(context: Context) -> None:
    """behave will invoke this before anything else happens.

    In this function, we launch a container, install ubuntu-advantage-tools and
    then capture an image.  This image is then reused by each feature, reducing
    test execution time.
    """
    context.config = UAClientBehaveConfig.from_environ()
    create_trusty_uat_lxd_image(context)


def _capture_container_as_image(container_name: str, image_name: str) -> None:
    """Capture a lxd container as an image.

    :param container_name:
        The name of the container to be captured.  Note that this container
        will be stopped.
    :param image_name:
        The name under which the image should be published.
    """
    subprocess.run(["lxc", "stop", container_name])
    subprocess.run(["lxc", "publish", container_name, "--alias", image_name])


def create_trusty_uat_lxd_image(context: Context) -> None:
    """Create a trusty lxd image with ubuntu-advantage-tools installed

    This will launch a container, install ubuntu-advantage-tools, and publish
    the image.  The image's name is stored in context.image_name for use within
    step code.

    :param context:
        A `behave.runner.Context`; this will have `image_name` set on it.
    """
    now = datetime.datetime.now()
    context.image_name = "behave-image-" + now.strftime("%s%f")
    build_container_name = "behave-image-build-" + now.strftime("%s%f")

    launch_lxd_container(context, "ubuntu:trusty", build_container_name)
    _install_uat_in_container(build_container_name)
    _capture_container_as_image(build_container_name, context.image_name)

    def image_cleanup() -> None:
        if context.config.image_clean:
            subprocess.run(["lxc", "image", "delete", context.image_name])
        else:
            print("Image cleanup disabled, not deleting:", context.image_name)

    context.add_cleanup(image_cleanup)


def _install_uat_in_container(container_name: str) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_name:
        The name of the container into which ubuntu-advantage-tools should be
        installed.
    """
    lxc_exec(
        container_name,
        [
            "add-apt-repository",
            "--yes",
            "ppa:canonical-server/ua-client-daily",
        ],
    )
    lxc_exec(container_name, ["apt-get", "update", "-qq"])
    lxc_exec(
        container_name,
        ["apt-get", "install", "-qq", "-y", "ubuntu-advantage-tools"],
    )
