import datetime
import subprocess

from behave.runner import Context

from features.util import launch_lxd_container, lxc_exec


def before_all(context: Context) -> None:
    """behave will invoke this before anything else happens.

    In this function, we launch a container, install ubuntu-advantage-tools and
    then capture an image.  This image is then reused by each feature, reducing
    test execution time.
    """
    create_trusty_uat_lxd_image(context)


def _capture_container_as_image(container_name: str, image_name: str) -> None:
    """Capture a lxd container as an image.

    :param container_name:
        The name of the container to be captured.  Note that this container
        will be stopped.
    :param image_name:
        The name under which the image should be published.
    """
    subprocess.run(["lxc", "stop", container_name])
    subprocess.run(["lxc", "publish", container_name, "--alias", image_name])


def create_trusty_uat_lxd_image(context: Context) -> None:
    """Create a trusty lxd image with ubuntu-advantage-tools installed

    This will launch a container, install ubuntu-advantage-tools, and publish
    the image.  The image's name is stored in context.image_name for use within
    step code.

    :param context:
        A `behave.runner.Context`; this will have `image_name` set on it.
    """
    now = datetime.datetime.now()
    context.image_name = "behave-image-" + now.strftime("%s%f")
    build_container_name = "behave-image-build-" + now.strftime("%s%f")

    launch_lxd_container(context, "ubuntu:trusty", build_container_name)
    _install_uat_in_container(build_container_name)
    _capture_container_as_image(build_container_name, context.image_name)

    def image_cleanup() -> None:
        subprocess.run(["lxc", "image", "delete", context.image_name])

    context.add_cleanup(image_cleanup)


def _install_uat_in_container(container_name: str) -> None:
    """Install ubuntu-advantage-tools into the specified container

    :param container_name:
        The name of the container into which ubuntu-advantage-tools should be
        installed.
    """
    lxc_exec(
        container_name,
        [
            "add-apt-repository",
            "--yes",
            "ppa:canonical-server/ua-client-daily",
        ],
    )
    lxc_exec(container_name, ["apt-get", "update", "-qq"])
    lxc_exec(
        container_name,
        ["apt-get", "install", "-qq", "-y", "ubuntu-advantage-tools"],
    )
