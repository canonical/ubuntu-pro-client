import json
import logging
import re
import textwrap

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
    text = process_template_vars(context, context.text)
    content = getattr(context.process, stream).strip()
    if re.compile(text).search(content) is not None:
        raise AssertionError(
            "Expected to NOT match regexp:\n{}\nBut got:\n{}".format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


@then("{stream} matches regexp")
def then_stream_matches_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    text = process_template_vars(context, context.text)
    if re.compile(text).search(content) is None:
        raise AssertionError(
            "Expected to match regexp:\n{}\nBut got:\n{}".format(
                textwrap.indent(text, "  "), textwrap.indent(content, "  ")
            )
        )


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
