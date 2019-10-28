import subprocess
from typing import Any, List


def lxc_exec(
    container_name: str, cmd: List[str], *args: Any, **kwargs: Any
) -> subprocess.CompletedProcess:
    """Run `lxc exec` in a container.

    :param container_name:
        The name of the container to run `lxc exec` against.
    :param cmd:
        A list containing the command to be run and its parameters; this will
        be appended to a list that is passed to `subprocess.run`.
    :param args, kwargs:
        These are passed directly to `subprocess.run`.

    :return:
        The `subprocess.CompletedProcess` returned by `subprocess.run`.
    """
    return subprocess.run(
        ["lxc", "exec", container_name, "--"] + cmd, *args, **kwargs
    )
