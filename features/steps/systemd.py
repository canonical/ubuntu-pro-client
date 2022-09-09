import datetime
import logging
import re

from behave import then

from features.steps.shell import when_i_run_command


def systemd_timer_info(context, timer_name, all=False):
    all_flag = " --all" if all else ""
    when_i_run_command(
        context,
        "systemctl list-timers {}.timer{}".format(timer_name, all_flag),
        "with sudo",
    )
    output = context.process.stdout.strip()
    lines = output.split("\n")
    return next((line for line in lines if timer_name in line), None)


@then("I verify the `{timer_name}` systemd timer is disabled")
def verify_systemd_timer_disabled(context, timer_name):
    timer_info_str = systemd_timer_info(context, timer_name)
    if timer_info_str is not None:
        raise AssertionError(
            "timer {} is not disabled:\n{}".format(timer_name, timer_info_str)
        )


@then(
    "I verify the `{timer_name}` systemd timer ran within the last `{seconds}` seconds"  # noqa: E501
)
def verify_systemd_timer_ran(context, timer_name, seconds):
    timer_info_str = systemd_timer_info(context, timer_name, all=True)
    if timer_info_str is None:
        raise AssertionError(
            "timer {} is not enabled or does not exist".format(timer_name)
        )
    match = re.match(r".*(left|n/a|ago)\s+(.+) UTC\s+(.+) ago", timer_info_str)
    if match is None:
        raise AssertionError(
            "timer {} has never run:\n{}".format(timer_name, timer_info_str)
        )
    datestr = match.group(2)
    last_ran = datetime.datetime.strptime(datestr, "%a %Y-%m-%d %H:%M:%S")
    if (datetime.datetime.utcnow() - last_ran) > datetime.timedelta(
        seconds=int(seconds)
    ):
        raise AssertionError(
            "timer {} has not run within {} seconds:\n{}".format(
                timer_name, seconds, timer_info_str
            )
        )


@then(
    "I verify the `{timer_name}` systemd timer is scheduled to run within `{minutes}` minutes"  # noqa: E501
)
def verify_systemd_timer_scheduled(context, timer_name, minutes):
    timer_info_str = systemd_timer_info(context, timer_name)
    if timer_info_str is None:
        raise AssertionError(
            "timer {} is not enabled or does not exist".format(timer_name)
        )
    match = re.match(r"^(.+) UTC\s+(.+) left", timer_info_str)
    if match is None:
        raise AssertionError(
            "timer {} is not scheduled to run:\n{}".format(
                timer_name, timer_info_str
            )
        )
    datestr = match.group(1)
    next_run = datetime.datetime.strptime(datestr, "%a %Y-%m-%d %H:%M:%S")
    if (next_run - datetime.datetime.utcnow()) > datetime.timedelta(
        minutes=int(minutes)
    ):
        raise AssertionError(
            "timer {} is not scheduled to run within {} minutes:\n{}".format(
                timer_name, minutes, timer_info_str
            )
        )


@then(
    "I verify the `{timer_name}` systemd timer either ran within the past `{seconds}` seconds OR is scheduled to run within `{minutes}` minutes"  # noqa: E501
)
def verify_systemd_timer_ran_or_scheduled(
    context, timer_name, seconds, minutes
):
    ran_error = None
    going_to_run_error = None
    try:
        verify_systemd_timer_ran(context, timer_name, seconds)
    except AssertionError as e:
        ran_error = e
    try:
        verify_systemd_timer_scheduled(context, timer_name, minutes)
    except AssertionError as e:
        going_to_run_error = e

    if ran_error and going_to_run_error:
        raise AssertionError("{}\n{}".format(ran_error, going_to_run_error))


@then(
    "on `{release}`, systemd status output says memory usage is less than `{mb_limit}` MB"  # noqa
)
def systemd_memory_usage_less_than(context, release, mb_limit):
    curr_release = context.active_outline["release"]
    if release != curr_release:
        logging.debug("Skipping for {}".format(curr_release))
        return
    match = re.search(r"Memory: (.*)M", context.process.stdout.strip())
    if match is None:
        raise AssertionError(
            "Memory usage not present in current process stdout"
        )
    mb_used = float(match.group(1))
    logging.debug("Found {}M".format(mb_used))

    mb_limit_float = float(mb_limit)
    if mb_used > mb_limit_float:
        raise AssertionError(
            "Using more memory than expected ({}M)".format(mb_used)
        )
