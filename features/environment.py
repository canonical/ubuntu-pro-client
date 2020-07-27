import datetime
import os
import itertools
import subprocess
import textwrap
import logging
from typing import Dict, Optional, Union, List

from behave.model import Feature, Scenario

from behave.runner import Context

import pycloudlib  # type: ignore

from features.util import (
    launch_lxd_container,
    launch_ec2,
    lxc_exec,
    lxc_get_property,
    lxc_build_deb,
)

PR_DEB_FILE = "/tmp/ubuntu-advantage.deb"
ALL_SUPPORTED_SERIES = ["bionic", "focal", "trusty", "xenial"]

EC2_KEY_FILE = "uaclient.pem"

DAILY_PPA = "http://ppa.launchpad.net/canonical-server/ua-client-daily/ubuntu"

USERDATA_INSTALL_DAILY_PRO_UATOOLS = """\
#cloud-config
write_files:
  - path: /etc/ubuntu-advantage-client
    content: |
      features:
         disable_auto_attach: true
    append: true
apt:
  sources:
    ua-tools-daily:
        source: "deb {daily_ppa} $RELEASE main"
        keyid: 8A295C4FB8B190B7
packages: [ubuntu-advantage-tools, ubuntu-advantage-pro]
""".format(
    daily_ppa=DAILY_PPA
)


class UAClientBehaveConfig:
    """Store config options for UA client behave test runs.

    This captures the configuration in one place, so that we have a single
    source of truth for test configuration (rather than having environment
    variable handling throughout the test code).

    :param contract_token:
        A valid contract token to use during attach scenarios
    :param contract_token_staging:
        A valid staging contract token to use during attach scenarios
    :param image_clean:
        This indicates whether the image created for this test run should be
        cleaned up when all tests are complete.
    :param machine_type:
        The default machine_type to test: lxd.container, lxd.vm or pro.aws
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
    str_options = [
        "aws_access_key_id",
        "aws_secret_access_key",
        "contract_token",
        "contract_token_staging",
        "machine_type",
        "reuse_image",
    ]
    redact_options = [
        "aws_access_key_id",
        "aws_secret_access_key",
        "contract_token",
        "contract_token_staging",
    ]

    # This variable is used in .from_environ() but also to emit the "Config
    # options" stanza in __init__
    all_options = boolean_options + str_options

    ec2_api = None  # type: pycloudlib.EC2

    def __init__(
        self,
        *,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        build_pr: bool = False,
        image_clean: bool = True,
        destroy_instances: bool = True,
        machine_type: str = "lxd.container",
        reuse_image: str = None,
        contract_token: str = None,
        contract_token_staging: str = None,
        cmdline_tags: "List" = []
    ) -> None:
        # First, store the values we've detected
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.build_pr = build_pr
        self.contract_token = contract_token
        self.contract_token_staging = contract_token_staging
        self.image_clean = image_clean
        self.destroy_instances = destroy_instances
        self.machine_type = machine_type
        self.reuse_image = reuse_image
        self.cmdline_tags = cmdline_tags
        self.filter_series = set(
            [
                tag.split(".")[1]
                for tag in cmdline_tags
                if tag.startswith("series.")
            ]
        )
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
        has_aws_keys = bool(aws_access_key_id and aws_secret_access_key)
        if has_aws_keys and self.machine_type != "pro.aws":
            raise RuntimeError(
                "Must set UACLIENT_BEHAVE_MACHINE_TYPE=pro.aws if providing"
                " AWS keys"
            )

    @classmethod
    def from_environ(cls, config) -> "UAClientBehaveConfig":
        """Gather config options from os.environ and return a config object"""
        # First, gather all known options
        kwargs: Dict[str, Union[str, bool, "List"]] = {}
        # Preserve cmdline_tags for reference
        if not config.tags.ands:
            kwargs["cmdline_tags"] = []
        else:
            kwargs["cmdline_tags"] = list(
                itertools.chain.from_iterable(config.tags.ands)
            )
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
    context.config.setup_logging()
    userdata = context.config.userdata
    if userdata:
        print("Userdata key / value pairs:")
        for key, value in context.config.userdata.items():
            print("   - {} = {}".format(key, value))
    context.series_image_name = {}
    context.series_reuse_image = ""
    context.reuse_container = {}
    context.config = UAClientBehaveConfig.from_environ(context.config)
    has_aws_keys = bool(
        context.config.aws_access_key_id
        and context.config.aws_secret_access_key
    )
    if has_aws_keys:
        logging.basicConfig(
            filename="pycloudlib-behave.log", level=logging.DEBUG
        )
        context.config.ec2_api = pycloudlib.EC2(
            tag="ua-testing",
            access_key_id=context.config.aws_access_key_id,
            secret_access_key=context.config.aws_secret_access_key,
        )
        ec2_api = context.config.ec2_api
        if "uaclient-integration" in ec2_api.list_keys():
            ec2_api.delete_key("uaclient-integration")
        keypair = ec2_api.client.create_key_pair(
            KeyName="uaclient-integration"
        )
        with open(EC2_KEY_FILE, "w") as stream:
            stream.write(keypair["KeyMaterial"])
        os.chmod(EC2_KEY_FILE, 0o600)
        ec2_api.use_key(EC2_KEY_FILE, EC2_KEY_FILE, "uaclient-integration")
    if context.config.reuse_image:
        series = lxc_get_property(
            context.config.reuse_image, property_name="series", image=True
        )
        machine_type = lxc_get_property(
            context.config.reuse_image,
            property_name="machine_type",
            image=True,
        )
        if machine_type:
            print("Found machine_type: {vm_type}".format(vm_type=machine_type))
        if series is not None:
            context.series_reuse_image = series
            context.series_image_name[series] = context.config.reuse_image
        else:
            print(" Could not check image series. It will not be used. ")
            context.config.reuse_image = None

    if userdata.get("reuse_container"):
        if context.config.ec2_api:
            inst = context.config.ec2_api.get_instance(
                userdata.get("reuse_container")
            )
            codename = inst.execute(
                ["grep", "UBUNTU_CODENAME", "/etc/os-release"]
            ).strip()
            [_, series] = codename.split("=")
        else:  # lxd.vm and lxd.container machine_types
            series = lxc_get_property(
                userdata.get("reuse_container"), property_name="series"
            )
            machine_type = lxc_get_property(
                userdata.get("reuse_container"), property_name="machine_type"
            )
            if machine_type:
                print("Found type: {vm_type}".format(vm_type=machine_type))
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


def _should_skip_tags(context: Context, tags: "List") -> str:
    """Return a reason if a feature or scenario should be skipped"""
    for tag in tags:
        parts = tag.split(".")
        if parts[0] == "uses":
            val = context
            for idx, attr in enumerate(parts[1:], 1):
                val = getattr(val, attr, None)
                if val is None:
                    return "Skipped because tag value was None: {}".format(tag)
                if attr == "machine_type":
                    machine_type = ".".join(parts[idx + 1 :])
                    if val == machine_type:
                        break
                    return "Skipped machine_type {} != {}".format(
                        val, machine_type
                    )
    return ""


def before_feature(context: Context, feature: Feature):
    reason = _should_skip_tags(context, feature.tags)
    if reason:
        feature.skip(reason=reason)


def before_scenario(context: Context, scenario: Scenario):
    """
    In this function, we launch a container, install ubuntu-advantage-tools and
    then capture an image. This image is then reused by each scenario, reducing
    test execution time.
    """
    reason = _should_skip_tags(context, scenario.effective_tags)
    if reason:
        scenario.skip(reason=reason)
        return
    releases = set([])
    for tag in scenario.effective_tags:
        parts = tag.split(".")
        if parts[0] == "series":
            if parts[1] == "all":
                releases.update(ALL_SUPPORTED_SERIES)
            else:
                releases.update([parts[1]])
    if context.config.filter_series:
        releases = releases.intersection(context.config.filter_series)
    for release in releases:
        if release not in context.series_image_name:
            if context.config.ec2_api:
                create_uat_ec2_image(context, release)
            else:
                create_uat_lxd_image(context, release)


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


def create_uat_ec2_image(context: Context, series: str) -> None:
    """Create an Ubuntu PRO Ec2 instance with latest ubuntu-advantage-tools

    :param context:
        A `behave.runner.Context` which will have `config.ec2_api` set on it
    :param series:
       A string representing the series name to create
    """
    if series in context.reuse_container:
        print(
            "\n Reusing the existing EC2 instance: {}({}) ".format(
                context.reuse_container[series], series
            )
        )
        return
    if context.config.build_pr:
        raise RuntimeError("Don't yet support ec2 pro build_pr=1")

    # Launch pro image based on series marketplace lookup
    inst = launch_ec2(
        context, series=series, user_data=USERDATA_INSTALL_DAILY_PRO_UATOOLS
    )
    print("Creating updated AWS PRO AMI from instance: {}".format(inst.id))
    context.series_image_name[series] = context.config.ec2_api.snapshot(inst)
    print(
        "Created updated AWS PRO AMI: {}".format(
            context.series_image_name[series]
        )
    )


def create_uat_lxd_image(context: Context, series: str) -> None:
    """Create a given series lxd image with ubuntu-advantage-tools installed

    This will launch a container, install ubuntu-advantage-tools, and publish
    the image. The image's name is stored in context.series_image_name for
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
    deb_file = None
    is_vm = bool(context.config.machine_type == "lxd.vm")
    if is_vm and series == "xenial":
        # FIXME: use lxd custom cloud images which containt HWE kernel for
        # vhost-vsock support
        ubuntu_series = "images:ubuntu/16.04/cloud"
    else:
        ubuntu_series = "ubuntu-daily:%s" % series
    if context.config.build_pr:
        # create a dirty development image which installs build depends
        deb_file = PR_DEB_FILE
        build_container_name = (
            "behave-image-pre-build-%s-" % series + now.strftime("%s%f")
        )
        launch_lxd_container(
            context,
            series=series,
            image_name=ubuntu_series,
            container_name=build_container_name,
            is_vm=is_vm,
        )
        lxc_build_deb(build_container_name, output_deb_file=deb_file)

    build_container_name = "behave-image-build%s-%s" % (
        "-vm" if is_vm else "",
        series + now.strftime("%s%f"),
    )

    launch_lxd_container(
        context,
        series=series,
        image_name=ubuntu_series,
        container_name=build_container_name,
        is_vm=is_vm,
    )

    # if build_pr it will install new built .deb
    _install_uat_in_container(build_container_name, deb_file=deb_file)

    context.series_image_name[
        series
    ] = "behave-image-%s-" % series + now.strftime("%s%f")

    _capture_container_as_image(
        build_container_name, context.series_image_name[series]
    )


def _install_uat_in_container(
    container_name: str, deb_file: "Optional[str]"
) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_name:
        The name of the container into which ubuntu-advantage-tools should be
        installed.
    :param deb_file: Optional path to the deb_file we need to install
    """
    if deb_file:
        subprocess.run(
            ["lxc", "file", "push", deb_file, container_name + "/tmp/"]
        )
        lxc_exec(container_name, ["sudo", "dpkg", "-i", deb_file])
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
