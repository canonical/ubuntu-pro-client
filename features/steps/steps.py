import datetime
import shlex
import subprocess
from typing import List

from behave import given, then, when
from behave.runner import Context
from hamcrest import assert_that, equal_to


CONTAINER_PREFIX = "behave-test-"


def _lxc_exec(context: Context, cmd: List[str], *args, **kwargs):
    return subprocess.run(
        ["lxc", "exec", context.container_name, "--"] + cmd, *args, **kwargs
    )


@given("a trusty lxd container")
def step_impl(context):
    now = datetime.datetime.now()
    context.container_name = CONTAINER_PREFIX + now.strftime("%s%f")
    subprocess.run(["lxc", "launch", "ubuntu:trusty", context.container_name])

    def cleanup_container():
        subprocess.run(["lxc", "stop", context.container_name])
        subprocess.run(["lxc", "delete", context.container_name])

    context.add_cleanup(cleanup_container)


@given("ubuntu-advantage-tools is installed")
def step_impl(context):
    _lxc_exec(
        context,
        [
            "add-apt-repository",
            "--yes",
            "ppa:canonical-server/ua-client-daily",
        ],
    )
    _lxc_exec(context, ["apt-get", "update", "-qq"])
    _lxc_exec(
        context, ["apt-get", "install", "-qq", "-y", "ubuntu-advantage-tools"]
    )


@when("I run `{command}` as non-root")
def step_impl(context, command):
    process = _lxc_exec(
        context, shlex.split(command), capture_output=True, text=True
    )
    context.process = process


@then("I will see the following on stdout")
def step_impl(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("I will see the following on stderr")
def step_impl(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))
