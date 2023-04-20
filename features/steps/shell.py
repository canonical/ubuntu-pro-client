import logging
import shlex
import subprocess
import time

from behave import then, when
from hamcrest import assert_that, equal_to

from features.util import SUT, process_template_vars


@when("I run `{command}` {user_spec}, retrying exit [{exit_codes}]")
def when_i_retry_run_command(context, command, user_spec, exit_codes):
    when_i_run_command(context, command, user_spec, verify_return=False)
    retries = [5, 5, 10]  # Sleep times to wait between retries
    while len(retries) > 0 and str(
        context.process.returncode
    ) in exit_codes.split(","):
        time.sleep(retries.pop(0))
        logging.info(
            "--- Retrying on exit {exit_code}: {command}".format(
                exit_code=context.process.returncode, command=command
            )
        )
        when_i_run_command(context, command, user_spec, verify_return=False)
    logging.warning(
        "Exhausted retries waiting for exit codes: %s. Final exit code: %d",
        exit_codes,
        context.process.returncode,
    )
    assert_that(context.process.returncode, equal_to(0))


@when("I run `{command}` {user_spec}")
@when("I run `{command}` `{user_spec}` on the `{machine_name}` machine")
@when("I run `{command}` `{user_spec}` and stdin `{stdin}`")
def when_i_run_command(
    context,
    command,
    user_spec,
    verify_return=True,
    stdin=None,
    machine_name=SUT,
):
    command = process_template_vars(context, command)
    prefix = get_command_prefix_for_user_spec(user_spec)
    full_cmd = prefix + shlex.split(command)

    if stdin is not None:
        stdin = stdin.replace("\\n", "\n")

    result = context.machines[machine_name].instance.execute(
        full_cmd, stdin=stdin
    )

    process = subprocess.CompletedProcess(
        args=full_cmd,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.return_code,
    )  # type: subprocess.CompletedProcess

    if verify_return and result.return_code != 0:
        logging.error("Error executing command: {}".format(command))
        logging.error("stdout: {}".format(result.stdout))
        logging.error("stderr: {}".format(result.stderr))
    else:
        logging.debug("stdout: {}".format(result.stdout))
        logging.debug("stderr: {}".format(result.stderr))

    if verify_return:
        assert_that(process.returncode, equal_to(0))

    context.process = process


@when("I run shell command `{command}` {user_spec}")
def when_i_run_shell_command(context, command, user_spec):
    when_i_run_command(context, 'sh -c "{}"'.format(command), user_spec)


@then("I verify that the `{cmd_name}` command is not found")
def then_i_should_see_that_the_command_is_not_found(context, cmd_name):
    cmd = "which {} || echo FAILURE".format(cmd_name)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "as non-root")

    expected_return = "FAILURE"
    actual_return = context.process.stdout.strip()
    assert_that(expected_return, equal_to(actual_return))


@then("I verify that running `{cmd_name}` `{spec}` exits `{exit_codes}`")
def then_i_verify_that_running_cmd_with_spec_exits_with_codes(
    context, cmd_name, spec, exit_codes
):
    when_i_run_command(context, cmd_name, spec, verify_return=False)
    logging.debug("got return code: %d", context.process.returncode)
    expected_codes = exit_codes.split(",")
    assert str(context.process.returncode) in expected_codes


@when(
    "I verify that running `{cmd_name}` `{spec}` and stdin `{stdin}` exits `{exit_codes}`"  # noqa
)
def then_i_verify_that_running_cmd_with_spec_and_stdin_exits_with_codes(
    context, cmd_name, spec, stdin, exit_codes
):
    when_i_run_command(
        context, cmd_name, spec, stdin=stdin, verify_return=False
    )

    expected_codes = exit_codes.split(",")
    assert str(context.process.returncode) in expected_codes


@when("I verify that running `{cmd_name}` `{spec}` exits `{exit_codes}`")
def when_i_verify_that_running_cmd_with_spec_exits_with_codes(
    context, cmd_name, spec, exit_codes
):
    then_i_verify_that_running_cmd_with_spec_exits_with_codes(
        context, cmd_name, spec, exit_codes
    )


def get_command_prefix_for_user_spec(user_spec):
    prefix = []
    if user_spec.lstrip() == "with sudo":
        prefix = ["sudo"]
    elif user_spec.lstrip() != "as non-root":
        raise Exception(
            "The two acceptable values for user_spec are: 'with sudo',"
            " 'as non-root'"
        )
    return prefix
