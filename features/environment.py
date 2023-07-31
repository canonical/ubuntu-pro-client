import datetime
import itertools
import logging
import os
import random
import re
import string
import sys
import tarfile
from typing import Dict, List, Optional, Tuple, Union  # noqa: F401

import pycloudlib  # type: ignore  # noqa: F401
from behave.model import Feature, Scenario
from behave.runner import Context

import features.cloud as cloud
from features.util import (
    SUT,
    InstallationSource,
    lxc_get_property,
    process_template_vars,
)

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
        The default machine_type to test: lxd-container, lxd-vm, azure.pro,
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
        "sbuild_output_to_terminal",
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
        "artifact_dir",
        "install_from",
        "custom_ppa",
        "debs_path",
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

    def __init__(
        self,
        *,
        cloud_credentials_path: Optional[str] = None,
        image_clean: bool = True,
        destroy_instances: bool = True,
        ephemeral_instance: bool = False,
        snapshot_strategy: bool = False,
        sbuild_output_to_terminal: bool = False,
        machine_type: str = "lxd-container",
        private_key_file: Optional[str] = None,
        private_key_name: str = "uaclient-integration",
        reuse_image: Optional[str] = None,
        contract_token: Optional[str] = None,
        contract_token_staging: Optional[str] = None,
        contract_token_staging_expired: Optional[str] = None,
        artifact_dir: str = "artifacts",
        install_from: InstallationSource = InstallationSource.LOCAL,
        custom_ppa: Optional[str] = None,
        debs_path: Optional[str] = None,
        userdata_file: Optional[str] = None,
        check_version: Optional[str] = None,
        sbuild_chroot: Optional[str] = None,
        cmdline_tags: List = []
    ) -> None:
        # First, store the values we've detected
        self.cloud_credentials_path = cloud_credentials_path
        self.ephemeral_instance = ephemeral_instance
        self.snapshot_strategy = snapshot_strategy
        self.sbuild_output_to_terminal = sbuild_output_to_terminal
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
        self.artifact_dir = artifact_dir
        self.install_from = install_from
        self.custom_ppa = custom_ppa
        self.debs_path = debs_path
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
        if install_from == InstallationSource.CUSTOM and not custom_ppa:
            logging.error(
                "UACLIENT_BEHAVE_INSTALL_FROM is set to 'custom', "
                "but missing UACLIENT_BEHAVE_CUSTOM_PPA"
            )
            sys.exit(1)
        if install_from == InstallationSource.PREBUILT and not debs_path:
            logging.error(
                "UACLIENT_BEHAVE_INSTALL_FROM is set to 'prebuilt', "
                "but missing UACLIENT_BEHAVE_DEBS_PATH"
            )
            sys.exit(1)

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

        self.clouds = {
            "aws": cloud.EC2(
                cloud_credentials_path=self.cloud_credentials_path,
                tag=timed_job_tag,
                timestamp_suffix=False,
            ),
            "azure": cloud.Azure(
                cloud_credentials_path=self.cloud_credentials_path,
                tag=timed_job_tag,
                timestamp_suffix=False,
            ),
            "gcp": cloud.GCP(
                cloud_credentials_path=self.cloud_credentials_path,
                tag=timed_job_tag,
                timestamp_suffix=False,
            ),
            "lxd-vm": cloud.LXDVirtualMachine(
                cloud_credentials_path=self.cloud_credentials_path,
            ),
            "lxd-container": cloud.LXDContainer(
                cloud_credentials_path=self.cloud_credentials_path,
            ),
        }
        if "aws" in self.machine_type:
            self.default_cloud = self.clouds["aws"]
        elif "azure" in self.machine_type:
            self.default_cloud = self.clouds["azure"]
        elif "gcp" in self.machine_type:
            self.default_cloud = self.clouds["gcp"]
        elif "lxd-vm" in self.machine_type:
            self.default_cloud = self.clouds["lxd-vm"]
        else:
            self.default_cloud = self.clouds["lxd-container"]

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

        # userdata should override environment variables
        kwargs.update(config.userdata)

        # Next, sanitise the non-string options to Python types
        for key in cls.boolean_options:
            bool_value = True  # Default to True
            if key in kwargs:
                if kwargs[key] == "0" or str(kwargs[key]).lower() == "false":
                    bool_value = False
                kwargs[key] = bool_value

        if "install_from" in kwargs:
            kwargs["install_from"] = InstallationSource(kwargs["install_from"])

        return cls(**kwargs)  # type: ignore


def before_all(context: Context) -> None:
    """behave will invoke this before anything else happens."""
    context.config.setup_logging()
    if logging.getLogger().level == logging.DEBUG:
        # The AWS boto libraries are very very very verbose
        # We pretty much never want their debug level messages,
        # but we do want to be able to use the debug log level
        # in our code. So we bump their loggers up to info
        # when we set debug at the cli with --logging-level=debug
        logging.warn(
            "Setting AWS botocore and boto3 loggers to INFO to avoid"
            " extra verbose logs"
        )
        logging.getLogger("botocore").setLevel(logging.INFO)
        logging.getLogger("boto3").setLevel(logging.INFO)
    userdata = context.config.userdata
    if userdata:
        logging.debug("Userdata key / value pairs:")
        print("Userdata key / value pairs:")
        for key, value in userdata.items():
            logging.debug("   - {} = {}".format(key, value))
            print("   - {} = {}".format(key, value))
    context.series_image_name = {}
    context.series_reuse_image = ""
    context.pro_config = UAClientBehaveConfig.from_environ(context.config)
    context.snapshots = {}
    context.machines = {}

    if context.pro_config.reuse_image:
        series = lxc_get_property(
            context.pro_config.reuse_image, property_name="series", image=True
        )
        machine_type = lxc_get_property(
            context.pro_config.reuse_image,
            property_name="machine_type",
            image=True,
        )
        if machine_type:
            print("Found machine_type: {vm_type}".format(vm_type=machine_type))
        if series is not None:
            context.series_reuse_image = series
            context.series_image_name[series] = context.pro_config.reuse_image
        else:
            print(" Could not check image series. It will not be used. ")
            context.pro_config.reuse_image = None


def _should_skip_tags(context: Context, tags: List) -> str:
    """Return a reason if a feature or scenario should be skipped"""
    machine_type = getattr(context.pro_config, "machine_type", "")
    machine_types = []

    for tag in tags:
        parts = tag.split(".")
        if parts[0] != "uses" or parts[1] != "config":
            continue  # Only process @uses.config.* tags for skipping:
        val = context.pro_config
        for idx, attr in enumerate(parts[2:], 1):
            val = getattr(val, attr, None)
            if attr == "machine_type":
                curr_machine_type = ".".join(parts[idx + 2 :])
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
    context.stored_vars = {}

    reason = _should_skip_tags(context, scenario.effective_tags)
    if reason:
        scenario.skip(reason=reason)
        return

    filter_series = context.pro_config.filter_series
    given_a_series_match = re.match(
        "a `([a-z]*)` machine with ubuntu-advantage-tools installed",
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

    if hasattr(scenario, "_row") and scenario._row is not None:
        row_release = scenario._row.get("release")
        if (
            row_release
            and len(filter_series) > 0
            and row_release not in filter_series
        ):
            scenario.skip(
                reason=(
                    "Skipping scenario outline series `{series}`."
                    " Cmdline provided @series tags: {cmdline_series}".format(
                        series=row_release, cmdline_series=filter_series
                    )
                )
            )
            return
        row_machine_type = scenario._row.get("machine_type")
        if (
            row_machine_type
            and context.pro_config.machine_type != "any"
            and row_machine_type != context.pro_config.machine_type
        ):
            scenario.skip(
                reason=(
                    "Skipping scenario outline machine_type `{}`."
                    " Cmdline provided machine_type: {}".format(
                        row_machine_type, context.pro_config.machine_type
                    )
                )
            )
            return

    # before_step doesn't execute early enough to modify the step
    # so we perform step text surgery here
    # Also, logging capture is not set up when before_scenario is called,
    # so if you call logging.info here, then the root logger gets configured
    # and it messes up all the future behave logging capture machinery.
    # See https://github.com/behave/behave/blob/v1.2.6/behave/model.py#L700
    # But we want to log the replacement we're making, so we use the behave
    # logger and warning log_level to make sure it gets included.
    logger = logging.getLogger("behave.before_scenario.process_template_vars")
    for step in scenario.steps:
        if step.text:
            step.text = process_template_vars(
                context, step.text, logger_fn=logger.warn
            )


def after_step(context, step):
    """Collect test artifacts in the event of failure."""
    if step.status == "failed":
        logging.warning("STEP FAILED. Collecting logs.")
        inner_dir = os.path.join(
            datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S"),
            "{}_{}".format(os.path.basename(step.filename), step.line),
        )
        new_artifacts_dir = os.path.join(
            context.pro_config.artifact_dir,
            inner_dir,
        )
        if not os.path.exists(new_artifacts_dir):
            os.makedirs(new_artifacts_dir)

        latest_link_dir = os.path.join(
            context.pro_config.artifact_dir, "latest"
        )
        if os.path.exists(latest_link_dir):
            os.unlink(latest_link_dir)
        os.symlink(inner_dir, latest_link_dir)

        if hasattr(context, "process"):
            artifact_file = os.path.join(new_artifacts_dir, "process.log")
            process = context.process
            with open(artifact_file, "w") as stream:
                stream.write(
                    PROCESS_LOG_TMPL.format(
                        returncode=process.returncode,
                        stdout=process.stdout,
                        stderr=process.stderr,
                    )
                )

        if hasattr(context, "machines") and SUT in context.machines:
            try:
                context.machines[SUT].instance.execute(
                    ["pro", "collect-logs", "-o", "/tmp/logs.tar.gz"],
                    use_sudo=True,
                )
                context.machines[SUT].instance.execute(
                    ["chmod", "666", "/tmp/logs.tar.gz"], use_sudo=True
                )
                dest = os.path.join(new_artifacts_dir, "logs.tar.gz")
                context.machines[SUT].instance.pull_file(
                    "/tmp/logs.tar.gz", dest
                )
                with tarfile.open(dest) as logs_tarfile:
                    logs_tarfile.extractall(new_artifacts_dir)
                logging.warning("Done collecting logs.")
            except Exception as e:
                logging.error(str(e))
                logging.warning("Failed to collect logs")


def after_all(context):
    if context.pro_config.image_clean:
        for key, image in context.series_image_name.items():
            if key == context.series_reuse_image:
                logging.info(
                    " Not deleting this image: ",
                    context.series_image_name[key],
                )
            else:
                context.pro_config.default_cloud.api.delete_image(image)

    if context.pro_config.destroy_instances:
        try:
            if context.pro_config.default_cloud._ssh_key_managed:
                key_pair = context.pro_config.default_cloud.api.key_pair
                os.remove(key_pair.private_key_path)
                os.remove(key_pair.public_key_path)

        except Exception as e:
            logging.error(
                "Failed to delete instance ssh keys:\n{}".format(str(e))
            )

    if "builder" in context.snapshots:
        try:
            context.pro_config.default_cloud.api.delete_image(
                context.snapshots["builder"]
            )
        except RuntimeError as e:
            logging.error(
                "Failed to delete image: {}\n{}".format(
                    context.snapshots["builder"], str(e)
                )
            )
