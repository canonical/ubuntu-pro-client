from behave import when

from features.steps.shell import when_i_run_command
from features.util import SUT


@when("I disable access to {website}")
def block_access_to_address(context, website):
    when_i_run_command(
        context,
        "sed -i '1i127.0.0.1 {}' /etc/hosts".format(website),
        "with sudo",
    )


@when("I disable any internet connection on the machine")
@when("I disable any internet connection on the `{machine_name}` machine")
def disable_internet_connection(context, machine_name=SUT):
    when_i_run_command(
        context,
        "ip route del default",
        "with sudo",
        machine_name=machine_name,
    )

    when_i_run_command(
        context,
        "sed -i '$ a precedence ::ffff:0:0/96  100' /etc/gai.conf",
        "with sudo",
        machine_name=machine_name,
    )
