import json
import time

from behave import then, when
from hamcrest import assert_that, equal_to

from features.steps.shell import when_i_run_command
from uaclient.defaults import DEFAULT_CONFIG_FILE
from uaclient.util import DatetimeAwareJSONDecoder


@when("I append the following on uaclient config")
def when_i_append_to_uaclient_config(context):
    cmd = "printf '{}\n' > /tmp/uaclient.conf".format(context.text)
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
