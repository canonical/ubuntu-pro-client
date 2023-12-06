import json

from behave import then, when

from features.steps.shell import when_i_run_command
from features.util import SUT


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


def get_enabled_services(context, machine_name=SUT):
    when_i_run_command(
        context,
        "pro api u.pro.status.enabled_services.v1",
        "as non-root",
        machine_name=machine_name,
    )

    data = json.loads(context.process.stdout.strip())
    enabled_services = []
    for enabled_service in data["data"]["attributes"]["enabled_services"]:
        if enabled_service["variant_enabled"]:
            enabled_services.append(enabled_service["variant_name"])
        else:
            enabled_services.append(enabled_service["name"])

    return enabled_services


@then("I verify that `{service}` is disabled")
def i_verify_that_service_is_disabled(context, service):
    enabled_services = get_enabled_services(context)

    if service in enabled_services:
        raise AssertionError(
            "Expected {} to not be enabled\nEnabled services: {}".format(
                service, ", ".join(enabled_services)
            )
        )


@then("I verify that `{service}` is enabled")
def i_verify_that_service_is_enabled(context, service):
    enabled_services = get_enabled_services(context)

    if service not in enabled_services:
        raise AssertionError(
            "Expected {} to be enabled\nEnabled services: {}".format(
                service, ", ".join(enabled_services)
            )
        )
