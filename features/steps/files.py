import datetime
import json
import os
import re
import tempfile

from behave import then, when
from hamcrest import assert_that, matches_regexp

from features.steps.shell import when_i_run_command
from features.util import SUT
from uaclient.defaults import DEFAULT_CONFIG_FILE


@when("I add this text on `{file_name}` on `{machine_name}` above `{line}`")
def when_i_add_this_text_on_file_above_line(
    context, file_name, machine_name, line
):
    command = 'sed -i "s/{}/{}\\n{}/" {}'.format(
        line, context.text, line, file_name
    )
    when_i_run_command(
        context, command, "with sudo", machine_name=machine_name
    )


@when("I verify `{file_name}` is empty on `{machine_name}` machine")
def when_i_verify_file_is_empty_on_machine(context, file_name, machine_name):
    command = 'sh -c "cat {} | wc -l"'.format(file_name)
    when_i_run_command(
        context, command, user_spec="with sudo", machine_name=machine_name
    )

    assert_that(context.process.stdout.strip(), matches_regexp("0"))


@when("I create the file `{file_path}` with the following")
def when_i_create_file_with_content(
    context, file_path, machine_name=SUT, text=None
):
    if text is None:
        text = context.text

    if "<ci-proxy-ip>" in text and "proxy" in context.machines:
        text = text.replace(
            "<ci-proxy-ip>", context.machines["proxy"].instance.ip
        )
    if "<cloud>" in text:
        text = text.replace("<cloud>", context.config.cloud)

    date_match = re.search(r"<now(?P<offset>.*)>", text)
    if date_match:
        day_offset = date_match.group("offset")
        offset = 0 if day_offset == "" else int(day_offset)
        now = datetime.datetime.utcnow()
        contract_expiry = now + datetime.timedelta(days=offset)
        new_value = '"' + contract_expiry.strftime("%Y-%m-%dT00:00:00Z") + '"'
        orig_str_value = "<now" + day_offset + ">"
        text = text.replace(orig_str_value, new_value)

    with tempfile.TemporaryDirectory() as tmpd:
        tmpf_path = os.path.join(tmpd, "tmpfile")
        with open(tmpf_path, mode="w") as tmpf:
            tmpf.write(text)
        context.machines[machine_name].instance.push_file(
            tmpf_path, "/tmp/behave_tmpfile"
        )
    when_i_run_command(
        context,
        "cp /tmp/behave_tmpfile {}".format(file_path),
        "with sudo",
        machine_name=machine_name,
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
        machine_name, _, port = value.split(":")
        ip_value = context.machines[machine_name].instance.ip
        value = "http:\/\/{}:{}".format(ip_value, port)  # noqa: W605

    when_i_run_command(
        context,
        "sed -i 's/{}: .*/{}: {}/g' {}".format(
            key, key, value, DEFAULT_CONFIG_FILE
        ),
        "with sudo",
    )


@when("I set `{key}` = `{json_value}` in json file `{filename}`")
def when_i_set_key_val_json_file(context, key, json_value, filename):
    when_i_run_command(
        context,
        "cat {}".format(filename),
        "with sudo",
    )
    val = json.loads(json_value)
    content = json.loads(context.process.stdout)
    content[key] = val
    context.text = json.dumps(content)
    when_i_create_file_with_content(context, filename)
