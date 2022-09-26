import os
import tempfile

from behave import then, when
from hamcrest import assert_that, matches_regexp

from features.steps.shell import (
    when_i_run_command,
    when_i_run_command_on_machine,
)
from uaclient.defaults import DEFAULT_CONFIG_FILE


@when("I add this text on `{file_name}` on `{instance_name}` above `{line}`")
def when_i_add_this_text_on_file_above_line(
    context, file_name, instance_name, line
):
    command = 'sed -i "s/{}/{}\\n{}/" {}'.format(
        line, context.text, line, file_name
    )
    when_i_run_command(
        context, command, "with sudo", instance_name=instance_name
    )


@when("I verify `{file_name}` is empty on `{instance_name}` machine")
def when_i_verify_file_is_empty_on_machine(context, file_name, instance_name):
    command = 'sh -c "cat {} | wc -l"'.format(file_name)
    when_i_run_command(
        context, command, user_spec="with sudo", instance_name=instance_name
    )

    assert_that(context.process.stdout.strip(), matches_regexp("0"))


@when("I create the file `{file_path}` with the following")
def when_i_create_file_with_content(context, file_path, machine="uaclient"):
    text = context.text
    if "<ci-proxy-ip>" in text and "proxy" in context.instances:
        text = text.replace("<ci-proxy-ip>", context.instances["proxy"].ip)
    with tempfile.TemporaryDirectory() as tmpd:
        tmpf_path = os.path.join(tmpd, "tmpfile")
        with open(tmpf_path, mode="w") as tmpf:
            tmpf.write(text)
        context.instances[machine].push_file(tmpf_path, "/tmp/behave_tmpfile")
    when_i_run_command_on_machine(
        context,
        "cp /tmp/behave_tmpfile {}".format(file_path),
        "with sudo",
        machine,
    )


@when("I delete the file `{file_path}`")
def when_i_delete_file(context, file_path):
    cmd = "rm -rf {}".format(file_path)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I replace `{original}` in `{filename}` with `{new}`")
def when_i_replace_string_in_file(context, original, filename, new):
    new = new.replace("\\", r"\\")
    new = new.replace("/", r"\/")
    new = new.replace("&", r"\&")
    when_i_run_command(
        context,
        "sed -i 's/{original}/{new}/' {filename}".format(
            original=original, new=new, filename=filename
        ),
        "with sudo",
    )


@when("I replace `{original}` in `{filename}` with token `{token_name}`")
def when_i_replace_string_in_file_with_token(
    context, original, filename, token_name
):
    token = getattr(context.config, token_name)
    when_i_replace_string_in_file(context, original, filename, token)


@then("I verify that files exist matching `{path_regex}`")
def there_should_be_files_matching_regex(context, path_regex):
    when_i_run_command(
        context, "ls {}".format(path_regex), "with sudo", verify_return=False
    )
    if context.process.returncode != 0:
        raise AssertionError("Missing expected files: {}".format(path_regex))


@then("I verify that no files exist matching `{path_regex}`")
def there_should_be_no_files_matching_regex(context, path_regex):
    when_i_run_command(
        context, "ls {}".format(path_regex), "with sudo", verify_return=False
    )
    if context.process.returncode == 0:
        raise AssertionError(
            "Unexpected files found: {}".format(context.process.stdout.strip())
        )


@when("I change config key `{key}` to use value `{value}`")
def change_contract_key_to_use_value(context, key, value):
    if "ip-address" in value:
        machine, _, port = value.split(":")
        ip_value = context.instances[machine].ip
        value = "http:\/\/{}:{}".format(ip_value, port)  # noqa: W605

    when_i_run_command(
        context,
        "sed -i 's/{}: .*/{}: {}/g' {}".format(
            key, key, value, DEFAULT_CONFIG_FILE
        ),
        "with sudo",
    )
