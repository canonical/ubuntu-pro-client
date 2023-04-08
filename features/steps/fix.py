from behave import when

from features.steps.contract import (
    change_contract_endpoint_to_production,
    change_contract_endpoint_to_staging,
)
from features.steps.shell import when_i_run_command


@when("I fix `{issue}` by attaching to a subscription with `{token_type}`")
def when_i_fix_a_issue_by_attaching(context, issue, token_type):
    token = getattr(context.pro_config, token_type)

    if (
        token_type == "contract_token_staging"
        or token_type == "contract_token_staging_expired"
    ):
        change_contract_endpoint_to_staging(context, user_spec="with sudo")
    else:
        change_contract_endpoint_to_production(context, user_spec="with sudo")

    when_i_run_command(
        context=context,
        command="pro fix {}".format(issue),
        user_spec="with sudo",
        stdin="a\n{}\n".format(token),
        verify_return=False,
    )


@when("I fix `{issue}` by enabling required service")
def when_i_fix_a_issue_by_enabling_service(context, issue):
    when_i_run_command(
        context=context,
        command="pro fix {}".format(issue),
        user_spec="with sudo",
        stdin="e\n",
    )


@when("I fix `{issue}` by updating expired token")
def when_i_fix_a_issue_by_updating_expired_token(context, issue):
    token = getattr(context.pro_config, "contract_token")
    when_i_run_command(
        context=context,
        command="pro fix {}".format(issue),
        user_spec="with sudo",
        stdin="r\n{}\n".format(token),
    )
