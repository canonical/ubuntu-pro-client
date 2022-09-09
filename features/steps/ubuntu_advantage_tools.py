import logging
import re

from behave import when

from features.environment import UA_PPA_TEMPLATE, build_debs_from_sbuild
from features.steps.machines import launch_machine
from features.steps.shell import (
    when_i_run_command,
    when_i_run_command_on_machine,
    when_i_run_shell_command,
)
from features.util import InstallationSource


@when("I have the `{series}` debs under test in `{dest}`")
def when_i_have_the_debs_under_test(context, series, dest):
    if context.config.install_from is InstallationSource.LOCAL:
        deb_paths = build_debs_from_sbuild(context, series)

        for deb_path in deb_paths:
            tools_or_pro = "tools" if "tools" in deb_path else "pro"
            dest_path = "{}/ubuntu-advantage-{}.deb".format(dest, tools_or_pro)
            context.instances["uaclient"].push_file(deb_path, dest_path)
    else:
        if context.config.install_from is InstallationSource.PROPOSED:
            ppa_opts = ""
        else:
            if context.config.install_from is InstallationSource.DAILY:
                ppa = UA_PPA_TEMPLATE.format("daily")
            elif context.config.install_from is InstallationSource.STAGING:
                ppa = UA_PPA_TEMPLATE.format("staging")
            elif context.config.install_from is InstallationSource.STABLE:
                ppa = UA_PPA_TEMPLATE.format("stable")
            elif context.config.install_from is InstallationSource.CUSTOM:
                ppa = context.config.custom_ppa
                if not ppa.startswith("ppa"):
                    # assumes format "http://domain.name/user/ppa/ubuntu"
                    match = re.match(r"https?://[\w.]+/([^/]+/[^/]+)", ppa)
                    if not match:
                        raise AssertionError(
                            "ppa is in unsupported format: {}".format(ppa)
                        )
                    ppa = "ppa:{}".format(match.group(1))
            ppa_opts = "--distro ppa --ppa {}".format(ppa)
        download_cmd = "pull-lp-debs {} ubuntu-advantage-tools {}".format(
            ppa_opts, series
        )
        when_i_run_command(
            context, "apt-get install -y ubuntu-dev-tools", "with sudo"
        )
        when_i_run_command(context, download_cmd, "with sudo")
        logging.info("Download command `{}`".format(download_cmd))
        logging.info("stdout: {}".format(context.process.stdout))
        logging.info("stderr: {}".format(context.process.stderr))
        when_i_run_shell_command(
            context,
            "cp ubuntu-advantage-tools*.deb ubuntu-advantage-tools.deb",
            "with sudo",
        )
        when_i_run_shell_command(
            context,
            "cp ubuntu-advantage-pro*.deb ubuntu-advantage-pro.deb",
            "with sudo",
        )


@when(
    "I prepare the local PPAs to upgrade from `{release}` to `{next_release}`"
)
def when_i_create_local_ppas(context, release, next_release):
    if context.config.install_from is not InstallationSource.LOCAL:
        return

    # We need Kinetic or greater to support zstd when creating the PPAs
    launch_machine(context, "kinetic", "ppa")
    when_i_run_command_on_machine(
        context, "apt-get update", "with sudo", "ppa"
    )
    when_i_run_command_on_machine(
        context, "apt-get install -y aptly", "with sudo", "ppa"
    )
    create_local_ppa(context, release)
    create_local_ppa(context, next_release)
    repo_line = "deb [trusted=yes] http://{}:8080 {} main".format(
        context.instances["ppa"].ip, release
    )
    repo_file = "/etc/apt/sources.list.d/local-ua.list"
    when_i_run_shell_command(
        context, "printf '{}\n' > {}".format(repo_line, repo_file), "with sudo"
    )
    when_i_run_command_on_machine(
        context,
        "sh -c 'nohup aptly serve > /dev/null 2>&1 &'",
        "with sudo",
        "ppa",
    )


def create_local_ppa(context, release):
    when_i_run_command_on_machine(
        context,
        "aptly repo create -distribution {} repo-{}".format(release, release),
        "with sudo",
        "ppa",
    )
    debs = build_debs_from_sbuild(context, release)
    for deb in debs:
        deb_destination = "/tmp/" + deb.split("/")[-1]
        context.instances["ppa"].push_file(deb, deb_destination)
        when_i_run_command_on_machine(
            context,
            "aptly repo add repo-{} {}".format(release, deb_destination),
            "with sudo",
            "ppa",
        )
    when_i_run_command_on_machine(
        context,
        "aptly publish repo -skip-signing repo-{}".format(release),
        "with sudo",
        "ppa",
    )
