import os
import subprocess
import sys
import textwrap
import time
import yaml
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
        if not context.config.destroy_instances:
            print("Leaving lxd container running: {}".format(container_name))
        else:
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
    retries = [10] * 5
    for sleep_time in retries:
        process = lxc_exec(
            container_name, ["runlevel"], capture_output=True, text=True
        )
        try:
            _, runlevel = process.stdout.strip().split(" ", 2)
        except ValueError:
            print("Unexpected runlevel output: ", process.stdout.strip())
            runlevel = None
        if runlevel in ("2", "5"):
            break
        time.sleep(sleep_time)
    else:
        raise Exception("System did not boot in {}s".format(sum(retries)))


def lxc_get_series(name: str, image: bool = False):
    """Check series name of either an image or a container.

    :param name:
        The name of the container or the image to check its series.
    :param image:
        If image==True will check image series
        If image==False it will check container configuration to get series.

    :return:
        The series of the container or the image.
       `None` if it could not detect it (
           some images don't have this field in properties).
    """

    if not image:
        output = subprocess.check_output(
            ["lxc", "config", "get", name, "image.release"],
            universal_newlines=True,
        )
        series = output.rstrip()
        return series
    else:
        image_output = "image_output.yaml"
        with open(image_output, "w") as fileoutput:
            subprocess.run(["lxc", "image", "show", name], stdout=fileoutput)
        output = subprocess.check_output(
            ["lxc", "image", "show", name], universal_newlines=True
        )
        image_config = yaml.safe_load(output)
        print(" `lxc image show` output: ", image_config)
        fileoutput.close()
        os.remove(image_output)
        try:
            series = image_config["properties"]["release"]
            print(
                textwrap.dedent(
                    """
                You are providing a {series} image.
                Make sure you are running this series tests.
                For instance: --tags=series.{series}""".format(
                        series=series
                    )
                )
            )
            return series
        except KeyError:
            print(
                " Could not detect image series. Add it via `lxc image edit`"
            )
    return None


def lxc_build_deb(
    container_name: str,
    output_deb_file: str = "/tmp/ubuntu-advantage.deb"
) -> None:
    """
    Push source PR code .tar.gz to the container.
    Run tools/build-from-source.sh which will create the .deb
    Pull .deb from this container to travis-ci instance

    :param container_name: the name of the container to:
         - push the PR source code;
         - pull the built .deb package.
    :param output_deb_file: the new output .deb from source code
    """

    print ('\n\n\n LXC file push pr_source.tar.gz')
    subprocess.run(["lxc", "file", "push", "/tmp/pr_source.tar.gz", container_name+'/tmp/'])
    script = "build-from-source.sh"
    with open(script, 'w') as stream:
        stream.write(textwrap.dedent("""\
            #!/bin/bash
            set -o xtrace
            apt-get update
            apt-get install make
            cd /tmp
            tar -zxvf *gz
            cd ubuntu-advantage-client
            make deps
            dpkg-buildpackage -us -uc
         """))
    os.chmod(script, 0o755)
    subprocess.run(["ls", "-lh", "/tmp"])
    print ('\n\n\n LXC file push script build-from-source')
    subprocess.run(["lxc", "file", "push", script, container_name+'/tmp/'])
    print ('\n\n\n Run build-from-source.sh')

    subprocess.run(
        [
            "lxc",
            "exec",
            container_name,
            "--",
            "/tmp/"+script
        ],
    )
    print ("\n\nPull .deb from the instance to travis VM")
    subprocess.run(["lxc", "exec", container_name, "--", "ls", "-lh" , "/tmp"])
    subprocess.run(["lxc", "file", "pull", container_name+'/tmp/ubuntu-advantage-tools_20.4_amd64.deb', output_deb_file])
