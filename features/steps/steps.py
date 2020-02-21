import datetime
import shlex

from behave import given, then, when
from hamcrest import assert_that, contains_string, equal_to

from features.util import launch_lxd_container, lxc_exec


CONTAINER_PREFIX = "behave-test-"


@given("a trusty lxd container with ubuntu-advantage-tools installed")
def given_a_trusty_lxd_container(context):
    now = datetime.datetime.now()
    context.container_name = CONTAINER_PREFIX + now.strftime("%s%f")
    launch_lxd_container(context, context.image_name, context.container_name)


@when("I run `{command}` {user_spec}")
def when_i_run_command(context, command, user_spec):
    prefix = get_command_prefix_for_user_spec(user_spec)
    if user_spec == "with sudo":
        prefix = ["sudo"]
    elif user_spec != "as non-root":
        raise Exception(
            "The two acceptable values for user_spec are: 'with sudo',"
            " 'as non-root'"
        )
    process = lxc_exec(
        context.container_name,
        prefix + shlex.split(command),
        capture_output=True,
        text=True,
    )
    context.process = process


@when('I attach "{token}" {user_spec}')
def when_i_attach_token(context, token, user_spec):
    token = context.config.contract_token
    if not token:
        context.scenario.skip(
            "Skipping test because you didn't provide a token"
        )
    when_i_run_command(context, "ua attach %s" % token, user_spec)


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("stdout will include")
def then_and_stdout_will_include(context):
    assert_that(context.process.stdout.strip(), contains_string(context.text))
+@then("stdout matches regexp")
+def then_stdout_matches_regexp(context):
+    assert_that(context.process.stdout.strip(), matches_regexp(context.text))

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
