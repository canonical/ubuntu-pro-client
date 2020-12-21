from contextlib import contextmanager
import os
import multiprocessing
import subprocess
import tempfile
import textwrap
import time
import yaml
from typing import List

import pycloudlib  # type: ignore


LXC_PROPERTY_MAP = {
    "image": {"series": "properties.release", "machine_type": "Type"},
    "container": {"series": "image.release", "machine_type": "image.type"},
}
SLOW_CMDS = ["do-release-upgrade"]  # Commands which will emit dots on travis
SOURCE_PR_TGZ = os.path.join(tempfile.gettempdir(), "pr_source.tar.gz")
UA_DEBS = frozenset({"ubuntu-advantage-tools.deb", "ubuntu-advantage-pro.deb"})
VM_PROFILE_TMPL = "behave-{}"


# For Xenial and Bionic vendor-data required to setup lxd-agent
# Additionally xenial needs to launch images:ubuntu/16.04/cloud
# because it contains the HWE kernel which has vhost-vsock support
LXC_SETUP_VENDORDATA = textwrap.dedent(
    """\
    config:
      user.vendor-data: |
        #cloud-config
        {custom_cfg}
        write_files:
        - path: /var/lib/cloud/scripts/per-once/setup-lxc.sh
          encoding: b64
          permissions: '0755'
          owner: root:root
          content: |
              IyEvYmluL3NoCmlmICEgZ3JlcCBseGRfY29uZmlnIC9wcm9jL21vdW50czsgdGhlbgogICAgbWtk
              aXIgLXAgL3J1bi9seGRhZ2VudAogICAgbW91bnQgLXQgOXAgY29uZmlnIC9ydW4vbHhkYWdlbnQK
              ICAgIFZJUlQ9JChzeXN0ZW1kLWRldGVjdC12aXJ0KQogICAgY2FzZSAkVklSVCBpbgogICAgICAg
              IHFlbXV8a3ZtKQogICAgICAgICAgICAoY2QgL3J1bi9seGRhZ2VudC8gJiYgLi9pbnN0YWxsLnNo
              KQogICAgICAgICAgICB1bW91bnQgL3J1bi9seGRhZ2VudAogICAgICAgICAgICBzeXN0ZW1jdGwg
              c3RhcnQgbHhkLWFnZW50LTlwIGx4ZC1hZ2VudAogICAgICAgICAgICA7OwogICAgICAgICopCiAg
              ICBlc2FjCmZpCg==
   """
)


BUILD_FROM_TGZ = textwrap.dedent(
    """\
   #!/bin/bash
   set -o xtrace
   apt-get update
   apt-get install make
   cd /tmp
   tar -zxf *gz
   cd *ubuntu-advantage-client*
   make deps
   dpkg-buildpackage -us -uc
   # Copy and rename versioned debs to /tmp/ubuntu-advantage-(tools|pro).deb
   cp /tmp/ubuntu-advantage-tools*.deb /tmp/ubuntu-advantage-tools.deb
   cp /tmp/ubuntu-advantage-pro*.deb /tmp/ubuntu-advantage-pro.deb
   """
)


def lxc_create_vm_profile(series: str):
    """Create a vm profile to enable launching kvm instances"""

    content_tmpl = textwrap.dedent(
        """\
        {vendordata}
        description: Default LXD profile for {series} VMs
        devices:
          config:
            source: cloud-init:config
            type: disk
          eth0:
            name: eth0
            network: lxdbr0
            type: nic
          root:
            path: /
            pool: default
            type: disk
        name: vm
    """
    )
    if series == "xenial":
        # FIXME: Xenial images from images:ubuntu/16.04/cloud have HWE kernel
        # but no openssh-server (which fips testing would expect)
        # Work with CPC to get vhost-vsock support if possible to use
        # ubuntu-daily:xenial images
        content = content_tmpl.format(
            vendordata=LXC_SETUP_VENDORDATA.format(
                custom_cfg="packages: [openssh-server]"
            ),
            series=series,
        )
    elif series == "bionic":
        content = content_tmpl.format(
            vendordata=LXC_SETUP_VENDORDATA.format(custom_cfg=""),
            series=series,
        )
    elif series == "focal":
        content = content_tmpl.format(vendordata="config: {}", series=series)
    else:
        raise RuntimeError(
            "===No lxc mv support for series {}====".format(series)
        )
    output = subprocess.check_output(["lxc", "profile", "list"])
    profile_name = VM_PROFILE_TMPL.format(series)
    if " {} ".format(profile_name) not in output.decode("utf-8"):
        subprocess.run(["lxc", "profile", "create", profile_name])
        proc = subprocess.Popen(
            ["lxc", "profile", "edit", profile_name], stdin=subprocess.PIPE
        )
        proc.communicate(content.encode())


def lxc_get_property(name: str, property_name: str, image: bool = False):
    """Check series name of either an image or a container.

    :param name:
        The name of the container or the image to check its series.
    :param property_name:
        The name of the property to return.
    :param image:
        If image==True will check image properties
        If image==False it will check container configuration to get
        properties.

    :return:
        The value of the container or image property.
       `None` if it could not detect it (
           some images don't have this field in properties).
    """
    if not image:
        property_name = LXC_PROPERTY_MAP["container"][property_name]
        output = subprocess.check_output(
            ["lxc", "config", "get", name, property_name],
            universal_newlines=True,
        )
        return output.rstrip()
    else:
        property_keys = LXC_PROPERTY_MAP["image"][property_name].split(".")
        output = subprocess.check_output(
            ["lxc", "image", "show", name], universal_newlines=True
        )
        image_config = yaml.safe_load(output)
        print("--- `lxc image show` output: ", image_config)
        value = image_config
        for key_name in property_keys:
            value = image_config.get(value, {})
        if not value:
            print(
                "--- Could not detect image property {name}."
                " Add it via `lxc image edit`".format(
                    name=".".join(property_keys)
                )
            )
            return None
        return value


def build_debs(
    container_name: str,
    output_deb_dir: str,
    cloud_api: "pycloudlib.cloud.BaseCloud",
) -> "List[str]":
    """
    Push source PR code .tar.gz to the container.
    Run tools/build-from-source.sh which will create the .deb
    Copy built debs from the build container back to the source environment
    Stop the container.

    :param container_name: the name of the container to:
         - push the PR source code;
         - pull the built .deb package.
    :param output_deb_dir: the target directory in which to copy deb artifacts
    :param cloud_api: Optional pycloudlib BaseCloud api if available for the
        machine_type

    :return: A list of file paths to debs created by the build.

    """
    if os.environ.get("TRAVIS") != "true":
        print(
            "--- Assuming non-travis build. Creating: {}".format(SOURCE_PR_TGZ)
        )
        if not os.path.exists(os.path.dirname(SOURCE_PR_TGZ)):
            os.makedirs(os.path.dirname(SOURCE_PR_TGZ))
        if not os.path.exists(SOURCE_PR_TGZ):
            cwd = os.getcwd()
            os.chdir("..")
            subprocess.run(
                [
                    "tar",
                    "-zcf",
                    SOURCE_PR_TGZ,
                    "--exclude-vcs",
                    "--exclude-vcs-ignores",
                    os.path.basename(cwd),
                ]
            )
            os.chdir(cwd)
    buildscript = "build-from-source.sh"
    with open(buildscript, "w") as stream:
        stream.write(BUILD_FROM_TGZ)

    instance = cloud_api.get_instance(instance_id=container_name)
    for filepath in (buildscript, SOURCE_PR_TGZ):
        print("--- Push {} -> {}:/tmp".format(filepath, instance.name))
        instance.push_file(filepath, "/tmp/" + os.path.basename(filepath))
    instance.execute(["sudo", "bash", "/tmp/" + buildscript])
    deb_artifacts = []
    if not os.path.exists(output_deb_dir):
        os.makedirs(output_deb_dir)
    for deb in UA_DEBS:
        deb_artifacts.append(os.path.join(output_deb_dir, deb))
        print(
            "--- Pull {}:/tmp/{} {}".format(instance.name, deb, output_deb_dir)
        )
        instance.pull_file("/tmp/" + deb, os.path.join(output_deb_dir, deb))
    instance.delete(wait=False)
    return deb_artifacts


# Support for python 3.6 or earlier
@contextmanager
def nullcontext(enter_result=None):
    yield enter_result


def spinning_cursor():
    while True:
        for cursor in "|/-\\":
            yield cursor


@contextmanager
def emit_spinner_on_travis(msg: str = " "):
    """
    A context manager that emits a spinner updating 5 seconds if running on
    Travis.

    Travis will kill jobs that don't emit output for a certain amount of time.
    This context manager spins up a background process which will emit a char
    to stdout every 10 seconds to avoid being killed.

    It should be wrapped selectively around operations that are known to take a
    long time
    """
    if os.environ.get("TRAVIS") != "true":
        # If we aren't on Travis, don't do anything.
        yield
        return

    def emit_spinner():
        print(msg, end="", flush=True)
        spinner = spinning_cursor()
        while True:
            time.sleep(5)
            print("\b%s" % next(spinner), end="", flush=True)

    dot_process = multiprocessing.Process(target=emit_spinner)
    dot_process.start()
    try:
        yield
    finally:
        print()
        dot_process.terminate()
