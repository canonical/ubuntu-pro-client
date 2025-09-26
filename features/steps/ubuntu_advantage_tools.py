import logging
import re

from behave import then, when

from features.steps.files import when_i_create_file_with_content
from features.steps.packages import when_i_apt_install, when_i_apt_update
from features.steps.shell import when_i_run_command, when_i_run_shell_command
from features.util import (
    ALL_BINARY_PACKAGE_NAMES,
    NORMAL_BINARY_PACKAGE_NAMES,
    SUT,
    InstallationSource,
    build_debs,
    get_debs_for_series,
)

SETUP_PRO_PACKAGE_SOURCES_SCRIPTS = {
    InstallationSource.ARCHIVE: "sudo apt update",
    InstallationSource.DAILY: """\
sudo add-apt-repository ppa:ua-client/daily
sudo apt update""",
    InstallationSource.STAGING: """\
sudo add-apt-repository ppa:ua-client/staging
sudo apt update""",
    InstallationSource.STABLE: """\
sudo add-apt-repository ppa:ua-client/stable
sudo apt update""",
    InstallationSource.PROPOSED: """\
cat > /etc/apt/sources.list.d/proposed.list << EOF
deb http://archive.ubuntu.com/ubuntu/ {series}-proposed main
EOF
cat > /etc/apt/preferences.d/lower-proposed << EOF
Package: *
Pin: release a=*-proposed
Pin-Priority: 400
EOF
cat > /etc/apt/preferences.d/upper-pro-posed << EOF
Package: {packages}
Pin: release a=*-proposed
Pin-Priority: 1001
EOF
sudo apt update""",
    InstallationSource.CUSTOM: """\
sudo add-apt-repository {ppa}
sudo apt update""",
}


def get_setup_pro_package_sources_script(context, series):
    script = SETUP_PRO_PACKAGE_SOURCES_SCRIPTS.get(
        context.pro_config.install_from, ""
    )
    script = script.format(
        ppa=context.pro_config.custom_ppa,
        series=series,
        packages=" ".join(ALL_BINARY_PACKAGE_NAMES),
    )
    return script


def setup_pro_package_sources(context, machine_name=SUT):
    instance = context.machines[machine_name].instance
    series = context.machines[machine_name].series
    script = get_setup_pro_package_sources_script(context, series)
    context.text = script
    when_i_create_file_with_content(
        context,
        "/tmp/setup_pro.sh",
        machine_name=machine_name,
    )
    instance.execute("sudo bash /tmp/setup_pro.sh")


@when("I install ubuntu-advantage-tools")
def when_i_install_uat(context, machine_name=SUT):
    instance = context.machines[machine_name].instance
    series = context.machines[machine_name].series
    is_pro = "pro" in context.machines[machine_name].machine_type
    setup_pro_package_sources(context, machine_name)

    if context.pro_config.install_from is InstallationSource.PREBUILT:
        debs = get_debs_for_series(context.pro_config.debs_path, series)
        logging.info("using debs: {}".format(debs))
        to_install = []
        for deb_name, deb_path in debs.non_cloud_pro_image_debs(series):
            instance_tmp_path = "/tmp/behave_{}.deb".format(deb_name)
            instance.push_file(deb_path, instance_tmp_path)
            to_install.append(instance_tmp_path)
        if is_pro:
            for deb_name, deb_path in debs.cloud_pro_image_debs():
                instance_tmp_path = "/tmp/behave_{}.deb".format(deb_name)
                instance.push_file(deb_path, instance_tmp_path)
                to_install.append(instance_tmp_path)
        when_i_apt_install(
            context, " ".join(to_install), machine_name=machine_name
        )
    elif context.pro_config.install_from is InstallationSource.LOCAL:
        debs = build_debs(
            series,
            sbuild_output_to_terminal=context.pro_config.sbuild_output_to_terminal,  # noqa: E501
        )
        to_install = []
        for deb_name, deb_path in debs.non_cloud_pro_image_debs(series):
            instance_tmp_path = "/tmp/behave_{}.deb".format(deb_name)
            instance.push_file(deb_path, instance_tmp_path)
            to_install.append(instance_tmp_path)
        if is_pro:
            for deb_name, deb_path in debs.cloud_pro_image_debs():
                instance_tmp_path = "/tmp/behave_{}.deb".format(deb_name)
                instance.push_file(deb_path, instance_tmp_path)
                to_install.append(instance_tmp_path)
        when_i_apt_install(
            context, " ".join(to_install), machine_name=machine_name
        )
    else:
        if series in ("xenial", "bionic", "focal", "jammy"):
            when_i_apt_install(
                context,
                "ubuntu-pro-client ubuntu-advantage-tools",
                machine_name=machine_name,
            )
        else:
            when_i_apt_install(
                context,
                "ubuntu-pro-client",
                machine_name=machine_name,
            )

        if is_pro:
            when_i_apt_install(
                context,
                "ubuntu-pro-auto-attach",
                machine_name=machine_name,
            )


@when("I install ubuntu-advantage-tools on the `{guest_name}` lxd guest")
def when_i_install_uat_on_lxd_guest(context, guest_name):
    # This function assumes "when_i_install_uat" was run on the SUT
    if context.pro_config.install_from in {
        InstallationSource.PREBUILT,
        InstallationSource.LOCAL,
    }:
        to_install = []
        for deb_name in NORMAL_BINARY_PACKAGE_NAMES:
            deb_file_name = "behave_{}.deb".format(deb_name)
            instance_tmp_path = "/tmp/{}".format(deb_file_name)
            guest_path = "/root/{}".format(deb_file_name)
            when_i_run_command(
                context,
                "lxc file push {tmp_path} {guest_name}{guest_path}".format(
                    tmp_path=instance_tmp_path,
                    guest_name=guest_name,
                    guest_path=guest_path,
                ),
                "with sudo",
            )
            to_install.append(guest_path)
        when_i_run_command(
            context,
            "lxc exec {guest_name} -- apt install -y {packages}".format(
                guest_name=guest_name, packages=" ".join(to_install)
            ),
            "with sudo",
        )
    else:
        setup_pro_package_sources(context)

        when_i_run_command(
            context,
            "lxc file push /tmp/setup_pro.sh {guest_name}/root/setup_pro.sh".format(  # noqa: E501
                guest_name=guest_name
            ),
            "with sudo",
        )
        when_i_run_command(
            context,
            "lxc exec {guest_name} -- bash /root/setup_pro.sh".format(
                guest_name=guest_name
            ),
            "with sudo",
        )
        when_i_run_command(
            context,
            "lxc exec {guest_name} -- apt install -y {packages}".format(
                guest_name=guest_name,
                packages=" ".join(NORMAL_BINARY_PACKAGE_NAMES),
            ),
            "with sudo",
        )


@when("I ensure -proposed is not enabled anymore")
def when_i_ensure_proposed_not_enabled(context, machine_name=SUT):
    if context.pro_config.install_from is InstallationSource.PROPOSED:
        when_i_run_command(
            context,
            "rm -f /etc/apt/sources.list.d/proposed.list",
            "with sudo",
            machine_name=machine_name,
        )
        when_i_apt_update(context, machine_name=machine_name)


@when("I have the `{series}` debs under test in `{dest}`")
def when_i_have_the_debs_under_test(context, series, dest):
    if context.pro_config.install_from is InstallationSource.LOCAL:
        debs = build_debs(
            series,
            sbuild_output_to_terminal=context.pro_config.sbuild_output_to_terminal,  # noqa: E501
        )

        for deb_name, deb_path in debs.all_debs(series):
            context.machines[SUT].instance.push_file(
                deb_path, "{}/{}.deb".format(dest, deb_name)
            )
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
        for package in ALL_BINARY_PACKAGE_NAMES:
            when_i_run_shell_command(
                context,
                "cp {package}_*.deb {package}.deb".format(package=package),
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
    given_a_machine(context, "noble", "lxd-container", machine_name="ppa")
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
    debs = build_debs(
        release,
        sbuild_output_to_terminal=context.pro_config.sbuild_output_to_terminal,
    )
    for deb_name, deb_path in debs.all_debs(release):
        deb_destination = "/tmp/{}.deb".format(deb_name)
        context.machines["ppa"].instance.push_file(deb_path, deb_destination)
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


@when("I install ubuntu-pro-auto-attach")
@when("I install ubuntu-advantage-pro")
def when_i_install_pro(context, machine_name=SUT):
    if context.pro_config.install_from is InstallationSource.LOCAL:
        series = context.machines[machine_name].series
        debs = build_debs(
            series,
            sbuild_output_to_terminal=context.pro_config.sbuild_output_to_terminal,  # noqa: E501
        )

        to_install = []
        for deb_name, deb_path in debs.cloud_pro_image_debs():
            instance_tmp_path = "/tmp/behave_{}.deb".format(deb_name)
            context.machines[machine_name].instance.push_file(
                deb_path, instance_tmp_path
            )
            to_install.append(instance_tmp_path)
        when_i_apt_install(
            context, " ".join(to_install), machine_name=machine_name
        )
    else:
        when_i_apt_install(
            context, "ubuntu-pro-auto-attach", machine_name=machine_name
        )


APT_POLICY_IS = "the apt-cache policy of ubuntu-pro-client is"


@then(APT_POLICY_IS)
def then_i_apt_cache_policy_is(context):
    pass


@when("I check the apt-cache policy of ubuntu-pro-client")
def when_i_check_apt_cache_policy(context):
    when_i_run_command(context, "apt-get update", "with sudo")
    when_i_run_command(
        context, "apt-cache policy ubuntu-pro-client", "with sudo"
    )
    for step in context.scenario.steps:
        if step.name == APT_POLICY_IS:
            step.text = context.process.stdout


@when("I install transition package ubuntu-advantage-tools")
def when_i_install_transition_uat(context, machine_name=SUT):
    is_pro = "pro" in context.machines[machine_name].machine_type
    setup_pro_package_sources(context, machine_name)

    when_i_apt_install(
        context, "ubuntu-advantage-tools", machine_name=machine_name
    )
    if is_pro:
        when_i_apt_install(
            context,
            "ubuntu-advantage-pro",
            machine_name=machine_name,
        )
