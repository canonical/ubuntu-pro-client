import datetime
import os
import itertools
import tempfile
import textwrap
import logging
import pycloudlib  # type: ignore

try:
    from typing import Dict, Optional, Union, List, Tuple, Any  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

from behave.model import Feature, Scenario

from behave.runner import Context

import features.cloud as cloud

from features.util import emit_spinner_on_travis, lxc_get_property, build_debs

ALL_SUPPORTED_SERIES = ["bionic", "focal", "xenial"]

DAILY_PPA = "http://ppa.launchpad.net/ua-client/daily/ubuntu"
DAILY_PPA_KEYID = "6E34E7116C0BC933"

USERDATA_BLOCK_AUTO_ATTACH_IMG = """\
#cloud-config
bootcmd:
 - cp /usr/bin/ua /usr/bin/ua.orig
 - 'echo "#!/bin/sh\ndate >> /root/ua-calls\n" > /usr/bin/ua'
 - chmod 755 /usr/bin/ua
"""

# we can't use write_files because it will clash with the
# lxd vendor-data write_files that is necessary to set up
# the lxd_agent on some releases
USERDATA_RUNCMD_PIN_PPA = """\
runcmd:
  - "printf \\"Package: *\\nPin: release o=LP-PPA-ua-client-daily\\nPin-Priority: 1001\\n\\" > /etc/apt/preferences.d/uaclient"
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
        "build_pr",
        "image_clean",
        "destroy_instances",
        "cache_source",
    ]
    str_options = [
        "aws_access_key_id",
        "aws_secret_access_key",
        "az_client_id",
        "az_client_secret",
        "az_tenant_id",
        "az_subscription_id",
        "gcp_credentials_path",
        "gcp_project",
        "contract_token",
        "contract_token_staging",
        "contract_token_staging_expired",
        "machine_type",
        "private_key_file",
        "private_key_name",
        "reuse_image",
        "debs_path",
        "artifact_dir",
        "ppa",
        "ppa_keyid",
        "userdata_file",
    ]
    redact_options = [
        "aws_access_key_id",
        "aws_secret_access_key",
        "az_client_id",
        "az_client_secret",
        "az_tenant_id",
        "az_subscription_id",
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
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        az_client_id: str = None,
        az_client_secret: str = None,
        az_tenant_id: str = None,
        az_subscription_id: str = None,
        gcp_credentials_path: str = None,
        gcp_project: str = None,
        build_pr: bool = False,
        image_clean: bool = True,
        destroy_instances: bool = True,
        cache_source: bool = True,
        machine_type: str = "lxd.container",
        private_key_file: str = None,
        private_key_name: str = "uaclient-integration",
        reuse_image: str = None,
        contract_token: str = None,
        contract_token_staging: str = None,
        contract_token_staging_expired: str = None,
        debs_path: str = None,
        artifact_dir: str = None,
        ppa: str = DAILY_PPA,
        ppa_keyid: str = DAILY_PPA_KEYID,
        userdata_file: str = None,
        cmdline_tags: "List" = []
    ) -> None:
        # First, store the values we've detected
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.az_client_id = az_client_id
        self.az_client_secret = az_client_secret
        self.az_tenant_id = az_tenant_id
        self.az_subscription_id = az_subscription_id
        self.gcp_credentials_path = gcp_credentials_path
        self.gcp_project = gcp_project
        self.build_pr = build_pr
        self.cache_source = cache_source
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
        self.ppa = ppa
        self.ppa_keyid = ppa_keyid
        self.userdata_file = userdata_file
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
        if "aws" not in self.machine_type:
            ignore_vars += cloud.EC2.env_vars
        if "azure" not in self.machine_type:
            ignore_vars += cloud.Azure.env_vars
        if "gcp" not in self.machine_type:
            ignore_vars += cloud.GCP.env_vars
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
        if "aws" in self.machine_type:
            self.cloud_manager = cloud.EC2(
                aws_access_key_id,
                aws_secret_access_key,
                region=os.environ.get("AWS_DEFAULT_REGION", "us-east-2"),
                machine_type=self.machine_type,
                tag=timed_job_tag,
                timestamp_suffix=False,
            )
        elif "azure" in self.machine_type:
            self.cloud_manager = cloud.Azure(
                az_client_id=az_client_id,
                az_client_secret=az_client_secret,
                az_tenant_id=az_tenant_id,
                az_subscription_id=az_subscription_id,
                machine_type=self.machine_type,
                tag=timed_job_tag,
                timestamp_suffix=False,
            )
        elif "gcp" in self.machine_type:
            self.cloud_manager = cloud.GCP(
                machine_type=self.machine_type,
                tag=timed_job_tag,
                timestamp_suffix=False,
                gcp_credentials_path=self.gcp_credentials_path,
                gcp_project=gcp_project,
            )
        elif "lxd.vm" in self.machine_type:
            self.cloud_manager = cloud.LXDVirtualMachine(
                machine_type=self.machine_type
            )
        else:
            self.cloud_manager = cloud.LXDContainer(
                machine_type=self.machine_type
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


def _should_skip_tags(context: Context, tags: "List") -> str:
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
                    if machine_type.startswith("lxd"):
                        return ""

                    cloud_manager = context.config.cloud_manager
                    if cloud_manager and cloud_manager.missing_env_vars():
                        return "".join(
                            (
                                "Skipped: {} machine_type requires:\n".format(
                                    machine_type
                                ),
                                *cloud_manager.format_missing_env_vars(
                                    cloud_manager.missing_env_vars()
                                ),
                            )
                        )
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


FAILURE_FILES = (
    "/etc/ubuntu-advantage/uaclient.log",
    "/var/log/cloud-init.log",
    "/var/log/ubuntu-advantage.log",
    "/var/lib/cloud/instance/user-data.txt",
    "/var/lib/cloud/instance/vendor-data.txt",
)
FAILURE_CMDS = {
    "ua-version": ["ua", "version"],
    "cloud-init-analyze": ["cloud-init", "analyze", "show"],
    "cloud-init.status": ["cloud-init", "status", "--long"],
    "status.json": ["ua", "status", "--all", "--format=json"],
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

        if hasattr(context, "instance"):
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir)
            for log_file in FAILURE_FILES:
                artifact_file = os.path.join(
                    artifacts_dir, os.path.basename(log_file)
                )
                print("-- pull instance:{} {}".format(log_file, artifact_file))
                try:
                    result = context.instance.execute(
                        ["cat", log_file], use_sudo=True
                    )
                    content = result.stdout if result.ok else ""
                except RuntimeError:
                    content = ""
                with open(artifact_file, "w") as stream:
                    stream.write(content)
            for artifact_file, cmd in FAILURE_CMDS.items():
                result = context.instance.execute(cmd, use_sudo=True)
                artifact_file = os.path.join(artifacts_dir, artifact_file)
                with open(artifact_file, "w") as stream:
                    stream.write(result.stdout)


def after_all(context):
    if context.config.ppa == "":
        print(" No custom images to delete. UACLIENT_BEHAVE_PPA is unset.")
    elif context.config.image_clean:
        for key, image in context.series_image_name.items():
            if key == context.series_reuse_image:
                print(
                    " Not deleting this image: ",
                    context.series_image_name[key],
                )
            else:
                context.config.cloud_api.delete_image(image)


def _capture_container_as_image(
    container_name: str,
    image_name: str,
    cloud_api: "pycloudlib.cloud.BaseCloud",
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
    inst = cloud_api.get_instance(container_name)
    return cloud_api.snapshot(instance=inst)


def build_debs_from_dev_instance(context: Context, series: str) -> "List[str]":
    """Create a development instance, instal build dependencies and build debs


    Will stop the development instance after deb build succeeds.

    :return: A list of paths to applicable deb files published.
    """
    time_suffix = datetime.datetime.now().strftime("%s%f")
    deb_paths = []

    if context.config.debs_path:
        print(
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
        print("--- Reusing debs: {}".format(", ".join(deb_paths)))
    else:
        print("--- Could not find any debs to reuse. Building it locally")
        print(
            "--- Launching vm to build ubuntu-advantage*debs from local source"
        )
        build_container_name = (
            "ubuntu-behave-image-pre-build-%s-" % series + time_suffix
        )

        cloud_manager = context.config.cloud_manager
        if "pro" in context.config.machine_type:
            user_data = USERDATA_BLOCK_AUTO_ATTACH_IMG
        else:
            user_data = ""
        inst = cloud_manager.launch(
            instance_name=build_container_name,
            series=series,
            user_data=user_data,
        )

        build_container_name = cloud_manager.get_instance_id(inst)

        with emit_spinner_on_travis("Building debs from local source... "):
            deb_paths = build_debs(
                build_container_name,
                output_deb_dir=os.path.join(tempfile.gettempdir(), series),
                cloud_api=context.config.cloud_api,
                cache_source=context.config.cache_source,
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
    ppa = context.config.ppa
    if ppa == "":
        image_name = context.config.cloud_manager.locate_image_name(series)
        print(
            "--- Unset UACLIENT_BEHAVE_PPA. Using ubuntu-advantage-tools "
            + "from image: {}".format(image_name)
        )
        context.series_image_name[series] = image_name
        return

    time_suffix = datetime.datetime.now().strftime("%s%f")
    deb_paths = []
    if context.config.build_pr:
        deb_paths = build_debs_from_dev_instance(context, series)

    print(
        "--- Launching VM to create a base image with updated ubuntu-advantage"
    )

    is_vm = bool(context.config.machine_type == "lxd.vm")
    build_container_name = "ubuntu-behave-image-build-%s-%s" % (
        "-vm" if is_vm else "",
        series + time_suffix,
    )

    user_data = ""
    ud_file = context.config.userdata_file
    if ud_file and os.path.exists(ud_file):
        with open(ud_file, "r") as stream:
            user_data = stream.read()
    if "pro" in context.config.machine_type:
        if not user_data:
            user_data = USERDATA_BLOCK_AUTO_ATTACH_IMG
    if not deb_paths:
        if not user_data:
            user_data = "#cloud-config\n"
        ppa = context.config.ppa
        ppa_keyid = context.config.ppa_keyid
        if context.config.ppa.startswith("ppa:"):
            ppa = ppa.replace("ppa:", "http://ppa.launchpad.net/") + "/ubuntu"

        if ppa == DAILY_PPA:
            user_data += USERDATA_RUNCMD_PIN_PPA

        user_data += USERDATA_APT_SOURCE_PPA.format(
            ppa_url=ppa, ppa_keyid=ppa_keyid
        )
    inst = context.config.cloud_manager.launch(
        instance_name=build_container_name, series=series, user_data=user_data
    )
    build_container_name = context.config.cloud_manager.get_instance_id(inst)

    _install_uat_in_container(
        build_container_name,
        series=series,
        config=context.config,
        machine_type=context.config.machine_type,
        deb_paths=deb_paths,
    )

    image_name = _capture_container_as_image(
        build_container_name,
        image_name="ubuntu-behave-image-%s-" % series + time_suffix,
        cloud_api=context.config.cloud_api,
    )
    context.series_image_name[series] = image_name
    inst.delete(wait=False)


def _install_uat_in_container(
    container_name: str,
    series: str,
    config: UAClientBehaveConfig,
    machine_type: str,
    deb_paths: "Optional[List[str]]" = None,
) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_name:
        The name of the container into which ubuntu-advantage-tools should be
        installed.
    :param series: The name of the series that is being used
    :param config: UAClientBehaveConfig
    :param deb_paths: Optional paths to local deb files we need to install
    """
    cmds: "List[Any]" = [["systemctl", "is-system-running", "--wait"]]

    if deb_paths is None:
        deb_paths = []

    if deb_paths:
        cmds.append(["sudo", "apt-get", "update", "-qqy"])

        deb_files = []
        inst = config.cloud_api.get_instance(container_name)

        for deb_file in deb_paths:
            if "pro" in deb_file and "pro" not in config.machine_type:
                continue

            deb_name = os.path.basename(deb_file)
            deb_files.append("/tmp/" + deb_name)
            inst.push_file(deb_file, "/tmp/" + deb_name)

        cmds.append(
            ["sudo", "apt-get", "install", "-y", "--allow-downgrades"]
            + deb_files
        )
    else:
        ua_pkg = ["ubuntu-advantage-tools"]
        if "pro" in machine_type:
            ua_pkg.append("ubuntu-advantage-pro")

        cmds.append(
            ["sudo", "apt-get", "install", "-y", "--allow-downgrades"] + ua_pkg
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
        cmds.append("sudo ua status --wait")
        cmds.append("sudo ua detach --assume-yes")

    cmds.append(["ua", "version"])
    instance = config.cloud_api.get_instance(container_name)
    for cmd in cmds:  # type: ignore
        result = instance.execute(cmd)
        if result.failed:
            print(
                "--- Failed {}: out {} err {}".format(
                    cmd, result.stdout, result.stderr
                )
            )
        elif "version" in cmd:
            print("--- " + result)
