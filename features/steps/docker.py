import logging

from behave import then

from features.steps.files import when_i_create_file_with_content
from features.steps.shell import when_i_run_command, when_i_run_shell_command


@then("`{file_name}` is not present in any docker image layer")
def file_is_not_present_in_any_docker_image_layer(context, file_name):
    when_i_run_command(
        context,
        "find /var/lib/docker/overlay2 -name {}".format(file_name),
        "with sudo",
    )
    results = context.process.stdout.strip()
    if results:
        raise AssertionError(
            'found "{}"'.format(", ".join(results.split("\n")))
        )


# This defines "not significantly larger" as "less than 2MB larger"
@then(
    "docker image `{name}` is not significantly larger than `ubuntu:{series}` with `{package}` installed"  # noqa: E501
)
def docker_image_is_not_larger(context, name, series, package):
    base_image_name = "ubuntu:{}".format(series)
    base_upgraded_image_name = "{}-with-test-package".format(series)

    # We need to compare against the base image after apt upgrade
    # and package install
    dockerfile = """\
    FROM {}
    RUN apt-get update \\
      && apt-get install -y {} \\
      && rm -rf /var/lib/apt/lists/*
    """.format(
        base_image_name, package
    )
    context.text = dockerfile
    when_i_create_file_with_content(context, "Dockerfile.base")
    when_i_run_command(
        context,
        "docker build . -f Dockerfile.base -t {}".format(
            base_upgraded_image_name
        ),
        "with sudo",
    )

    # find image sizes
    when_i_run_shell_command(
        context, "docker inspect {} | jq .[0].Size".format(name), "with sudo"
    )
    custom_image_size = int(context.process.stdout.strip())
    when_i_run_shell_command(
        context,
        "docker inspect {} | jq .[0].Size".format(base_upgraded_image_name),
        "with sudo",
    )
    base_image_size = int(context.process.stdout.strip())

    # Get pro test deb size
    when_i_run_command(context, "du ubuntu-advantage-tools.deb", "with sudo")
    # Example out: "1234\tubuntu-advantage-tools.deb"
    ua_test_deb_size = (
        int(context.process.stdout.strip().split("\t")[0]) * 1024
    )  # KB -> B

    # Give us some space for bloat we don't control: 2MB -> B
    extra_space = 2 * 1024 * 1024

    if custom_image_size > (base_image_size + ua_test_deb_size + extra_space):
        raise AssertionError(
            "Custom image size ({}) is over 2MB greater than the base image"
            " size ({}) + pro test deb size ({})".format(
                custom_image_size, base_image_size, ua_test_deb_size
            )
        )
    logging.debug(
        "custom image size ({})\n"
        "base image size ({})\n"
        "pro test deb size ({})".format(
            custom_image_size, base_image_size, ua_test_deb_size
        )
    )
