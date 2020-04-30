import datetime
import shlex

from behave import given, then, when
from hamcrest import assert_that, equal_to, matches_regexp

from features.util import launch_lxd_container, lxc_exec


CONTAINER_PREFIX = "behave-test-"


@given("a series lxd container with ubuntu-advantage-tools installed")
def given_a_lxd_container(context):
    series = context.current_series
    if series in context.reuse_container:
        context.container_name = context.reuse_container[series]
    else:
        now = datetime.datetime.now()
        context.container_name = (
            CONTAINER_PREFIX + series + now.strftime("-%s%f")
        )
        launch_lxd_container(
            context, context.series_image_name[series], context.container_name
        )


@when("I run `{command}` {user_spec}")
def when_i_run_command(context, command, user_spec):
    prefix = get_command_prefix_for_user_spec(user_spec)
    process = lxc_exec(
        context.container_name,
        prefix + shlex.split(command),
        capture_output=True,
        text=True,
    )
    context.process = process


@when("I attach contract_token {user_spec}")
def when_i_attach_token(context, user_spec):
    token = context.config.contract_token
    when_i_run_command(context, "ua attach %s" % token, user_spec)


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("stdout matches regexp")
def then_stdout_matches_regexp(context):
    assert_that(context.process.stdout.strip(), matches_regexp(context.text))


@then("stderr matches regexp")
def then_stderr_matches_regexp(context):
    assert_that(context.process.stderr.strip(), matches_regexp(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))


def get_command_prefix_for_user_spec(user_spec):
    prefix = []
    if user_spec == "with sudo":
        prefix = ["sudo"]
    elif user_spec != "as non-root":
        raise Exception(
            "The two acceptable values for user_spec are: 'with sudo',"
            " 'as non-root'"
        )
    return prefix
