import datetime
import logging
import sys
from typing import NamedTuple

from behave import given, when
from pycloudlib.instance import BaseInstance  # type: ignore

from features.steps.packages import when_i_apt_install, when_i_apt_update
from features.steps.shell import when_i_run_command
from features.steps.ubuntu_advantage_tools import when_i_install_uat
from features.util import (
    BUILDER_NAME_PREFIX,
    SUT,
    InstallationSource,
    build_debs,
    get_debs_for_series,
)

MachineTuple = NamedTuple(
    "MachineTuple",
    [
        ("series", str),
        ("instance", BaseInstance),
        ("machine_type", str),
        ("cloud", str),
    ],
)
SnapshotTuple = NamedTuple(
    "SnapshotTuple",
    [("series", str), ("name", str), ("machine_type", str), ("cloud", str)],
)


@when(
    "I launch a `{series}` `{machine_type}` machine named `{machine_name}` from the snapshot of `{snapshot_name}`"  # noqa: E501
)
@given("a `{series}` `{machine_type}` machine")
@given("a `{series}` `{machine_type}` machine named `{machine_name}`")
@given(
    "a `{series}` `{machine_type}` machine named `{machine_name}` with ingress ports `{ports}`"  # noqa: E501
)
def given_a_machine(
    context,
    series,
    machine_type,
    machine_name=SUT,
    snapshot_name=None,
    user_data=None,
    ports=None,
    cleanup=True,
):
    cloud = machine_type.split(".")[0]
    context.pro_config.clouds.get(cloud).manage_ssh_key()

    time_suffix = datetime.datetime.now().strftime("%m%d-%H%M%S%f")
    instance_name = "upro-behave-{series}-{machine_name}-{time_suffix}".format(
        series=series,
        machine_name=machine_name,
        time_suffix=time_suffix,
    )

    inbound_ports = ports.split(",") if ports is not None else None

    is_pro = "pro" in machine_type
    pro_user_data = (
        "bootcmd:\n"
        """  - "cloud-init-per once disable-auto-attach printf '\\nfeatures: {disable_auto_attach: true}\\n' >> /etc/ubuntu-advantage/uaclient.conf"\n"""  # noqa: E501
    )
    user_data_to_use = None
    if is_pro or user_data is not None:
        user_data_to_use = "#cloud-config\n"
        if is_pro:
            user_data_to_use += pro_user_data
        if user_data is not None:
            user_data_to_use += user_data

    if snapshot_name and snapshot_name in context.snapshots:
        image_name = context.snapshots[snapshot_name].name
    else:
        image_name = None

    instance = context.pro_config.clouds.get(cloud).launch(
        series=series,
        machine_type=machine_type,
        instance_name=instance_name,
        ephemeral=context.pro_config.ephemeral_instance,
        image_name=image_name,
        inbound_ports=inbound_ports,
        user_data=user_data_to_use,
    )

    context.machines[machine_name] = MachineTuple(
        series=series,
        instance=instance,
        machine_type=machine_type,
        cloud=cloud,
    )

    if series == "xenial":
        # Upgrading open-iscsi to esm version on xenial restarts this service
        # This sometimes causes resource errors on github action runners
        when_i_run_command(
            context,
            "systemctl mask iscsid.service",
            "with sudo",
            machine_name=machine_name,
        )

    # make sure the machine has up-to-date apt data
    when_i_apt_update(context, machine_name=machine_name)

    # add coverage
    when_i_apt_install(context, "python3-coverage", machine_name=machine_name)

    # Create the .coveragerc file in the lxd container
    if hasattr(context, "machines") and SUT in context.machines:
        context.machines[SUT].instance.execute(
            [
                "bash",
                "-c",
                "echo -e '[run]\nrelative_files = True\n\n[paths]\nsource = \
                    \n\tuaclient/ \
                    \n\tusr/lib/python3/dist-packages/uaclient/' > \
                    /usr/lib/python3/dist-packages/uaclient/.coveragerc",
            ],
            use_sudo=True,
        )

    if cleanup:

        def cleanup_instance():
            if not context.pro_config.destroy_instances:
                logging.info(
                    "--- Leaving instance running: {}".format(
                        context.machines[machine_name].instance.name
                    )
                )
                return
            try:
                machine = context.machines.pop(machine_name)
                machine.instance.delete(wait=False)
            except RuntimeError as e:
                logging.error(
                    "Failed to delete instance: {}\n{}".format(
                        context.machines[machine_name].instance.name, str(e)
                    )
                )

        context.add_cleanup(cleanup_instance)


@when("I take a snapshot of the machine")
def when_i_take_a_snapshot(context, machine_name=SUT, cleanup=True):
    machine_type = context.machines[machine_name].machine_type
    series = context.machines[machine_name].series
    cloud = context.machines[machine_name].cloud
    inst = context.machines[machine_name].instance
    snapshot = context.pro_config.clouds.get(cloud).api.snapshot(inst)

    context.snapshots[machine_name] = SnapshotTuple(
        series=series, name=snapshot, machine_type=machine_type, cloud=cloud
    )

    if cleanup:

        def cleanup_snapshot() -> None:
            try:
                context.pro_config.clouds.get(cloud).api.delete_image(snapshot)
            except RuntimeError as e:
                logging.error(
                    "Failed to delete image: {}\n{}".format(snapshot, str(e))
                )

        context.add_cleanup(cleanup_snapshot)


@given(
    "a `{series}` `{machine_type}` machine with ubuntu-advantage-tools installed"  # noqa: E501
)
def given_a_sut_machine(context, series, machine_type):
    if context.pro_config.install_from == InstallationSource.LOCAL:
        # build right away, this will cache the built debs for later use
        # building early means we catch build errors before investing in
        # launching instances
        build_debs(
            series,
            sbuild_output_to_terminal=context.pro_config.sbuild_output_to_terminal,  # noqa: E501
        )

    if context.pro_config.install_from == InstallationSource.PREBUILT:
        deb_paths = get_debs_for_series(context.pro_config.debs_path, series)
        if not deb_paths:
            logging.error(
                (
                    "UACLIENT_BEHAVE_INSTALL_FROM is set to 'prebuilt', "
                    "but no debs for series {} were found in"
                    "UACLIENT_BEHAVE_DEBS_PATH"
                ).format(series)
            )
            sys.exit(1)

    builder_name = BUILDER_NAME_PREFIX + machine_type

    if context.pro_config.snapshot_strategy:
        if builder_name not in context.snapshots:
            given_a_machine(
                context,
                series,
                machine_type=machine_type,
                machine_name=builder_name,
                cleanup=False,
            )
            when_i_install_uat(context, machine_name=builder_name)
            when_i_take_a_snapshot(
                context,
                machine_name=builder_name,
                cleanup=False,
            )
            context.machines[builder_name].instance.delete(wait=False)
        given_a_machine(
            context,
            series,
            machine_type=machine_type,
            snapshot_name=builder_name,
        )
    else:
        given_a_machine(context, series, machine_type=machine_type)
        when_i_install_uat(context)

    logging.info(
        "--- instance ip: {}".format(context.machines[SUT].instance.ip)
    )


@given(
    "a `{series}` `{machine_type}` machine with ubuntu-advantage-tools installed adding this cloud-init user_data"  # noqa: E501
)
def given_a_sut_machine_with_user_data(context, series, machine_type):
    # doesn't support snapshot strategy because the test depends on
    # custom user data
    given_a_machine(context, series, machine_type, user_data=context.text)
    when_i_install_uat(context)


@when("I reboot the `{machine_name}` machine")
@when("I reboot the machine")
def when_i_reboot_the_machine(context, machine_name=SUT):
    context.machines[machine_name].instance.restart(wait=True)
