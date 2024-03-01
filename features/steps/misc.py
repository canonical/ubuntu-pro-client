import json
import re
import time

from behave import then, when
from hamcrest import assert_that, equal_to

from features.steps.files import when_i_create_file_with_content
from features.steps.packages import when_i_apt_install
from features.steps.shell import when_i_run_command, when_i_run_shell_command
from uaclient.defaults import DEFAULT_CONFIG_FILE
from uaclient.util import DatetimeAwareJSONDecoder

AUTOCOMPLETE_TEST_FILE = """\
#!/usr/bin/expect -f

set command [lindex $argv 0];
set send_human {.1 .3 1 .05 2}
set timeout 10

spawn /bin/bash
expect -exact "$"
send -h "$command \t\t"
expect -exact "$ $command"
"""


@when("I append the following on uaclient config")
def when_i_append_to_uaclient_config(context):
    cmd = "printf '\n{}\n' > /tmp/uaclient.conf".format(context.text)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "as non-root")

    cmd = "cat /tmp/uaclient.conf >> {}".format(DEFAULT_CONFIG_FILE)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I wait `{seconds}` seconds")
def when_i_wait(context, seconds):
    time.sleep(int(seconds))


@then("I verify that the timer interval for `{job}` is `{interval}`")
def verify_timer_interval_for_job(context, job, interval):
    when_i_run_command(
        context, "cat /var/lib/ubuntu-advantage/jobs-status.json", "with sudo"
    )
    jobs_status = json.loads(
        context.process.stdout.strip(), cls=DatetimeAwareJSONDecoder
    )
    last_run = jobs_status[job]["last_run"]
    next_run = jobs_status[job]["next_run"]
    run_diff = next_run - last_run

    assert_that(run_diff.seconds, equal_to(int(interval)))


@when("I prepare the autocomplete test")
def prepare_autocomplete_test(context):
    when_i_run_command(context, "apt update", "with sudo")
    when_i_apt_install(context, "expect")
    when_i_create_file_with_content(
        context, "/tmp/test_autocomplete.exp", text=AUTOCOMPLETE_TEST_FILE
    )
    when_i_run_command(
        context, "chmod +x /tmp/test_autocomplete.exp", "with sudo"
    )


@when("I press tab twice to autocomplete the `{command}` command")
def when_i_autocomplete_command(context, command):
    when_i_run_command(
        context,
        "/tmp/test_autocomplete.exp '{}'".format(command),
        "as non-root",
    )


@then("I verify that the folder `{folder}` does not exist")
def then_folder_does_not_exist(context, folder):
    when_i_run_shell_command(
        context,
        command="ls {} || echo 'empty'".format(folder),
        user_spec="with sudo",
    )
    assert_that(context.process.stdout.strip(), equal_to("empty"))


@when("I regexify `{var_name}` stored var")
def regixify_stored_var(context, var_name):
    val = context.stored_vars.get(var_name)

    if val:
        context.stored_vars[var_name] = re.escape(val)
