import shlex

from features.steps.shell import when_i_run_command

LXC_COMMAND_TIMEOUT = "10m"
LXC_DIAGNOSTIC_TIMEOUT = "30s"
LXC_COMMAND_LOG_PATH = "/tmp/behave-lxc-command.log"
LXC_COMMAND_LOG_TAIL_BYTES = 8192


def run_lxc_guest_command(context, guest_name, command):
    """Run a command on the LXC guest and emit its output only on failure.

    A failed or timed-out command emits the final portion of that log for
    the Behave failure report.
    """
    guest_command = "{} >{} 2>&1".format(command, LXC_COMMAND_LOG_PATH)
    lxc_exec = ("lxc exec {guest_name} -- sh -c {guest_command}").format(
        guest_name=shlex.quote(guest_name),
        guest_command=shlex.quote(guest_command),
    )
    diagnostic_command = (
        "timeout {timeout} lxc exec {guest_name} -- tail -c {tail_bytes} "
        "{log_path} >&2 || true"
    ).format(
        timeout=LXC_DIAGNOSTIC_TIMEOUT,
        guest_name=shlex.quote(guest_name),
        tail_bytes=LXC_COMMAND_LOG_TAIL_BYTES,
        log_path=shlex.quote(LXC_COMMAND_LOG_PATH),
    )
    command = (
        "timeout {timeout} {lxc_exec}; exit_code=$?; "
        "if [ $exit_code -ne 0 ]; then "
        'echo "LXC guest command failed with exit code $exit_code" >&2; '
        "{diagnostic_command}; fi; exit $exit_code"
    ).format(
        timeout=LXC_COMMAND_TIMEOUT,
        lxc_exec=lxc_exec,
        diagnostic_command=diagnostic_command,
    )
    when_i_run_command(
        context,
        "sh -c {}".format(shlex.quote(command)),
        "with sudo",
    )
