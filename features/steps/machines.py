import datetime
import logging
import sys
from typing import Dict, NamedTuple

from behave import given, when
from pycloudlib.instance import BaseInstance  # type: ignore

from features.steps.ubuntu_advantage_tools import when_i_install_uat
from features.util import (
    SUT,
    InstallationSource,
    build_debs,
    get_debs_for_series,
)

MachineTuple = NamedTuple(
    "MachineTuple", [("series", str), ("instance", BaseInstance)]
)
MachinesDict = Dict[str, MachineTuple]


@when(
    "I launch a `{series}` machine named `{machine_name}` from the snapshot of `{snapshot_name}`"  # noqa: E501
)
@given("a `{series}` machine")
@given("a `{series}` machine named `{machine_name}`")
@given(
    "a `{series}` machine named `{machine_name}` with ingress ports `{ports}`"
)
def given_a_machine(
    context,
    series,
    machine_type=None,
    machine_name=SUT,
    snapshot_name=None,
    user_data=None,
    ports=None,
    cleanup=True,
):
    if machine_type is None:
        machine_type = context.pro_config.machine_type

    cloud = machine_type.split(".")[0]
    context.pro_config.clouds[cloud].manage_ssh_key()

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

    instance = context.pro_config.clouds[cloud].launch(
        series=series,
        machine_type=machine_type,
        instance_name=instance_name,
        ephemeral=context.pro_config.ephemeral_instance,
        image_name=context.snapshots.get(snapshot_name, None),
        inbound_ports=inbound_ports,
        user_data=user_data_to_use,
    )

    context.machines[machine_name] = MachineTuple(
        series=series, instance=instance
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
def when_i_take_a_snapshot(
    context, machine_type=None, machine_name=SUT, cleanup=True
):
    if machine_type is None:
        machine_type = context.pro_config.machine_type

    cloud = machine_type.split(".")[0]
    inst = context.machines[machine_name].instance
    snapshot = context.pro_config.clouds[cloud].api.snapshot(inst)

    context.snapshots[machine_name] = snapshot

    if cleanup:

        def cleanup_snapshot() -> None:
            try:
                context.pro_config.clouds[cloud].api.delete_image(
                    context.snapshots[machine_name]
                )
            except RuntimeError as e:
                logging.error(
                    "Failed to delete image: {}\n{}".format(
                        context.snapshots[machine_name], str(e)
                    )
                )

        context.add_cleanup(cleanup_snapshot)


@given("a `{series}` machine with ubuntu-advantage-tools installed")
@given(
    "a `{series}` `{machine_type}` machine with ubuntu-advantage-tools installed"  # noqa: E501
)
def given_a_sut_machine(context, series, machine_type=None):
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

    if context.pro_config.snapshot_strategy:
        if "builder" not in context.snapshots:
            given_a_machine(
                context,
                series,
                machine_type=machine_type,
                machine_name="builder",
                cleanup=False,
            )
            when_i_install_uat(context, machine_name="builder")
            when_i_take_a_snapshot(
                context,
                machine_type=machine_type,
                machine_name="builder",
                cleanup=False,
            )
            context.machines["builder"].instance.delete(wait=False)
        given_a_machine(context, series, snapshot_name="builder")
    else:
        given_a_machine(context, series, machine_type=machine_type)
        when_i_install_uat(context)

    logging.info(
        "--- instance ip: {}".format(context.machines[SUT].instance.ip)
    )


@given(
    "a `{series}` machine with ubuntu-advantage-tools installed adding this cloud-init user_data"  # noqa: E501
)
def given_a_sut_machine_with_user_data(context, series):
    # doesn't support snapshot strategy because the test depends on
    # custom user data
    given_a_machine(context, series, user_data=context.text)
    when_i_install_uat(context)


@when("I reboot the `{machine_name}` machine")
@when("I reboot the machine")
def when_i_reboot_the_machine(context, machine_name=SUT):
    context.machines[machine_name].instance.restart(wait=True)
