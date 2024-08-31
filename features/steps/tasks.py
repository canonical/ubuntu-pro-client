import time

from behave import step

from features.steps.shell import when_i_run_command


@step("I start `{task}` command `{command}` in the background")
def start_task(context, task, command):
    when_i_run_command(
        context,
        f"systemd-run --no-block --unit={task} --property=Type=oneshot --property=RemainAfterExit=yes {command}",  # noqa: E501
        "with sudo",
    )


@step("I wait for the `{task}` command to complete")
def wait_for_task(context, task):
    while True:
        try:
            when_i_run_command(
                context, f"systemctl is-active {task}", "with sudo"
            )
            break
        except AssertionError:
            time.sleep(2)
