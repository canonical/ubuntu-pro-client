import datetime
import logging
import os

from behave import given, when

from features.environment import (
    capture_container_as_image,
    create_instance_with_uat_installed,
)
from features.util import cleanup_instance

CONTAINER_PREFIX = "ubuntu-behave-test"
IMAGE_BUILD_PREFIX = "ubuntu-behave-image-build"
IMAGE_PREFIX = "ubuntu-behave-image"


def add_test_name_suffix(context, series, prefix):
    pr_number = os.environ.get("UACLIENT_BEHAVE_JENKINS_CHANGE_ID")
    pr_suffix = "-" + str(pr_number) if pr_number else ""
    is_vm = bool(context.config.machine_type == "lxd.vm")
    vm_suffix = "-vm" if is_vm else ""
    time_suffix = datetime.datetime.now().strftime("-%s%f")

    return "{prefix}{pr_suffix}{vm_suffix}-{series}{time_suffix}".format(
        prefix=prefix,
        pr_suffix=pr_suffix,
        vm_suffix=vm_suffix,
        series=series,
        time_suffix=time_suffix,
    )


@given("a `{series}` machine with ubuntu-advantage-tools installed")
def given_a_machine(
    context, series, custom_user_data=None, cloud_init_ppa=None
):
    if series in context.reuse_container:
        context.instances = {}
        context.container_name = context.reuse_container[series]
        context.instances["uaclient"] = context.config.cloud_api.get_instance(
            context.container_name
        )
        if "pro" in context.config.machine_type:
            context.instances[
                "uaclient"
            ] = context.config.cloud_api.get_instance(context.container_name)
        return

    instance_name = add_test_name_suffix(context, series, CONTAINER_PREFIX)

    if (
        context.config.snapshot_strategy
        and not custom_user_data
        and not cloud_init_ppa
    ):
        if series not in context.series_image_name:
            build_container_name = add_test_name_suffix(
                context, series, IMAGE_BUILD_PREFIX
            )
            image_inst = create_instance_with_uat_installed(
                context,
                series,
                build_container_name,
                custom_user_data,
                cloud_init_ppa=cloud_init_ppa,
            )

            image_name = add_test_name_suffix(context, series, IMAGE_PREFIX)
            image_inst_id = context.config.cloud_manager.get_instance_id(
                image_inst
            )
            image_id = capture_container_as_image(
                image_inst_id,
                image_name=image_name,
                cloud_api=context.config.cloud_api,
            )

            context.series_image_name[series] = image_id
            image_inst.delete(wait=False)

        inst = context.config.cloud_manager.launch(
            series=series,
            instance_name=instance_name,
            image_name=context.series_image_name[series],
            ephemeral=context.config.ephemeral_instance,
        )
    else:
        inst = create_instance_with_uat_installed(
            context,
            series,
            instance_name,
            custom_user_data,
            cloud_init_ppa=cloud_init_ppa,
        )

    context.series = series
    context.instances = {"uaclient": inst}

    context.container_name = context.config.cloud_manager.get_instance_id(
        context.instances["uaclient"]
    )

    context.add_cleanup(cleanup_instance(context, "uaclient"))
    logging.info(
        "--- instance ip: {}".format(context.instances["uaclient"].ip)
    )


@when("I take a snapshot of the machine")
def when_i_take_a_snapshot(context):
    cloud = context.config.cloud_manager
    inst = context.instances["uaclient"]

    snapshot = cloud.api.snapshot(inst)
    logging.debug("--- Snapshot created: %s", snapshot)
    context.instance_snapshot = snapshot

    def cleanup_image() -> None:
        try:
            context.config.cloud_manager.api.delete_image(
                context.instance_snapshot
            )
        except RuntimeError as e:
            logging.error(
                "Failed to delete image: {}\n{}".format(
                    context.instance_snapshot, str(e)
                )
            )

    context.add_cleanup(cleanup_image)


@given(
    "a `{series}` machine with ubuntu-advantage-tools installed adding this cloud-init user_data"  # noqa
)
def given_a_machine_with_user_data(context, series):
    custom_user_data = context.text
    given_a_machine(context, series, custom_user_data)


@given(
    "a `{series}` machine with ubuntu-advantage-tools installed and cloud-init upgraded to the latest daily version"  # noqa
)
def given_a_machine_with_uat_and_daily_cloud_init(context, series):
    given_a_machine(
        context,
        series,
        custom_user_data=None,
        cloud_init_ppa="ppa:cloud-init-dev/daily",
    )


@when(
    "I launch a `{series}` `{instance_name}` machine with ingress ports `{ports}`"  # noqa
)
def launch_machine_with_ingress_ports(context, series, instance_name, ports):
    launch_machine(
        context=context,
        series=series,
        instance_name=instance_name,
        ports=ports,
    )


@when("I launch a `{series}` `{instance_name}` machine")
def launch_machine(context, series, instance_name, ports=None):
    now = datetime.datetime.now()
    date_prefix = now.strftime("-%s%f")
    name = CONTAINER_PREFIX + series + date_prefix + "-" + instance_name

    kwargs = {"series": series, "instance_name": name}
    if ports:
        kwargs["inbound_ports"] = ports.split(",")
    context.instances[instance_name] = context.config.cloud_manager.launch(
        **kwargs
    )

    context.add_cleanup(cleanup_instance(context, instance_name))


@when("I launch a `{instance_name}` machine from the snapshot")
def launch_machine_from_snapshot(context, instance_name, user_data=None):
    now = datetime.datetime.now()
    date_prefix = now.strftime("-%s%f")
    name = CONTAINER_PREFIX + date_prefix + "-" + instance_name

    inst = context.instances[
        instance_name
    ] = context.config.cloud_manager.launch(
        context.series,
        instance_name=name,
        image_name=context.instance_snapshot,
        user_data=user_data,
    )
    instance_id = context.config.cloud_manager.get_instance_id(inst)
    logging.info(
        "--- Instance launched rom snapshot: instance_id=%s, instance_name=%s",
        instance_id,
        name,
    )
    context.add_cleanup(cleanup_instance(context, instance_name))


@when(
    "I launch a `{instance_name}` machine from the snapshot adding this cloud-init user_data"  # noqa
)
def launch_machine_from_snapshot_adding_user_data(context, instance_name):
    custom_user_data = context.text
    launch_machine_from_snapshot(
        context, instance_name, user_data=custom_user_data
    )


@when("I reboot the machine")
def when_i_reboot_the_machine(context):
    context.instances["uaclient"].restart(wait=True)


@when("I reboot the `{machine}` machine")
def when_i_reboot_the_machine_name(context, machine):
    context.instances[machine].restart(wait=True)
