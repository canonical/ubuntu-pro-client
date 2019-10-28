import subprocess
from typing import Any, List

from behave.runner import Context


def lxc_exec(
    context: Context, cmd: List[str], *args: Any, **kwargs: Any
) -> subprocess.CompletedProcess:
    """Run `lxc exec` in a container.

    :param context:
        A `behave.runner.Context`, which should have `container_name` set on
        it.
    :param cmd:
        A list containing the command to be run and its parameters; this will
        be appended to a list that is passed to `subprocess.run`.
    :param args, kwargs:
        These are passed directly to `subprocess.run`.

    :return:
        The `subprocess.CompletedProcess` returned by `subprocess.run`.
    """
    return subprocess.run(
        ["lxc", "exec", context.container_name, "--"] + cmd, *args, **kwargs
    )
