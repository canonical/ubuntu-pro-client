import json
import os
import tempfile

import yaml
from behave import then, when
from hamcrest import assert_that, equal_to, matches_regexp

from features.steps.shell import when_i_run_command
from features.util import SUT, process_template_vars
from uaclient.defaults import DEFAULT_CONFIG_FILE


def _get_file_contents(
    context, file_path: str, machine_name: str = SUT
) -> str:
    # pycloudlib pull_file doesn't work on root readable files
    when_i_run_command(
        context,
        "cat {}".format(file_path),
        "with sudo",
        machine_name=machine_name,
    )
    return context.process.stdout


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


@when("I verify `{file_name}` is empty")
@when("I verify `{file_name}` is empty on `{machine_name}` machine")
def when_i_verify_file_is_empty_on_machine(
    context, file_name, machine_name=SUT
):
    command = 'sh -c "cat {} | wc -l"'.format(file_name)
    when_i_run_command(
        context, command, user_spec="with sudo", machine_name=machine_name
    )

    assert_that(context.process.stdout.strip(), matches_regexp("0"))


@when(
    "I create the file `{file_path}` on the `{machine_name}` machine with the following"  # noqa: E501
)
@when("I create the file `{file_path}` with the following")
def when_i_create_file_with_content(
    context, file_path, machine_name=SUT, text=None
):
    if text is None:
        text = context.text
    text = process_template_vars(context, text)

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
    token = getattr(context.pro_config, token_name)
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


@when("I change config key `{key}` to use value `{yaml_value}`")
def change_config_key_to_use_value(context, key, yaml_value):
    yaml_value = process_template_vars(context, yaml_value)

    content = _get_file_contents(context, DEFAULT_CONFIG_FILE)
    cfg = yaml.safe_load(content)
    val = yaml.safe_load(yaml_value)
    cfg[key] = val
    new_content = yaml.dump(cfg)

    when_i_create_file_with_content(
        context, DEFAULT_CONFIG_FILE, text=new_content
    )


@when("I set `{key}` = `{json_value}` in json file `{filename}`")
def when_i_set_key_val_json_file(context, key, json_value, filename):
    json_value = process_template_vars(context, json_value)

    content_str = _get_file_contents(context, filename)
    content = json.loads(content_str)
    val = json.loads(json_value)
    content[key] = val
    new_content = json.dumps(content)

    when_i_create_file_with_content(context, filename, text=new_content)


@when("I move `{src_machine}` `{src_path}` to `{dest_machine}` `{dest_path}`")
def when_i_move_file_from_one_machine_to_another(
    context, src_machine, src_path, dest_machine, dest_path
):
    content = _get_file_contents(context, src_path, machine_name=src_machine)
    when_i_create_file_with_content(
        context, dest_path, machine_name=dest_machine, text=content
    )


@then("I verify that `{file_path}` is world readable")
def then_i_verify_that_file_is_world_readable(
    context, file_path, machine_name=SUT
):
    when_i_run_command(
        context,
        "stat -c '%a' {}".format(file_path),
        "with sudo",
        machine_name=machine_name,
    )

    assert_that(context.process.stdout.strip(), equal_to("644"))
