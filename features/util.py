import subprocess
import time
from typing import Any, List

from behave.runner import Context


def launch_lxd_container(
    context: Context, image_name: str, container_name: str
) -> None:
    """Launch a container from an image and wait for it to boot

    This will also register a cleanup with behave so the container will be
    removed before test execution completes.

    :param context:
        A `behave.runner.Context`; used only for registering cleanups.

    :param container_name:
        The name to be used for the launched container.
    """
    subprocess.run(["lxc", "launch", image_name, container_name])

    def cleanup_container() -> None:
        subprocess.run(["lxc", "delete", "-f", container_name])

    context.add_cleanup(cleanup_container)

    wait_for_boot(container_name)


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


def wait_for_boot(container_name: str) -> None:
    """Wait for a test container to boot.

    :param container_name:
        The name of the container to wait for.
    """
    retries = [2] * 5
    for sleep_time in retries:
        process = lxc_exec(
            container_name, ["runlevel"], capture_output=True, text=True
        )
        try:
            _, runlevel = process.stdout.strip().split(" ", 2)
        except ValueError:
            print("Unexpected runlevel output: ", process.stdout.strip())
            runlevel = None
        if runlevel == "2":
            break
        time.sleep(sleep_time)
    else:
        raise Exception("System did not boot in {}s".format(sum(retries)))
