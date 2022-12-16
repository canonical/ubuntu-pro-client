import json

import jsonschema  # type: ignore
import yaml
from behave import then, when
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    matches_regexp,
    not_,
)

from features.steps.shell import when_i_run_command
from features.util import SafeLoaderWithoutDatetime


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("if `{value1}` in `{value2}` and stdout matches regexp")
def then_conditional_stdout_matches_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_matches_regexp(context, "stdout")


@then("if `{value1}` in `{value2}` and stdout does not match regexp")
def then_conditional_stdout_does_not_match_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_does_not_match_regexp(context, "stdout")


@then("if `{value1}` not in `{value2}` and stdout matches regexp")
def then_not_in_conditional_stdout_does_not_match_regexp(
    context, value1, value2
):
    """Only apply regex assertion if value1 not in value2."""
    if value1 not in value2.split(" or "):
        then_stream_matches_regexp(context, "stdout")


@then("{stream} does not match regexp")
def then_stream_does_not_match_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    assert_that(content, not_(matches_regexp(context.text)))


@then("{stream} matches regexp")
def then_stream_matches_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    text = context.text
    if "<ci-proxy-ip>" in text and "proxy" in context.machines:
        text = text.replace(
            "<ci-proxy-ip>", context.machines["proxy"].instance.ip
        )
    assert_that(content, matches_regexp(text))


@then("{stream} contains substring")
def then_stream_contains_substring(context, stream):
    content = getattr(context.process, stream).strip()
    assert_that(content, contains_string(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))


@then("I will see the uaclient version on stdout")
def then_i_will_see_the_uaclient_version_on_stdout(context):
    python_import = "from uaclient.version import get_version"

    cmd = "python3 -c '{}; print(get_version())'".format(python_import)

    actual_version = context.process.stdout.strip()
    when_i_run_command(context, cmd, "as non-root")
    expected_version = context.process.stdout.strip()

    assert_that(expected_version, equal_to(actual_version))


@then("stdout is a {output_format} matching the `{schema}` schema")
def stdout_matches_the_json_schema(context, output_format, schema):
    if output_format == "json":
        instance = json.loads(context.process.stdout.strip())
    elif output_format == "yaml":
        instance = yaml.load(
            context.process.stdout.strip(), SafeLoaderWithoutDatetime
        )
    with open("features/schemas/{}.json".format(schema), "r") as schema_file:
        jsonschema.validate(instance=instance, schema=json.load(schema_file))


@then("the {output_format} API response data matches the `{schema}` schema")
def api_response_matches_schema(context, output_format, schema):
    if output_format == "json":
        instance = json.loads(context.process.stdout.strip())
    elif output_format == "yaml":
        instance = yaml.load(
            context.process.stdout.strip(), SafeLoaderWithoutDatetime
        )
    with open("features/schemas/{}.json".format(schema), "r") as schema_file:
        jsonschema.validate(
            instance=instance.get("data", {}).get("attributes"),
            schema=json.load(schema_file),
        )


@when("I verify root and non-root `{cmd}` calls have the same output")
def root_vs_nonroot_cmd_comparison(context, cmd):
    when_i_run_command(context, cmd, "with sudo")
    root_status_stdout = context.process.stdout.strip()
    root_status_stderr = context.process.stderr.strip()

    when_i_run_command(context, cmd, "as non-root")
    nonroot_status_stdout = context.process.stdout.strip()
    nonroot_status_stderr = context.process.stderr.strip()

    assert_that(root_status_stdout, nonroot_status_stdout)
    assert root_status_stderr == nonroot_status_stderr
