import logging
import os
import re

from behave import then, when

from features.steps.files import when_i_create_file_with_content
from features.steps.packages import when_i_apt_install
from features.steps.shell import when_i_run_command, when_i_run_shell_command
from features.util import SUT, InstallationSource, build_debs


@when("I install ubuntu-advantage-tools")
def when_i_install_uat(context, machine_name=SUT):
    instance = context.machines[machine_name].instance
    series = context.machines[machine_name].series
    is_pro = "pro" in context.pro_config.machine_type
    if context.pro_config.install_from is InstallationSource.ARCHIVE:
        instance.execute("sudo apt update")
        when_i_apt_install(
            context, "ubuntu-advantage-tools", machine_name=machine_name
        )
        if is_pro:
            when_i_apt_install(
                context, "ubuntu-advantage-pro", machine_name=machine_name
            )
    elif context.pro_config.install_from is InstallationSource.PREBUILT:
        debs_path = context.pro_config.debs_path
        deb_paths = [
            os.path.join(debs_path, deb_file)
            for deb_file in os.listdir(debs_path)
            if series in deb_file
        ]
        logging.info("using debs: {}".format(deb_paths))
        for deb_path in deb_paths:
            if "pro" not in deb_path or is_pro:
                instance.push_file(deb_path, "/tmp/behave_ua.deb")
                when_i_apt_install(
                    context, "/tmp/behave_ua.deb", machine_name=machine_name
                )
                instance.execute("sudo rm /tmp/behave_ua.deb")
    elif context.pro_config.install_from is InstallationSource.LOCAL:
        ua_deb_path, pro_deb_path = build_debs(series)
        instance.push_file(ua_deb_path, "/tmp/behave_ua.deb")
        when_i_apt_install(
            context, "/tmp/behave_ua.deb", machine_name=machine_name
        )
        instance.execute("sudo rm /tmp/behave_ua.deb")
        if is_pro:
            instance.push_file(pro_deb_path, "/tmp/behave_ua.deb")
            when_i_apt_install(
                context, "/tmp/behave_ua.deb", machine_name=machine_name
            )
            instance.execute("sudo rm /tmp/behave_ua.deb")
    elif context.pro_config.install_from is InstallationSource.DAILY:
        instance.execute("sudo add-apt-repository ppa:ua-client/daily")
        instance.execute("sudo apt update")
        when_i_apt_install(
            context, "ubuntu-advantage-tools", machine_name=machine_name
        )
        if is_pro:
            when_i_apt_install(
                context, "ubuntu-advantage-pro", machine_name=machine_name
            )
    elif context.pro_config.install_from is InstallationSource.STAGING:
        instance.execute("sudo add-apt-repository ppa:ua-client/staging")
        instance.execute("sudo apt update")
        when_i_apt_install(
            context, "ubuntu-advantage-tools", machine_name=machine_name
        )
        if is_pro:
            when_i_apt_install(
                context, "ubuntu-advantage-pro", machine_name=machine_name
            )
    elif context.pro_config.install_from is InstallationSource.STABLE:
        instance.execute("sudo add-apt-repository ppa:ua-client/stable")
        instance.execute("sudo apt update")
        when_i_apt_install(
            context, "ubuntu-advantage-tools", machine_name=machine_name
        )
        if is_pro:
            when_i_apt_install(
                context, "ubuntu-advantage-pro", machine_name=machine_name
            )
    elif context.pro_config.install_from is InstallationSource.PROPOSED:
        context.text = "deb http://archive.ubuntu.com/ubuntu/ {series}-proposed main\n".format(  # noqa: E501
            series=series
        )
        when_i_create_file_with_content(
            context,
            "/etc/apt/sources.list.d/uaclient-proposed.list",
            machine_name=machine_name,
        )

        context.text = "Package: *\nPin: release a={series}-proposed\nPin-Priority: 400\n".format(  # noqa: E501
            series=series
        )
        when_i_create_file_with_content(
            context,
            "/etc/apt/preferences.d/lower-proposed",
            machine_name=machine_name,
        )

        context.text = "Package: ubuntu-advantage-tools\nPin: release a={series}-proposed\nPin-Priority: 1001\n".format(  # noqa: E501
            series=series
        )
        when_i_create_file_with_content(
            context,
            "/etc/apt/preferences.d/uatools-proposed",
            machine_name=machine_name,
        )

        context.text = "Package: ubuntu-advantage-pro\nPin: release a={series}-proposed\nPin-Priority: 1001\n".format(  # noqa: E501
            series=series
        )
        when_i_create_file_with_content(
            context,
            "/etc/apt/preferences.d/uapro-proposed",
            machine_name=machine_name,
        )

        instance.execute("sudo apt update")
        when_i_apt_install(
            context, "ubuntu-advantage-tools", machine_name=machine_name
        )
        if is_pro:
            when_i_apt_install(
                context, "ubuntu-advantage-pro", machine_name=machine_name
            )
    elif context.pro_config.install_from is InstallationSource.CUSTOM:
        instance.execute(
            "sudo add-apt-repository {}".format(context.pro_config.custom_ppa)
        )
        instance.execute("sudo apt update")
        when_i_apt_install(
            context, "ubuntu-advantage-tools", machine_name=machine_name
        )
        if is_pro:
            when_i_apt_install(
                context, "ubuntu-advantage-pro", machine_name=machine_name
            )


@when("I have the `{series}` debs under test in `{dest}`")
def when_i_have_the_debs_under_test(context, series, dest):
    if context.pro_config.install_from is InstallationSource.LOCAL:
        deb_paths = build_debs(series)

        for deb_path in deb_paths:
            tools_or_pro = "tools" if "tools" in deb_path else "pro"
            dest_path = "{}/ubuntu-advantage-{}.deb".format(dest, tools_or_pro)
            context.machines[SUT].instance.push_file(deb_path, dest_path)
    else:
        if context.pro_config.install_from is InstallationSource.PROPOSED:
            ppa_opts = ""
        else:
            if context.pro_config.install_from is InstallationSource.DAILY:
                ppa = "ppa:ua-client/daily"
            elif context.pro_config.install_from is InstallationSource.STAGING:
                ppa = "ppa:ua-client/staging"
            elif context.pro_config.install_from is InstallationSource.STABLE:
                ppa = "ppa:ua-client/stable"
            elif context.pro_config.install_from is InstallationSource.CUSTOM:
                ppa = context.pro_config.custom_ppa
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
    if context.pro_config.install_from is not InstallationSource.LOCAL:
        return

    from features.steps.machines import given_a_machine

    # We need Kinetic or greater to support zstd when creating the PPAs
    given_a_machine(context, "kinetic", "ppa")
    when_i_run_command(
        context, "apt-get update", "with sudo", machine_name="ppa"
    )
    when_i_run_command(
        context, "apt-get install -y aptly", "with sudo", machine_name="ppa"
    )
    create_local_ppa(context, release)
    create_local_ppa(context, next_release)
    repo_line = "deb [trusted=yes] http://{}:8080 {} main".format(
        context.machines["ppa"].instance.ip, release
    )
    repo_file = "/etc/apt/sources.list.d/local-ua.list"
    when_i_run_shell_command(
        context, "printf '{}\n' > {}".format(repo_line, repo_file), "with sudo"
    )
    when_i_run_command(
        context,
        "sh -c 'nohup aptly serve > /dev/null 2>&1 &'",
        "with sudo",
        machine_name="ppa",
    )


def create_local_ppa(context, release):
    when_i_run_command(
        context,
        "aptly repo create -distribution {} repo-{}".format(release, release),
        "with sudo",
        machine_name="ppa",
    )
    debs = build_debs(release)
    for deb in debs:
        deb_destination = "/tmp/" + deb.split("/")[-1]
        context.machines["ppa"].instance.push_file(deb, deb_destination)
        when_i_run_command(
            context,
            "aptly repo add repo-{} {}".format(release, deb_destination),
            "with sudo",
            machine_name="ppa",
        )
    when_i_run_command(
        context,
        "aptly publish repo -skip-signing repo-{}".format(release),
        "with sudo",
        machine_name="ppa",
    )


@when("I install ubuntu-advantage-pro")
def when_i_install_pro(context):
    if context.pro_config.install_from is InstallationSource.LOCAL:
        deb_paths = build_debs(context.machines[SUT].instance.series)

        for deb_path in deb_paths:
            if "pro" in deb_path:
                context.instances["uaclient"].push_file(
                    deb_path, "/tmp/pro.deb"
                )
                when_i_run_command(
                    context, "dpkg -i /tmp/pro.deb", "with sudo"
                )
    else:
        when_i_run_command(
            context, "apt-get install ubuntu-advantage-pro", "with sudo"
        )


APT_POLICY_IS = "the apt-cache policy of ubuntu-advantage-tools is"


@then(APT_POLICY_IS)
def then_i_apt_cache_policy_is(context):
    pass


@when("I check the apt-cache policy of ubuntu-advantage-tools")
def when_i_check_apt_cache_policy(context):
    when_i_run_command(context, "apt-get update", "with sudo")
    when_i_run_command(
        context, "apt-cache policy ubuntu-advantage-tools", "with sudo"
    )
    for step in context.scenario.steps:
        if step.name == APT_POLICY_IS:
            step.text = context.process.stdout
