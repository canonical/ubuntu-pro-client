import datetime
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
    _lxc_exec(context, ["apt-get", "update", "-q"])
    _lxc_exec(
        context, ["apt-get", "install", "-q", "-y", "ubuntu-advantage-tools"]
    )


@when("I run `ua status` as non-root")
def step_impl(context):
    process = _lxc_exec(
        context, ["ua", "status"], capture_output=True, text=True
    )
    context.output = process.stdout.strip()


@then("I will see the following output")
def step_impl(context):
    assert_that(context.output, equal_to(context.text))
