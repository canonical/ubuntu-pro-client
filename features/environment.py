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
    UA_DEBS,
    launch_lxd_container,
    launch_ec2,
    lxc_exec,
    lxc_get_property,
    build_debs,
)

ALL_SUPPORTED_SERIES = ["bionic", "focal", "trusty", "xenial"]

DAILY_PPA = "http://ppa.launchpad.net/canonical-server/ua-client-daily/ubuntu"
DEFAULT_PRIVATE_KEY_FILE = "/tmp/uaclient.pem"
LOCAL_BUILD_ARTIFACTS_DIR = "/tmp/"

USERDATA_INSTALL_DAILY_PRO_UATOOLS = """\
#cloud-config
write_files:
  # TODO(drop path: /usr/bin/ua when 25.0 is in Ubuntu PRO images)
  - path: /usr/bin/ua
    content: |
        #!/bin/bash
        DATE=`date -u`
        echo "$DATE: exec ua $@" >> /root/ua-runs
    permissions: '0755'
  - path: /etc/ubuntu-advantage/uaclient.conf
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
    :param private_key_file:
        Optional path to pre-existing private key file to use when connecting
        launched VMs via ssh.
    :param private_key_name:
        Optional name of the cloud's named private key object to use when
        connecting to launched VMs via ssh. Default: uaclient-integration.
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
        "private_key_file",
        "private_key_name",
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

    cloud_api = None  # type: pycloudlib.cloud.BaseCloud

    def __init__(
        self,
        *,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        build_pr: bool = False,
        image_clean: bool = True,
        destroy_instances: bool = True,
        machine_type: str = "lxd.container",
        private_key_file: str = None,
        private_key_name: str = "uaclient-integration",
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
        self.private_key_file = private_key_file
        self.private_key_name = private_key_name
        self.reuse_image = reuse_image
        self.cmdline_tags = cmdline_tags
        self.filter_series = set(
            [
                tag.split(".")[1]
                for tag in cmdline_tags
                if tag.startswith("series.") and "series.all" not in tag
            ]
        )
        # Next, perform any required validation
        if self.reuse_image is not None:
            if self.image_clean:
                print(" Reuse_image specified, it will not be deleted.")

        has_aws_keys = bool(aws_access_key_id and aws_secret_access_key)
        if self.machine_type != "pro.aws":
            for attr_name in ("aws_access_key_id", "aws_secret_access_key"):
                if getattr(self, attr_name):
                    print(
                        " --- Ignoring UACLIENT_BEHAVE_{} because machine_type"
                        " is {}".format(attr_name.upper(), self.machine_type)
                    )
                    setattr(self, attr_name, None)
        else:
            # Machine-type precludes use of any contract tokens
            for attr_name in ("contract_token", "contract_token_staging"):
                if getattr(self, attr_name):
                    print(
                        " --- Ignoring UACLIENT_BEHAVE_{} because machine_type"
                        " is {}".format(attr_name.upper(), self.machine_type)
                    )
                    setattr(self, attr_name, None)
            if self.machine_type == "pro.aws":
                if not has_aws_keys:
                    logging.warning(
                        "UACLIENT_BEHAVE_MACHINE_TYPE=pro.aws requires"
                        " the following env vars:\n"
                        " - UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID\n"
                        " - UACLIENT_BEHAVE_AWS_SECRET_ACCESS_KEY\n"
                    )
        # Finally, print the config options.  This helps users debug the use of
        # config options, and means they'll be included in test logs in CI.
        print("Config options:")
        for option in self.all_options:
            value = getattr(self, option, "<UNSET>")
            if option in self.redact_options and value not in (
                None,
                "<UNSET>",
            ):
                value = "<REDACTED>"
            print("  {}".format(option), "=", value)

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
    logging.basicConfig(filename="pycloudlib-behave.log", level=logging.DEBUG)
    userdata = context.config.userdata
    if userdata:
        logging.debug("Userdata key / value pairs:")
        print("Userdata key / value pairs:")
        for key, value in userdata.items():
            logging.debug("   - {} = {}".format(key, value))
            print("   - {} = {}".format(key, value))
    context.series_image_name = {}
    context.series_reuse_image = ""
    context.reuse_container = {}
    context.config = UAClientBehaveConfig.from_environ(context.config)
    if context.config.machine_type == "pro.aws":
        context.config.cloud_api = pycloudlib.EC2(
            tag="uaclientci",
            access_key_id=context.config.aws_access_key_id,
            secret_access_key=context.config.aws_secret_access_key,
            region="us-east-2",
        )
        if context.config.private_key_file:
            private_key_file = context.config.private_key_file
        else:
            private_key_file = DEFAULT_PRIVATE_KEY_FILE
        cloud_api = context.config.cloud_api
        if not os.path.exists(private_key_file):
            if "uaclient-integration" in cloud_api.list_keys():
                cloud_api.delete_key("uaclient-integration")
            keypair = cloud_api.client.create_key_pair(
                KeyName="uaclient-integration"
            )
            with open(private_key_file, "w") as stream:
                stream.write(keypair["KeyMaterial"])
            os.chmod(private_key_file, 0o600)
        cloud_api.use_key(
            private_key_file, private_key_file, context.config.private_key_name
        )
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
        if context.config.cloud_api:
            inst = context.config.cloud_api.get_instance(
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
                    return "Skipped: tag value was None: {}".format(tag)
                if attr == "machine_type":
                    machine_type = ".".join(parts[idx + 1 :])
                    if val == machine_type:
                        if val == "aws.pro":  # Ensure we have AWS creds
                            has_aws_keys = bool(
                                context.config.aws_access_key_id
                                and context.config.aws_secret_access_key
                            )
                            if not has_aws_keys:
                                return (
                                    "Skipped: aws.pro machine_type requires"
                                    " UACLIENT_BEHAVE_AWS_ACCESS_KEY_ID and"
                                    " UACLIENT_BEHAVE_AWS_SECRET_KEY"
                                )
                        break
                    return "Skipped: machine_type {} != {}".format(
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


def _capture_container_as_image(
    container_name: str,
    image_name: str,
    cloud_api: "Optional[pycloudlib.cloud.BaseCloud]" = None,
) -> str:
    """Capture a container as an image.

    :param container_name:
        The name of the container to be captured.  Note that this container
        will be stopped.
    :param image_name:
        The name under which the image should be published.
    :param cloud_api: Optional pycloud BaseCloud api for applicable
        machine_types.
    """
    print(
        "--- Creating  base image snapshot from vm {}".format(container_name)
    )
    if cloud_api:
        inst = cloud_api.get_instance(container_name)
        return cloud_api.snapshot(instance=inst)
    else:
        # TODO(drop this with migration to pycloudlib.lxc)
        subprocess.run(["lxc", "stop", container_name])
        subprocess.run(
            ["lxc", "publish", container_name, "--alias", image_name]
        )
        return image_name


def build_debs_from_dev_instance(context: Context, series: str) -> "List[str]":
    """Create a development instance, instal build dependencies and build debs


    Will stop the development instance after deb build succeeds.

    :return: A list of paths to applicable deb files published.
    """
    time_suffix = datetime.datetime.now().strftime("%s%f")
    print("--- Launching vm to build ubuntu-advantage*debs from local source")
    if context.config.machine_type == "pro.aws":
        inst = launch_ec2(
            context,
            series=series,
            user_data=USERDATA_INSTALL_DAILY_PRO_UATOOLS,
        )
        build_container_name = inst.id
    else:
        build_container_name = (
            "behave-image-pre-build-%s-" % series + time_suffix
        )
        is_vm = bool(context.config.machine_type == "lxd.vm")
        if is_vm and series == "xenial":
            # FIXME: use lxd custom cloud images which containt HWE kernel for
            # vhost-vsock support
            lxc_ubuntu_series = "images:ubuntu/16.04/cloud"
        else:
            lxc_ubuntu_series = "ubuntu-daily:%s" % series
        launch_lxd_container(
            context,
            series=series,
            image_name=lxc_ubuntu_series,
            container_name=build_container_name,
            is_vm=is_vm,
        )
    deb_paths = build_debs(
        build_container_name,
        output_deb_dir=LOCAL_BUILD_ARTIFACTS_DIR,
        cloud_api=context.config.cloud_api,
    )
    if "pro" in context.config.machine_type:
        return deb_paths
    # Redact ubuntu-advantage-pro deb as inapplicable
    return [deb_path for deb_path in deb_paths if "pro" not in deb_path]


def create_uat_image(context: Context, series: str) -> None:
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
    time_suffix = datetime.datetime.now().strftime("%s%f")
    deb_paths = []
    if context.config.build_pr:
        deb_paths = build_debs_from_dev_instance(context, series)

    print(
        "--- Launching VM to create a base image with updated ubuntu-advantage"
    )
    if context.config.cloud_api:
        inst = launch_ec2(
            context,
            series=series,
            user_data=USERDATA_INSTALL_DAILY_PRO_UATOOLS,
        )
        build_container_name = inst.id
    else:
        is_vm = bool(context.config.machine_type == "lxd.vm")
        build_container_name = "behave-image-build-%s-%s" % (
            "-vm" if is_vm else "",
            series + time_suffix,
        )
        if is_vm and series == "xenial":
            # FIXME: use lxd custom cloud images which containt HWE kernel for
            # vhost-vsock support
            lxc_ubuntu_series = "images:ubuntu/16.04/cloud"
        else:
            lxc_ubuntu_series = "ubuntu-daily:%s" % series
        launch_lxd_container(
            context,
            series=series,
            image_name=lxc_ubuntu_series,
            container_name=build_container_name,
            is_vm=is_vm,
        )

    _install_uat_in_container(
        build_container_name,
        deb_paths=deb_paths,
        cloud_api=context.config.cloud_api,
    )

    image_name = _capture_container_as_image(
        build_container_name,
        image_name="behave-image-%s-" % series + time_suffix,
        cloud_api=context.config.cloud_api,
    )
    context.series_image_name[series] = image_name


def _install_uat_in_container(
    container_name: str,
    deb_paths: "Optional[List[str]]" = [],
    cloud_api: "Optional[pycloudlib.cloud.BaseCloud]" = None,
) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_name:
        The name of the container into which ubuntu-advantage-tools should be
        installed.
    :param deb_paths: Optional paths to local deb files we need to install
    :param cloud_api: Optional pycloud BaseCloud api for applicable
        machine_types.
    """
    cmds = []
    if not deb_paths:
        deb_names = (
            " ".join(UA_DEBS) if cloud_api else "ubuntu-advantage-tools"
        )
        cmds.extend(
            [
                [
                    "sudo",
                    "add-apt-repository",
                    "--yes",
                    "ppa:canonical-server/ua-client-daily",
                ],
                ["sudo", "apt-get", "update", "-qq"],
                ["sudo", "apt-get", "install", "-qq", "-y", deb_names],
            ]
        )
    else:
        for deb_file in deb_paths:
            deb_name = os.path.basename(deb_file)
            cmds.append(["sudo", "dpkg", "-i", "/tmp/" + deb_name])
            cmds.append(["apt-cache", "policy", deb_name.rstrip(".deb")])
            if cloud_api:
                inst = cloud_api.get_instance(container_name)
                inst.push_file(deb_file, "/tmp/" + deb_name)
            else:
                cmd = [
                    "lxc",
                    "file",
                    "push",
                    deb_file,
                    container_name + "/tmp/",
                ]
                subprocess.check_call(cmd)
    if cloud_api:
        instance = cloud_api.get_instance(container_name)
        for cmd in cmds:
            instance.execute(cmd)
    else:
        for cmd in cmds:
            lxc_exec(container_name, cmd)
