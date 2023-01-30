import socket

from behave import when

from features.steps.shell import when_i_run_command
from features.util import SUT


@when("I disable access to {website}")
def block_access_to_address(context, website):
    address_info = socket.getaddrinfo(website, None)
    # Don't believe the magic? The C code will return a 5-tuple where the
    # actual socket address is the last item, and it is a 4-tuple for ipv6 or
    # a 2-tuple for ipv4, address string being the first item.
    addresses_to_block = set([address[-1][0] for address in address_info])
    for address in addresses_to_block:
        when_i_run_command(
            context,
            "ufw reject out from any to {}".format(address),
            "with sudo",
        )
    when_i_run_command(
        context,
        "ufw enable",
        "with sudo",
        stdin="y\n",
    )


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
