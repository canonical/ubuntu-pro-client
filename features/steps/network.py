from behave import when

from features.steps.shell import when_i_run_command


@when("I disable any internet connection on the machine")
def disable_internet_connection(context, instance_name="uaclient"):
    when_i_run_command(
        context,
        "ufw default deny incoming",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw default deny outgoing",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw allow from 10.0.0.0/8",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw allow from 172.16.0.0/12",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw allow from 192.168.0.0/16",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw allow out to 10.0.0.0/8",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw allow out to 172.16.0.0/12",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context,
        "ufw allow out to 192.168.0.0/16",
        "with sudo",
        instance_name=instance_name,
    )
    when_i_run_command(
        context, "ufw allow ssh", "with sudo", instance_name=instance_name
    )
    # We expect DNS to be working, but don't really want to set a server up...
    when_i_run_command(
        context, "ufw allow out 53", "with sudo", instance_name=instance_name
    )
    when_i_run_command(
        context,
        "ufw enable",
        "with sudo",
        instance_name=instance_name,
        stdin="y\n",
    )


@when("I disable any internet connection on the `{machine}` machine")
def disable_internet_connection_on_machine(context, machine):
    disable_internet_connection(context, instance_name=machine)
