from behave import when

from features.steps.contract import change_contract_endpoint_to_staging
from features.steps.shell import (
    then_i_verify_that_running_cmd_with_spec_exits_with_codes,
    when_i_retry_run_command,
    when_i_run_command,
)

ERROR_CODE = "1"


@when("I attach `{token_type}` {user_spec} and options `{options}`")
def when_i_attach_staging_token_with_options(
    context, token_type, user_spec, options
):
    when_i_attach_staging_token(
        context, token_type, user_spec, options=options
    )


@when("I attach `{token_type}` {user_spec}")
def when_i_attach_staging_token(
    context, token_type, user_spec, verify_return=True, options=""
):
    token = getattr(context.pro_config, token_type)
    if (
        token_type == "contract_token_staging"
        or token_type == "contract_token_staging_expired"
    ):
        change_contract_endpoint_to_staging(context, user_spec)
    cmd = "pro attach {} {}".format(token, options).strip()
    if verify_return:
        when_i_retry_run_command(context, cmd, user_spec, ERROR_CODE)
    else:
        when_i_run_command(context, cmd, user_spec, verify_return=False)


@when("I attempt to attach `{token_type}` {user_spec}")
def when_i_attempt_to_attach_staging_token(context, token_type, user_spec):
    when_i_attach_staging_token(
        context, token_type, user_spec, verify_return=False
    )


@when(
    "I verify that running attach `{spec}` with json response exits `{exit_codes}`"  # noqa
)
def when_i_verify_attach_with_json_response(context, spec, exit_codes):
    cmd = "pro attach {} --format json".format(
        context.pro_config.contract_token
    )
    then_i_verify_that_running_cmd_with_spec_exits_with_codes(
        context=context, cmd_name=cmd, spec=spec, exit_codes=exit_codes
    )


@when(
    "I verify that running attach `{spec}` using expired token with json response fails"  # noqa
)
def when_i_verify_attach_expired_token_with_json_response(context, spec):
    change_contract_endpoint_to_staging(context, user_spec="with sudo")
    cmd = "pro attach {} --format json".format(
        context.pro_config.contract_token_staging_expired
    )
    then_i_verify_that_running_cmd_with_spec_exits_with_codes(
        context=context, cmd_name=cmd, spec=spec, exit_codes=ERROR_CODE
    )
