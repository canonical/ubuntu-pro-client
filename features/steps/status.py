from behave import when

from features.steps.shell import when_i_run_command


@when("I do a preflight check for `{contract_token}` {user_spec}")
def when_i_preflight(context, contract_token, user_spec, verify_return=True):
    token = getattr(context.pro_config, contract_token, "invalid_token")
    command = "pro status --simulate-with-token {}".format(token)
    if user_spec == "with the all flag":
        command += " --all"
    if "formatted as" in user_spec:
        output_format = user_spec.split()[2]
        command += " --format {}".format(output_format)
    when_i_run_command(
        context=context,
        command=command,
        user_spec="as non-root",
        verify_return=verify_return,
    )


@when(
    "I verify that a preflight check for `{contract_token}` {user_spec} exits {exit_codes}"  # noqa
)
def when_i_attempt_preflight(context, contract_token, user_spec, exit_codes):
    when_i_preflight(context, contract_token, user_spec, verify_return=False)

    expected_codes = exit_codes.split(",")
    assert str(context.process.returncode) in expected_codes
