import json
import logging
import re
import shlex
from typing import List  # noqa: F401

from behave import then

from features.steps.files import when_i_create_file_with_content
from features.steps.shell import when_i_run_command, when_i_run_shell_command


@then(
    "the following files are {presence} in any layer of docker image "
    "`{image_name}`"
)
def files_in_docker_image_layers(context, presence, image_name):
    if presence not in ("present", "not present"):
        raise AssertionError(
            "unsupported expected file presence: {}".format(presence)
        )
    want_found = presence == "present"

    file_names = [row["file_name"] for row in context.table]
    when_i_run_command(
        context,
        "mktemp -d /tmp/docker-image-layers.XXXXXX",
        "with sudo",
    )
    temp_dir = context.process.stdout.strip()
    archive_path = "{}/image.tar".format(temp_dir)
    layer_archive_path = "{}/layer.tar".format(temp_dir)
    layer_files_path = "{}/layer-files".format(temp_dir)

    try:
        when_i_run_command(
            context,
            "docker image save --output {} {}".format(
                shlex.quote(archive_path), shlex.quote(image_name)
            ),
            "with sudo",
        )
        when_i_run_command(
            context,
            "tar -xOf {} manifest.json".format(shlex.quote(archive_path)),
            "with sudo",
        )
        manifest = json.loads(context.process.stdout)
        layers = sorted(
            {layer for image in manifest for layer in image.get("Layers", [])}
        )
        if not layers:
            raise AssertionError(
                'docker image "{}" has no layers'.format(image_name)
            )

        pattern = r"(^|/)({})$".format(
            "|".join(re.escape(file_name) for file_name in file_names)
        )
        found = []  # type: List[str]
        for layer in layers:
            scan = (
                "tar -xOf {archive} {layer} > {layer_archive} && "
                "if gzip -t {layer_archive} 2>/dev/null; then "
                "gzip -dc {layer_archive} | tar -tf - > {files} || exit 2; "
                "else tar -tf {layer_archive} > {files} || exit 2; fi; "
                "grep -E -- {pattern} {files}"
            ).format(
                archive=shlex.quote(archive_path),
                layer=shlex.quote(layer),
                layer_archive=shlex.quote(layer_archive_path),
                files=shlex.quote(layer_files_path),
                pattern=shlex.quote(pattern),
            )
            when_i_run_command(
                context,
                "bash -o pipefail -c {}".format(shlex.quote(scan)),
                "with sudo",
                verify_return=False,
            )
            if context.process.returncode == 0:
                found.extend(
                    "{}: {}".format(layer, path)
                    for path in context.process.stdout.splitlines()
                )
            elif context.process.returncode != 1:
                raise AssertionError(
                    (
                        'could not inspect layer "{}" of docker image '
                        '"{}": {}'
                    ).format(layer, image_name, context.process.stderr.strip())
                )

        if found and not want_found:
            raise AssertionError(
                'unexpected files in docker image "{}": {}'.format(
                    image_name, ", ".join(found)
                )
            )
        if not found and want_found:
            raise AssertionError(
                (
                    'expected files in docker image "{}" ' "were not found: {}"
                ).format(image_name, ", ".join(file_names))
            )
    finally:
        when_i_run_command(
            context,
            "rm -rf {}".format(shlex.quote(temp_dir)),
            "with sudo",
            verify_return=False,
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
