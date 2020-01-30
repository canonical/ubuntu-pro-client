import subprocess
import sys
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
    container_name: str,
    cmd: List[str],
    capture_output: bool = False,
    text: bool = False,
    **kwargs: Any
) -> subprocess.CompletedProcess:
    """Run `lxc exec` in a container.

    :param container_name:
        The name of the container to run `lxc exec` against.
    :param cmd:
        A list containing the command to be run and its parameters; this will
        be appended to a list that is passed to `subprocess.run`.
    :param capture_output:
        If capture_output is true, stdout and stderr will be captured.  (On
        pre-3.7 Pythons, this will behave as capture_output does for 3.7+.  On
        3.7+, this is just passed through.)
    :param text:
        If text (also known as universal_newlines) is true, the file objects
        stdin, stdout and stderr will be opened in text mode. (On pre-3.7
        Pythons, this will behave as universal_newlines does).
    :param kwargs:
        These are passed directly to `subprocess.run`.

    :return:
        The `subprocess.CompletedProcess` returned by `subprocess.run`.
    """
    if sys.version_info >= (3, 7):
        # We have native capture_output support
        kwargs["capture_output"] = capture_output
        kwargs["text"] = text
    elif capture_output:
        if (
            kwargs.get("stdout") is not None
            or kwargs.get("stderr") is not None
        ):
            raise ValueError(
                "stdout and stderr arguments may not be used "
                "with capture_output."
            )
        # stdout and stderr will be opened in text mode (by default they are
        # opened in binary mode
        kwargs["universal_newlines"] = text
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(
        ["lxc", "exec", "--user", "1000", container_name, "--"] + cmd, **kwargs
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
