import datetime
import shlex
import subprocess
import time
from typing import List

from behave import given, then, when
from behave.runner import Context
from hamcrest import assert_that, equal_to


CONTAINER_PREFIX = "behave-test-"


def _lxc_exec(context: Context, cmd: List[str], *args, **kwargs):
    return subprocess.run(
        ["lxc", "exec", context.container_name, "--"] + cmd, *args, **kwargs
    )


def _wait_for_boot(context: Context) -> None:
    retries = [2] * 5
    for sleep_time in retries:
        process = _lxc_exec(
            context, ["runlevel"], capture_output=True, text=True
        )
        try:
            _, runlevel = process.stdout.strip().split(" ", 2)
        except ValueError:
            print("Unexpected runlevel output: ", process.stdout.strip())
            runlevel = None
        if runlevel == "2":
            break
        time.sleep(sleep_time)
    else:
        raise Exception("System did not boot in {}s".format(sum(retries)))


@given("a trusty lxd container")
def given_a_trusty_lxd_container(context):
    now = datetime.datetime.now()
    context.container_name = CONTAINER_PREFIX + now.strftime("%s%f")
    subprocess.run(["lxc", "launch", "ubuntu:trusty", context.container_name])

    def cleanup_container():
        subprocess.run(["lxc", "stop", context.container_name])
        subprocess.run(["lxc", "delete", context.container_name])

    context.add_cleanup(cleanup_container)

    _wait_for_boot(context)


@given("ubuntu-advantage-tools is installed")
def given_uat_is_installed(context):
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
def when_i_run_command(context, command):
    process = _lxc_exec(
        context, shlex.split(command), capture_output=True, text=True
    )
    context.process = process


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))
