import datetime
import shlex

from behave import given, then, when
from hamcrest import assert_that, equal_to

from features.util import launch_lxd_container, lxc_exec


CONTAINER_PREFIX = "behave-test-"


@given("a trusty lxd container with ubuntu-advantage-tools installed")
def given_a_trusty_lxd_container(context):
    now = datetime.datetime.now()
    context.container_name = CONTAINER_PREFIX + now.strftime("%s%f")
    launch_lxd_container(context, context.image_name, context.container_name)


@when("I run `{command}` as {user}")
def when_i_run_command(context, command, user):
    prefix = []
    if user == "root":
        prefix = ["sudo"]
    elif user != "non-root":
        raise Exception(
            "The two acceptable values for user are: root, non-root"
        )
    process = lxc_exec(
        context.container_name,
        prefix + shlex.split(command),
        capture_output=True,
        text=True,
    )
    context.process = process


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))
