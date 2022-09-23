from behave import when

from features.steps.shell import when_i_run_command
from features.util import SUT


@when("I disable any internet connection on the machine")
@when("I disable any internet connection on the `{machine_name}` machine")
def disable_internet_connection(context, machine_name=SUT):
    when_i_run_command(
        context,
        "ufw default deny incoming",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw default deny outgoing",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw allow from 10.0.0.0/8",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw allow from 172.16.0.0/12",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw allow from 192.168.0.0/16",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw allow out to 10.0.0.0/8",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw allow out to 172.16.0.0/12",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context,
        "ufw allow out to 192.168.0.0/16",
        "with sudo",
        machine_name=machine_name,
    )
    when_i_run_command(
        context, "ufw allow ssh", "with sudo", machine_name=machine_name
    )
    # We expect DNS to be working, but don't really want to set a server up...
    when_i_run_command(
        context, "ufw allow out 53", "with sudo", machine_name=machine_name
    )
    when_i_run_command(
        context,
        "ufw enable",
        "with sudo",
        machine_name=machine_name,
        stdin="y\n",
    )
