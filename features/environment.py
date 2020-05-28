import datetime
import os
import subprocess
import textwrap
from typing import Dict, Optional, Union

from behave.model import Feature, Scenario

from behave.runner import Context

from features.util import (
    launch_lxd_container,
    lxc_exec,
    lxc_get_series,
    lxc_build_deb,
)

PR_DEB_FILE = "/tmp/ubuntu-advantage.deb"

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
        fresh image for this test run.   If specified, this image will not be
        deleted.
    :param destroy_instances:
        This boolean indicates that test containers should be destroyed after
        the completion. Set to False to leave instances running.
    """

    prefix = "UACLIENT_BEHAVE_"

    # These variables are used in .from_environ() to convert the string
    # environment variable input to the appropriate Python types for use within
    # the test framework
    boolean_options = ["build_pr", "image_clean", "destroy_instances"]
    str_options = ["contract_token", "reuse_image"]
    redact_options = ["contract_token"]

    # This variable is used in .from_environ() but also to emit the "Config
    # options" stanza in __init__
    all_options = boolean_options + str_options

    def __init__(
        self,
        *,
        build_pr: bool = False,
        image_clean: bool = True,
        destroy_instances: bool = True,
        reuse_image: str = None,
        contract_token: str = None
    ) -> None:
        # First, store the values we've detected
        self.build_pr = build_pr
        self.contract_token = contract_token
        self.image_clean = image_clean
        self.destroy_instances = destroy_instances
        self.reuse_image = reuse_image

        # Next, perform any required validation
        if self.reuse_image is not None:
            if self.image_clean:
                print(" Reuse_image specified, it will not be deleted.")

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
    """behave will invoke this before anything else happens."""
    userdata = context.config.userdata
    context.series_image_name = {}
    context.series_reuse_image = ""
    context.reuse_container = {}
    context.config = UAClientBehaveConfig.from_environ()

    print(
        "\n\n ***** build_pr from travis: ",
        os.environ.get("UACLIENT_BEHAVE_BUILD_PR"),
    )

    if context.config.reuse_image:
        series = lxc_get_series(context.config.reuse_image, image=True)
        if series is not None:
            context.series_reuse_image = series
            context.series_image_name[series] = context.config.reuse_image
        else:
            print(" Could not check image series. It will not be used. ")
            context.config.reuse_image = None

    if userdata.get("reuse_container"):
        series = lxc_get_series(userdata.get("reuse_container"))
        context.reuse_container = {series: userdata.get("reuse_container")}
        print(
            textwrap.dedent(
                """
            You are providing a {series} container. Make sure you are running
            this series tests. For instance: --tags=series.{series}""".format(
                    series=series
                )
            )
        )


def before_feature(context: Context, feature: Feature):
    for tag in feature.tags:
        parts = tag.split(".")
        if parts[0] == "uses":
            val = context
            for attr in parts[1:]:
                val = getattr(val, attr, None)
                if val is None:
                    feature.skip(
                        reason="Skipped because tag value was None: {}".format(
                            tag
                        )
                    )


def before_scenario(context: Context, scenario: Scenario):
    """
    In this function, we launch a container, install ubuntu-advantage-tools and
    then capture an image. This image is then reused by each scenario, reducing
    test execution time.
    """
    for tag in scenario.effective_tags:
        parts = tag.split(".")
        if parts[0] == "series":
            series = parts[1]
            if series not in context.series_image_name:
                create_uat_lxd_image(context, series)


def after_all(context):
    if context.config.image_clean:
        for key, image in context.series_image_name.items():
            if key == context.series_reuse_image:
                print(
                    " Not deleting this image: ",
                    context.series_image_name[key],
                )
            else:
                subprocess.run(["lxc", "image", "delete", image])


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


def create_uat_lxd_image(context: Context, series: str) -> None:
    """Create a given series lxd image with ubuntu-advantage-tools installed

    This will launch a container, install ubuntu-advantage-tools, and publish
    the image.    The image's name is stored in context.series_image_name for
    use within step code.

    :param context:
        A `behave.runner.Context`;  this will have `series.image_name` set on
        it.
    :param series:
       A string representing the series name to create
    """

    if series in context.reuse_container:
        print(
            "\n Reusing the existing container: ",
            context.reuse_container[series],
        )
        return
    now = datetime.datetime.now()
    ubuntu_series = "ubuntu-daily:%s" % series
    deb_file = None
    if context.config.build_pr:
        # create a dirty development image which installs build depends
        deb_file = PR_DEB_FILE
        build_container_name = (
            "behave-image-pre-build-%s-" % series + now.strftime("%s%f")
        )
        launch_lxd_container(context, ubuntu_series, build_container_name)
        lxc_build_deb(build_container_name, output_deb_file=deb_file)

    build_container_name = "behave-image-build-%s-" % series + now.strftime(
        "%s%f"
    )

    launch_lxd_container(context, ubuntu_series, build_container_name)

    # if build_pr it will install new built .deb
    _install_uat_in_container(build_container_name, deb_file=deb_file)

    context.series_image_name[
        series
    ] = "behave-image-%s-" % series + now.strftime("%s%f")

    _capture_container_as_image(
        build_container_name, context.series_image_name[series]
    )


def _install_uat_in_container(
    container_name: str, deb_file: 'Optional[str]'
) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_name:
        The name of the container into which ubuntu-advantage-tools should be
        installed.
    :param deb_file: Optional path to the deb_file we need to install
    """
    if deb_file:
        subprocess.run(
            [
                "lxc",
                "file",
                "push",
                deb_file,
                container_name + "/tmp/",
            ]
        )
        lxc_exec(container_name,["sudo", "dpkg", "-i", deb_file])
        lxc_exec(
            container_name, ["apt-cache", "policy", "ubuntu-advantage-tools"]
        )
    else:
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
            [
                "sudo",
                "apt-get",
                "install",
                "-qq",
                "-y",
                "ubuntu-advantage-tools",
            ],
        )
