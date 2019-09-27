import subprocess
from typing import List

from behave import given, then, when
from hamcrest import assert_that, equal_to


CONTAINER_NAME = "behave-test"


def _lxc_exec(cmd: List[str], *args, **kwargs):
    return subprocess.run(
        ["lxc", "exec", CONTAINER_NAME, "--"] + cmd, *args, **kwargs
    )


@given("a trusty lxd container")
def step_impl(context):
    subprocess.run(["lxc", "launch", "ubuntu:trusty", CONTAINER_NAME])


@given("ubuntu-advantage-tools is installed")
def step_impl(context):
    _lxc_exec(
        ["add-apt-repository", "--yes", "ppa:canonical-server/ua-client-daily"]
    )
    _lxc_exec(["apt-get", "update", "-q"])
    _lxc_exec(["apt-get", "install", "-q", "-y", "ubuntu-advantage-tools"])


@when("I run `ua status` as non-root")
def step_impl(context):
    process = _lxc_exec(["ua", "status"], capture_output=True, text=True)
    context.output = process.stdout.strip()


@then("I will see the following output")
def step_impl(context):
    assert_that(context.output, equal_to(context.text))
