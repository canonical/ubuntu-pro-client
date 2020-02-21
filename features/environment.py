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

    :param contract_token:
        A valid contract token to use during attach scenarios
    :param image_clean:
        This indicates whether the image created for this test run should be
        cleaned up when all tests are complete.
    :param reuse_image:
        A string with an image name that should be used instead of building a
        fresh image for this test run.  If specified, image_clean will be set
        to False.
    :param destroy_instances:
        This boolean indicates that test containers should be destroyed after
        the completion. Set to False to leave instances running.
    """

    prefix = "UACLIENT_BEHAVE_"

    # These variables are used in .from_environ() to convert the string
    # environment variable input to the appropriate Python types for use within
    # the test framework
    boolean_options = ["image_clean", "destroy_instances"]
    str_options = ["contract_token", "reuse_image"]
    redact_options = ["contract_token"]

    # This variable is used in .from_environ() but also to emit the "Config
    # options" stanza in __init__
    all_options = boolean_options + str_options + redact_options

    def __init__(
        self,
        *,
        image_clean: bool = True,
        reuse_image: str = None,
        destroy_instances: bool = True
        contract_token: str = None,
        reuse_image: str = None
    ) -> None:
        # First, store the values we've detected
        self.contract_token = contract_token
        self.image_clean = image_clean
        self.destroy_instances = destroy_instances
        self.reuse_image = reuse_image

        # Next, perform any required validation
        if self.reuse_image is not None:
            if self.image_clean:
                print("reuse_image specified, setting image_clean = False")
                self.image_clean = False

        # Finally, print the config options.  This helps users debug the use of
        # config options, and means they'll be included in test logs in CI.
        print("Config options:")
        for option in self.all_options:
            value = getattr(self, option, "ERROR")
            if option in self.redact_options and value not in (None, "ERROR"):
                value = "<REDACTED>"
            print("  {}".format(option), "=", value)

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
    if context.config.reuse_image is None:
        create_trusty_uat_lxd_image(context)
    else:
        context.image_name = context.config.reuse_image


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
            "sudo",
            "add-apt-repository",
            "--yes",
            "ppa:canonical-server/ua-client-daily",
        ],
    )
    lxc_exec(container_name, ["sudo", "apt-get", "update", "-qq"])
    lxc_exec(
        container_name,
        ["sudo", "apt-get", "install", "-qq", "-y", "ubuntu-advantage-tools"],
    )
