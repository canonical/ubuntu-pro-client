import json
import logging
import urllib

import requests
import yaml
from behave import then, when
from hamcrest import assert_that, equal_to, not_

from features.steps.files import (
    change_config_key_to_use_value,
    when_i_create_file_with_content,
)
from features.steps.shell import when_i_run_command
from features.util import SUT, process_template_vars
from uaclient import util
from uaclient.defaults import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_PRIVATE_MACHINE_TOKEN_PATH,
)


@when("I update contract to use `{contract_field}` as `{new_value}`")
def when_i_update_contract_field_to_new_value(
    context, contract_field, new_value
):
    new_value = process_template_vars(context, new_value)
    when_i_run_command(
        context,
        'sed -i \'s/"{}": "[^"]*"/"{}": "{}"/g\' {}'.format(
            contract_field,
            contract_field,
            new_value,
            DEFAULT_PRIVATE_MACHINE_TOKEN_PATH,
        ),
        user_spec="with sudo",
    )


@when("I change contract to staging {user_spec}")
def change_contract_endpoint_to_staging(context, user_spec):
    when_i_run_command(
        context,
        "sed -i 's/contracts.can/contracts.staging.can/' {}".format(
            DEFAULT_CONFIG_FILE
        ),
        user_spec,
    )


def change_contract_endpoint_to_production(context, user_spec):
    when_i_run_command(
        context,
        "sed -i 's/contracts.staging.can/contracts.can/' {}".format(
            DEFAULT_CONFIG_FILE
        ),
        user_spec,
    )


@when("I save the `{key}` value from the contract")
def i_save_the_key_value_from_contract(context, key):
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_PRIVATE_MACHINE_TOKEN_PATH),
        "with sudo",
    )
    output = context.process.stdout.strip()

    if output:
        if not hasattr(context, "saved_values"):
            setattr(context, "saved_values", {})

        context.saved_values[key] = output


def _get_saved_attr(context, key):
    saved_value = getattr(context, "saved_values", {}).get(key)

    if saved_value is None:
        raise AssertionError(
            "Value for key {} was not previously saved\n".format(key)
        )

    return saved_value


@then("I verify that `{key}` value has been updated on the contract")
@then(
    "I verify that `{key}` value has been updated on the contract on the `{machine_name}` machine"  # noqa: E501
)
def i_verify_that_key_value_has_been_updated(context, key, machine_name=SUT):
    saved_value = _get_saved_attr(context, key)
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_PRIVATE_MACHINE_TOKEN_PATH),
        "with sudo",
        machine_name=machine_name,
    )
    assert_that(context.process.stdout.strip(), not_(equal_to(saved_value)))


@then("I verify that `{key}` value has not been updated on the contract")
def i_verify_that_key_value_has_not_been_updated(context, key):
    saved_value = _get_saved_attr(context, key)
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_PRIVATE_MACHINE_TOKEN_PATH),
        "with sudo",
    )
    assert_that(context.process.stdout.strip(), equal_to(saved_value))


@when("I restore the saved `{key}` value on contract")
def i_restore_the_saved_key_value_on_contract(context, key):
    saved_value = _get_saved_attr(context, key)
    when_i_update_contract_field_to_new_value(
        context=context,
        contract_field=key.split(".")[-1],
        new_value=saved_value,
    )


@when("I set the machine token overlay to the following yaml")
def when_i_set_the_machine_token_overlay(context):
    json_text = json.dumps(
        yaml.safe_load(context.text), cls=util.DatetimeAwareJSONEncoder
    )
    when_i_create_file_with_content(
        context,
        "/var/lib/ubuntu-advantage/machine-token-overlay.json",
        text=json_text,
    )
    change_config_key_to_use_value(
        context,
        "features",
        "{ machine_token_overlay: "
        "/var/lib/ubuntu-advantage/machine-token-overlay.json}",
    )


@when("I set the test contract expiration date to `{date_str}`")
def when_i_set_the_test_contract_expiration_date_to(context, date_str):
    date_str = process_template_vars(context, date_str)
    resp = requests.put(
        "https://contracts.staging.canonical.com/v1/contract-items",
        auth=(
            context.pro_config.contract_staging_service_account_username,
            context.pro_config.contract_staging_service_account_password,
        ),
        json=[
            {
                # Do not delete any of these fields. They are all required.
                "contractID": "cAOEJ9Vymiwr47-HZ3FnYR_YDCPILpaTfdloKpojyNPE",
                "id": 39398,
                "effectiveFrom": "2024-01-01T00:00:00Z",
                "effectiveTo": date_str,
                "metric": "units",
                "reason": "contract_created",
                "value": 1000,
            }
        ],
    )
    logging.debug(resp.json())
    assert resp.status_code == 200
