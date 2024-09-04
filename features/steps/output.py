import json
import logging
import re
import textwrap

import jq  # type: ignore
import jsonschema  # type: ignore
import yaml
from behave import then, when
from hamcrest import assert_that, contains_string, equal_to, not_

from features.steps.shell import when_i_run_command
from features.util import SafeLoaderWithoutDatetime, process_template_vars


@then("I will see the following on {stream}")
def then_i_will_see_on_stream(context, stream):
    content = getattr(context.process, stream).strip()
    text = process_template_vars(context, context.text)
    logging.debug("repr(expected): %r", text)
    logging.debug("repr(actual): %r", content)
    if not text == content:
        raise AssertionError(
            "Expected to find exactly:\n{}\nBut got:\n{}".format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


@then("if `{value1}` in `{value2}` and stdout matches regexp")
def then_conditional_stdout_matches_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_matches_regexp(context, "stdout")


@then("if `{value1}` in `{value2}` and stdout contains substring")
def then_conditional_stdout_contains_substring(context, value1, value2):
    if value1 in value2.split(" or "):
        then_stream_contains_substring(context, "stdout")


@then("if `{value1}` in `{value2}` and stderr matches regexp")
def then_conditional_stderr_matches_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_matches_regexp(context, "stderr")


@then("if `{value1}` in `{value2}` and stdout does not match regexp")
def then_conditional_stdout_does_not_match_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_does_not_match_regexp(context, "stdout")


@then("if `{value1}` in `{value2}` then output is")
def then_conditional_stdout_is(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_i_will_see_on_stream(context, "stdout")


@then("if `{value1}` not in `{value2}` and stdout matches regexp")
def then_not_in_conditional_stdout_does_not_match_regexp(
    context, value1, value2
):
    """Only apply regex assertion if value1 not in value2."""
    if value1 not in value2.split(" or "):
        then_stream_matches_regexp(context, "stdout")


@then("{stream} does not match regexp")
def then_stream_does_not_match_regexp(context, stream):
    text = process_template_vars(context, context.text)
    content = getattr(context.process, stream).strip()
    if re.compile(text).search(content) is not None:
        raise AssertionError(
            "Expected to NOT match regexp:\n{}\nBut got:\n{}".format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


def compare_regexp(expected_regex, actual_output):
    if re.compile(expected_regex).search(actual_output) is None:
        raise AssertionError(
            "Expected to match regexp:\n{}\nBut got:\n{}".format(
                textwrap.indent(expected_regex, "  "),
                textwrap.indent(actual_output, "  "),
            )
        )


def process_api_data(context, api_key=None, escape=True):
    json_data = json.loads(context.process.stdout.strip())
    if escape:
        context.text = context.text.replace("[", "\\[")
        context.text = context.text.replace("]", "\\]")
        context.text = context.text.replace("(", "\\(")
        context.text = context.text.replace(")", "\\)")
        context.text = context.text.replace("\\n", "\\\\n")

    if api_key is None:
        return json.dumps(json_data, indent=2)
    else:
        return json.dumps(json_data[api_key], indent=2)


@then("API full output matches regexp")
def then_api_output_matches_regexp(context):
    content = process_api_data(context)
    text = process_template_vars(context, context.text)
    compare_regexp(text, content)


@then("API data field output matches regexp")
def then_api_data_output_matches_regexp(context):
    content = process_api_data(context, api_key="data")
    text = process_template_vars(context, context.text)
    compare_regexp(text, content)


@then("API data field output is")
def then_api_data_output_is(context):
    content = process_api_data(context, api_key="data", escape=False)
    text = process_template_vars(context, context.text)
    if not text == content:
        raise AssertionError(
            "Expected to find exactly:\n{}\nBut got:\n{}".format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


@then("API errors field output matches regexp")
def then_api_errors_output_matches_regexp(context):
    content = process_api_data(context, api_key="errors")
    text = process_template_vars(context, context.text)
    compare_regexp(text, content)


@then("API errors field output is")
def then_api_errors_output_is(context):
    content = process_api_data(context, api_key="errors", escape=False)
    text = process_template_vars(context, context.text)
    if not text == content:
        raise AssertionError(
            "Expected to find exactly:\n{}\nBut got:\n{}".format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


@then("API warnings field output matches regexp")
def then_api_warnings_output_matches_regexp(context):
    content = process_api_data(context, api_key="warnings")
    text = process_template_vars(context, context.text)
    compare_regexp(text, content)


@then("{stream} matches regexp")
def then_stream_matches_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    text = process_template_vars(context, context.text)
    compare_regexp(text, content)


@then("{stream} contains substring")
def then_stream_contains_substring(context, stream):
    content = getattr(context.process, stream).strip()
    text = process_template_vars(context, context.text)
    if text not in content:
        raise AssertionError(
            (
                "Expected to find substring:\n{}\n"
                + "But couldn't find it in:\n{}"
            ).format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


@then("{stream} does not contain substring")
def then_stream_not_contains_substring(context, stream):
    content = getattr(context.process, stream).strip()
    text = process_template_vars(context, context.text)
    assert_that(content, not_(contains_string(text)))
    if text in content:
        raise AssertionError(
            (
                "Expected to NOT find substring:\n{}\n"
                + "But did find it in:\n{}"
            ).format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


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


@when("I verify that `{field}` field is redacted in the logs")
def i_verify_field_is_redacted_in_the_logs(context, field):
    when_i_run_command(
        context, "cat /var/log/ubuntu-advantage.log", "with sudo"
    )
    context.text = field + "<REDACTED>"
    then_stream_contains_substring(context, "stdout")


@when("I apply this jq filter `{jq_filter}` to the output")
def i_apply_jq_filter(context, jq_filter):
    context.process.stdout = (
        jq.compile(jq_filter).input_text(context.process.stdout.strip()).text()
    )


@when("I apply this jq filter `{jq_filter}` to the API data field output")
def i_apply_jq_filter_to_api_data(context, jq_filter):
    content = process_api_data(context, api_key="data", escape=False)
    context.process.stdout = jq.compile(jq_filter).input_text(content).text()
