import datetime
import itertools
import logging
import os
import random
import re
import string
import sys
import textwrap
from typing import Dict, List, Optional, Tuple, Union  # noqa: F401

import pycloudlib  # type: ignore
from behave.model import Feature, Scenario
from behave.runner import Context

import features.cloud as cloud
from features.util import InstallationSource, build_debs, lxc_get_property

ALL_SUPPORTED_SERIES = ["bionic", "focal", "xenial"]

UA_PPA_TEMPLATE = "http://ppa.launchpad.net/ua-client/{}/ubuntu"
DEFAULT_UA_PPA_KEYID = "6E34E7116C0BC933"

USERDATA_BLOCK_AUTO_ATTACH_IMG = """\
#cloud-config
bootcmd:
 - systemctl stop ua-auto-attach.service
"""

# we can't use write_files because it will clash with the
# lxd vendor-data write_files that is necessary to set up
# the lxd_agent on some releases
USERDATA_RUNCMD_PIN_PPA = """\
runcmd:
  - "printf \\"Package: *\\nPin: release o=LP-PPA-ua-client-{}\\nPin-Priority: 1001\\n\\" > /etc/apt/preferences.d/uaclient"
"""  # noqa: E501

USERDATA_RUNCMD_ENABLE_PROPOSED = """
runcmd:
  - printf \"deb http://archive.ubuntu.com/ubuntu/ {series}-proposed main\" > /etc/apt/sources.list.d/uaclient-proposed.list
  - "printf \\"Package: *\\nPin: release a={series}-proposed\\nPin-Priority: 400\\n\\" > /etc/apt/preferences.d/lower-proposed"
  - "printf \\"Package: ubuntu-advantage-tools\\nPin: release a={series}-proposed\\nPin-Priority: 1001\\n\\" > /etc/apt/preferences.d/uaclient-proposed"
"""  # noqa: E501

USERDATA_APT_SOURCE_PPA = """\
apt:
  sources:
    ua-tools-ppa:
        source: deb {ppa_url} $RELEASE main
        keyid: {ppa_keyid}
"""

PROCESS_LOG_TMPL = """\
returncode: {}
stdout:
{stdout}
stderr:
{stderr}
"""

PROCESS_LOG_TMPL = """\
returncode: {returncode}
stdout:
{stdout}
stderr:
{stderr}
"""


class UAClientBehaveConfig:
    """Store config options for Pro client behave test runs.

    This captures the configuration in one place, so that we have a single
    source of truth for test configuration (rather than having environment
    variable handling throughout the test code).

    :param cloud_credentials_path:
        Optional path the pycloudlib file containing the cloud credentials
    :param contract_token:
        A valid contract token to use during attach scenarios
    :param contract_token_staging:
        A valid staging contract token to use during attach scenarios
    :param image_clean:
        This indicates whether the image created for this test run should be
        cleaned up when all tests are complete.
    :param machine_type:
        The default machine_type to test: lxd.container, lxd.vm, azure.pro,
            azure.generic, aws.pro or aws.generic
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
    :param debs_path:
        Location of the debs to be used when lauching a focal integration
        test. If that path is None, we will build those debs locally.
    :param artifact_dir:
        Location where test artifacts are emitted.
    """

    prefix = "UACLIENT_BEHAVE_"

    # These variables are used in .from_environ() to convert the string
    # environment variable input to the appropriate Python types for use within
    # the test framework
    boolean_options = [
        "image_clean",
        "destroy_instances",
        "ephemeral_instance",
        "snapshot_strategy",
    ]
    str_options = [
        "cloud_credentials_path",
        "contract_token",
        "contract_token_staging",
        "contract_token_staging_expired",
        "machine_type",
        "private_key_file",
        "private_key_name",
        "reuse_image",
        "debs_path",
        "artifact_dir",
        "install_from",
        "custom_ppa",
        "custom_ppa_keyid",
        "userdata_file",
        "check_version",
        "sbuild_chroot",
    ]
    redact_options = [
        "contract_token",
        "contract_token_staging",
        "contract_token_staging_expired",
    ]

    # This variable is used in .from_environ() but also to emit the "Config
    # options" stanza in __init__
    all_options = boolean_options + str_options
    cloud_api = None  # type: pycloudlib.cloud.BaseCloud
    cloud_manager = None  # type: cloud.Cloud

    def __init__(
        self,
        *,
        cloud_credentials_path: str = None,
        image_clean: bool = True,
        destroy_instances: bool = True,
        ephemeral_instance: bool = False,
        snapshot_strategy: bool = False,
        machine_type: str = "lxd.container",
        private_key_file: str = None,
        private_key_name: str = "uaclient-integration",
        reuse_image: str = None,
        contract_token: str = None,
        contract_token_staging: str = None,
        contract_token_staging_expired: str = None,
        debs_path: str = None,
        artifact_dir: str = None,
        install_from: InstallationSource = InstallationSource.DAILY,
        custom_ppa: str = None,
        custom_ppa_keyid: str = None,
        userdata_file: str = None,
        check_version: str = None,
        sbuild_chroot: str = None,
        cmdline_tags: List = []
    ) -> None:
        # First, store the values we've detected
        self.cloud_credentials_path = cloud_credentials_path
        self.ephemeral_instance = ephemeral_instance
        self.snapshot_strategy = snapshot_strategy
        self.contract_token = contract_token
        self.contract_token_staging = contract_token_staging
        self.contract_token_staging_expired = contract_token_staging_expired
        self.image_clean = image_clean
        self.destroy_instances = destroy_instances
        self.machine_type = machine_type
        self.private_key_file = private_key_file
        self.private_key_name = private_key_name
        self.reuse_image = reuse_image
        self.cmdline_tags = cmdline_tags
        self.debs_path = debs_path
        self.artifact_dir = artifact_dir
        self.install_from = install_from
        self.custom_ppa = custom_ppa
        self.custom_ppa_keyid = custom_ppa_keyid
        self.userdata_file = userdata_file
        self.check_version = check_version
        self.sbuild_chroot = sbuild_chroot
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

        ignore_vars = ()  # type: Tuple[str, ...]
        if "pro" in self.machine_type:
            ignore_vars += (
                "UACLIENT_BEHAVE_CONTRACT_TOKEN",
                "UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING",
                "UACLIENT_BEHAVE_CONTRACT_TOKEN_STAGING_EXPIRED",
            )
        for env_name in ignore_vars:
            attr_name = env_name.replace("UACLIENT_BEHAVE_", "").lower()
            if getattr(self, attr_name):
                print(
                    " --- Ignoring {} because machine_type is {}".format(
                        env_name, self.machine_type
                    )
                )
                setattr(self, attr_name, None)
        timed_job_tag = datetime.datetime.utcnow().strftime(
            "uaclient-ci-%m%d-%H%M-"
        )
        # Jenkinsfile provides us with UACLIENT_BEHAVE_JENKINS_BUILD_TAG
        job_suffix = os.environ.get("UACLIENT_BEHAVE_JENKINS_BUILD_TAG")
        print("--- job suffix: {}".format(job_suffix), flush=True)
        if not job_suffix:
            job_suffix = os.environ.get("CHANGE_ID", "dev")
        else:
            job_suffix = job_suffix.split("PR-")[-1]
        timed_job_tag += str(job_suffix)
        timed_job_tag = timed_job_tag.replace(".", "-")

        # Add 8-digit random suffix to the tag, so it does not conflict when
        # spinning many jobs at the same time
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        timed_job_tag += "-" + random_suffix

        if "aws" in self.machine_type:
            # For AWS, we need to specify on the pycloudlib config file that
            # the AWS region must be us-east-2. The reason for that is because
            # our image ids were captured using that region.
            self.cloud_manager = cloud.EC2(
                machine_type=self.machine_type,
                cloud_credentials_path=self.cloud_credentials_path,
                tag=timed_job_tag,
                timestamp_suffix=False,
            )
        elif "azure" in self.machine_type:
            self.cloud_manager = cloud.Azure(
                machine_type=self.machine_type,
                cloud_credentials_path=self.cloud_credentials_path,
                tag=timed_job_tag,
                timestamp_suffix=False,
            )
        elif "gcp" in self.machine_type:
            self.cloud_manager = cloud.GCP(
                machine_type=self.machine_type,
                cloud_credentials_path=self.cloud_credentials_path,
                tag=timed_job_tag,
                timestamp_suffix=False,
            )
        elif "lxd.vm" in self.machine_type:
            self.cloud_manager = cloud.LXDVirtualMachine(
                machine_type=self.machine_type,
                cloud_credentials_path=self.cloud_credentials_path,
            )
        else:
            self.cloud_manager = cloud.LXDContainer(
                machine_type=self.machine_type,
                cloud_credentials_path=self.cloud_credentials_path,
            )

        self.cloud_api = self.cloud_manager.api

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
        kwargs = (
            {}
        )  # type: Dict[str, Union[str, bool, List, InstallationSource]]
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

        if "install_from" in kwargs:
            kwargs["install_from"] = InstallationSource(kwargs["install_from"])

        return cls(**kwargs)  # type: ignore


def before_all(context: Context) -> None:
    """behave will invoke this before anything else happens."""
    context.config.setup_logging()
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
    context.config.cloud_manager.manage_ssh_key()

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
        inst = context.config.cloud_api.get_instance(
            userdata.get("reuse_container")
        )
        codename = inst.execute(
            ["grep", "UBUNTU_CODENAME", "/etc/os-release"]
        ).strip()
        [_, series] = codename.split("=")

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


def _should_skip_tags(context: Context, tags: List) -> str:
    """Return a reason if a feature or scenario should be skipped"""
    machine_type = getattr(context.config, "machine_type", "")
    machine_types = []

    for tag in tags:
        parts = tag.split(".")
        if parts[0] != "uses":
            continue  # Only process @uses.* tags for skipping:
        val = context
        for idx, attr in enumerate(parts[1:], 1):
            val = getattr(val, attr, None)
            if attr == "machine_type":
                curr_machine_type = ".".join(parts[idx + 1 :])
                machine_types.append(curr_machine_type)
                if curr_machine_type == machine_type:
                    return ""

                break
            if val is None:
                return "Skipped: tag value was None: {}".format(tag)

    if machine_types:
        return "Skipped: machine type {} was not found in tags:\n {}".format(
            machine_type, ", ".join(machine_types)
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

    filter_series = context.config.filter_series
    given_a_series_match = re.match(
        "a `(.*)` machine with ubuntu-advantage-tools installed",
        scenario.steps[0].name,
    )
    if filter_series and given_a_series_match:
        series = given_a_series_match.group(1)
        if series and series not in filter_series:
            scenario.skip(
                reason=(
                    "Skipping scenario outline series `{series}`."
                    " Cmdline provided @series tags: {cmdline_series}".format(
                        series=series, cmdline_series=filter_series
                    )
                )
            )
            return

    if "uses.config.check_version" in scenario.effective_tags:
        # before_step doesn't execute early enough to modify the step
        # so we perform the version step surgery here
        for step in scenario.steps:
            if step.text:
                step.text = step.text.replace(
                    "{UACLIENT_BEHAVE_CHECK_VERSION}",
                    context.config.check_version,
                )


FAILURE_FILES = (
    "/etc/ubuntu-advantage/uaclient.log",
    "/var/log/cloud-init.log",
    "/var/log/ubuntu-advantage.log",
    "/var/lib/cloud/instance/user-data.txt",
    "/var/lib/cloud/instance/vendor-data.txt",
)
FAILURE_CMDS = {
    "ua-version": ["pro", "version"],
    "cloud-init-analyze": ["cloud-init", "analyze", "show"],
    "cloud-init.status": ["cloud-init", "status", "--long"],
    "status.json": ["pro", "status", "--all", "--format=json"],
    "journal.log": ["journalctl", "-b", "0"],
    "systemd-analyze-blame": ["systemd-analyze", "blame"],
    "systemctl-status": ["systemctl", "status"],
    "systemctl-status-ua-auto-attach": [
        "systemctl",
        "status",
        "ua-auto-attach.service",
    ],
    "systemctl-status-ua-reboot-cmds": [
        "systemctl",
        "status",
        "ua-reboot-cmds.service",
    ],
}


def after_step(context, step):
    """Collect test artifacts in the event of failure."""
    if step.status == "failed":
        if context.config.artifact_dir:
            artifacts_dir = context.config.artifact_dir
        else:
            artifacts_dir = "artifacts"
        artifacts_dir = os.path.join(
            artifacts_dir,
            "{}_{}".format(os.path.basename(step.filename), step.line),
        )
        if hasattr(context, "process"):
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir)
            artifact_file = os.path.join(artifacts_dir, "process.log")
            process = context.process
            with open(artifact_file, "w") as stream:
                stream.write(
                    PROCESS_LOG_TMPL.format(
                        returncode=process.returncode,
                        stdout=process.stdout,
                        stderr=process.stderr,
                    )
                )

        if hasattr(context, "instances"):
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir)
            for log_file in FAILURE_FILES:
                artifact_file = os.path.join(
                    artifacts_dir, os.path.basename(log_file)
                )
                logging.info(
                    "-- pull instance:{} {}".format(log_file, artifact_file)
                )
                try:
                    result = context.instances["uaclient"].execute(
                        ["cat", log_file], use_sudo=True
                    )
                    content = result.stdout if result.ok else ""
                except RuntimeError:
                    content = ""
                with open(artifact_file, "w") as stream:
                    stream.write(content)
            for artifact_file, cmd in FAILURE_CMDS.items():
                result = context.instances["uaclient"].execute(
                    cmd, use_sudo=True
                )
                artifact_file = os.path.join(artifacts_dir, artifact_file)
                with open(artifact_file, "w") as stream:
                    stream.write(result.stdout)


def after_all(context):
    if context.config.image_clean:
        for key, image in context.series_image_name.items():
            if key == context.series_reuse_image:
                logging.info(
                    " Not deleting this image: ",
                    context.series_image_name[key],
                )
            else:
                context.config.cloud_api.delete_image(image)


def capture_container_as_image(
    container_id: str, image_name: str, cloud_api: pycloudlib.cloud.BaseCloud
) -> str:
    """Capture a container as an image.

    :param container_id:
        The id of the container to be captured.  Note that this container
        will be stopped.
    :param image_name:
        The name under which the image should be published.
    :param cloud_api: Optional pycloud BaseCloud api for applicable
        machine_types.
    """
    logging.info(
        "--- Creating  base image snapshot from vm {}".format(container_id)
    )
    inst = cloud_api.get_instance(container_id)
    return cloud_api.snapshot(instance=inst)


def build_debs_from_sbuild(context: Context, series: str) -> List[str]:
    """Create a chroot and build the package using sbuild


    Will stop the development instance after deb build succeeds.

    :return: A list of paths to applicable deb files published.
    """
    deb_paths = []

    if context.config.debs_path:
        logging.info(
            "--- Checking if debs can be reused in {}".format(
                context.config.debs_path
            )
        )
        debs_path = context.config.debs_path
        if os.path.isdir(debs_path):
            deb_paths = [
                os.path.join(debs_path, deb_file)
                for deb_file in os.listdir(debs_path)
                if series in deb_file
            ]

    if len(deb_paths):
        logging.info("--- Reusing debs: {}".format(", ".join(deb_paths)))
    else:
        logging.info(
            "--- Could not find any debs to reuse. Building it locally"
        )
        deb_paths = build_debs(
            series=series,
            chroot=context.config.sbuild_chroot,
        )

    if "pro" in context.config.machine_type:
        return deb_paths
    # Redact ubuntu-advantage-pro deb as inapplicable
    return [deb_path for deb_path in deb_paths if "pro" not in deb_path]


def create_instance_with_uat_installed(
    context: Context,
    series: str,
    name: str,
    custom_user_data: Optional[str] = None,
) -> pycloudlib.instance.BaseInstance:
    """Create a given series lxd image with ubuntu-advantage-tools installed

    This will launch a container, install ubuntu-advantage-tools, and publish
    the image. The image's name is stored in context.series_image_name for
    use within step code.

    :param context:
        A `behave.runner.Context`;  this will have `series.image_name` set on
        it.
    :param series:
       A string representing the series name to create
    :param name:
       A string representing the instance name
    :param custom_user_data:
       A string representing custom userdata to be added to the instance

    :return: A pycloudlib Instance
    """

    if series in context.reuse_container:
        logging.info(
            "\n Reusing the existing container: ",
            context.reuse_container[series],
        )
        return

    user_data = _get_user_data_for_instance(context.config, series)

    if custom_user_data:
        prefix = "" if user_data else "#cloud-config"
        user_data += "{}\n{}".format(prefix, custom_user_data)

    logging.info(
        "--- Launching VM to create a base image with ubuntu-advantage"
    )
    inst = context.config.cloud_manager.launch(
        instance_name=name, series=series, user_data=user_data
    )
    instance_id = context.config.cloud_manager.get_instance_id(inst)

    deb_paths = None
    if context.config.install_from is InstallationSource.LOCAL:
        deb_paths = build_debs_from_sbuild(context, series)

    _install_uat_in_container(
        instance_id,
        series=series,
        config=context.config,
        machine_type=context.config.machine_type,
        deb_paths=deb_paths,
    )

    return inst


def _get_user_data_for_instance(
    config: UAClientBehaveConfig, series: str
) -> str:
    if config.install_from in (
        InstallationSource.ARCHIVE,
        InstallationSource.LOCAL,
    ):
        return ""

    user_data = "#cloud-config\n"

    if "pro" in config.machine_type:
        user_data = USERDATA_BLOCK_AUTO_ATTACH_IMG

    if config.userdata_file and os.path.exists(config.userdata_file):
        with open(config.userdata_file, "r") as stream:
            user_data = stream.read()

    if config.install_from is InstallationSource.PROPOSED:
        user_data += USERDATA_RUNCMD_ENABLE_PROPOSED.format(series=series)
        return user_data

    if config.install_from is InstallationSource.DAILY:
        user_data += USERDATA_RUNCMD_PIN_PPA.format("daily")
        ppa = UA_PPA_TEMPLATE.format("daily")
        ppa_keyid = DEFAULT_UA_PPA_KEYID
    elif config.install_from is InstallationSource.STAGING:
        user_data += USERDATA_RUNCMD_PIN_PPA.format("staging")
        ppa = UA_PPA_TEMPLATE.format("staging")
        ppa_keyid = DEFAULT_UA_PPA_KEYID
    elif config.install_from is InstallationSource.STABLE:
        user_data += USERDATA_RUNCMD_PIN_PPA.format("stable")
        ppa = UA_PPA_TEMPLATE.format("stable")
        ppa_keyid = DEFAULT_UA_PPA_KEYID
    elif config.install_from is InstallationSource.CUSTOM:
        if not config.custom_ppa or not config.custom_ppa_keyid:
            logging.error(
                "UACLIENT_BEHAVE_INSTALL_FROM is set to 'custom', "
                + "but missing UACLIENT_BEHAVE_CUSTOM_PPA or "
                + "UACLIENT_BEHAVE_CUSTOM_PPA_KEYID"
            )
            sys.exit(1)
        ppa = config.custom_ppa
        if ppa.startswith("ppa:"):
            ppa = ppa.replace("ppa:", "http://ppa.launchpad.net/") + "/ubuntu"
        ppa_keyid = config.custom_ppa_keyid or ""

    user_data += USERDATA_APT_SOURCE_PPA.format(
        ppa_url=ppa, ppa_keyid=ppa_keyid
    )

    logging.info("-- user data:\n" + user_data)
    return user_data


def _install_uat_in_container(
    container_id: str,
    series: str,
    config: UAClientBehaveConfig,
    machine_type: str,
    deb_paths: Optional[List[str]] = None,
) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_id:
        The id of the container into which ubuntu-advantage-tools should be
        installed.
    :param series: The name of the series that is being used
    :param config: UAClientBehaveConfig
    :param deb_paths: Optional paths to local deb files we need to install
    """
    cmds = ["systemctl is-system-running --wait"]  # type:  List[str]

    if deb_paths is None:
        deb_paths = []

    if deb_paths:
        cmds.append("sudo apt-get update -qqy")

        deb_files = []
        inst = config.cloud_api.get_instance(container_id)

        for deb_file in deb_paths:
            if "pro" in deb_file and "pro" not in config.machine_type:
                continue

            deb_name = os.path.basename(deb_file)
            deb_files.append("/tmp/" + deb_name)
            inst.push_file(deb_file, "/tmp/" + deb_name)

        cmds.append(
            " ".join(
                [
                    "sudo",
                    "DEBIAN_FRONTEND=noninteractive",
                    "apt-get",
                    "install",
                    "-y",
                    "--allow-downgrades",
                    '-o Dpkg::Options::="--force-confdef"',
                    '-o Dpkg::Options::="--force-confold"',
                ]
                + deb_files
            )
        )
    else:
        ua_pkg = ["ubuntu-advantage-tools"]
        if "pro" in machine_type:
            ua_pkg.append("ubuntu-advantage-pro")

        cmds.append("sudo apt-get update")
        cmds.append(
            " ".join(
                [
                    "sudo",
                    "DEBIAN_FRONTEND=noninteractive",
                    "apt-get",
                    "install",
                    "-y",
                    "--allow-downgrades",
                    '-o Dpkg::Options::="--force-confdef"',
                    '-o Dpkg::Options::="--force-confold"',
                ]
                + ua_pkg
            )
        )

    if "pro" in config.machine_type:
        features = "features:\n  disable_auto_attach: true\n"
        conf_path = "/etc/ubuntu-advantage/uaclient.conf"
        cmd = "printf '{}' > /var/tmp/uaclient.conf".format(features)
        cmds.append('sh -c "{}"'.format(cmd))
        cmds.append(
            'sudo -- sh -c "cat /var/tmp/uaclient.conf >> {}"'.format(
                conf_path
            )
        )
        cmds.append("sudo pro status --wait")
        cmds.append("sudo pro detach --assume-yes")

    cmds.append("pro version")
    instance = config.cloud_api.get_instance(container_id)
    for cmd in cmds:  # type: ignore
        result = instance.execute(cmd)
        if result.failed:
            logging.info(
                "--- Failed {}: out {} err {}".format(
                    cmd, result.stdout, result.stderr
                )
            )
        elif "version" in cmd:
            logging.info("--- " + result)
