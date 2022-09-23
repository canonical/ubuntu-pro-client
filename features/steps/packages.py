import re

from behave import then, when
from hamcrest import assert_that, contains_string, matches_regexp

from features.steps.shell import when_i_run_command
from features.util import SUT


@when("I apt install `{package_name}`")
def when_i_apt_install(context, package_name, machine_name=SUT):
    when_i_run_command(
        context,
        " ".join(
            [
                "sudo",
                "DEBIAN_FRONTEND=noninteractive",
                "apt-get",
                "install",
                "-y",
                "--allow-downgrades",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
                package_name,
            ]
        ),
        "with sudo",
        machine_name=machine_name,
    )


@then("apt-cache policy for the following url has permission `{perm_id}`")
def then_apt_cache_policy_for_the_following_url_has_permission_perm_id(
    context, perm_id
):
    full_url = "{} {}".format(perm_id, context.text)
    assert_that(context.process.stdout.strip(), matches_regexp(full_url))


@then("I verify that `{package}` installed version matches regexp `{regex}`")
def verify_installed_package_matches_version_regexp(context, package, regex):
    when_i_run_command(
        context,
        "dpkg-query --showformat='${{Version}}' --show {}".format(package),
        "as non-root",
    )
    assert_that(context.process.stdout.strip(), matches_regexp(regex))


@then(
    "I verify that packages `{packages}` installed versions match regexp `{regex}`"  # noqa: E501
)
def verify_installed_packages_match_version_regexp(context, packages, regex):
    for package in packages.split(" "):
        verify_installed_package_matches_version_regexp(
            context, package, regex
        )


@then("I verify that `{package}` is installed from apt source `{apt_source}`")
def verify_package_is_installed_from_apt_source(context, package, apt_source):
    when_i_run_command(
        context, "apt-cache policy {}".format(package), "as non-root"
    )
    policy = context.process.stdout.strip()
    RE_APT_SOURCE = r"\s+\d+\s+(?P<source>.*)"
    lines = policy.splitlines()
    for index, line in enumerate(lines):
        if re.match(r"\s+\*\*\*", line):  # apt-policy installed prefix ***
            # Next line is the apt repo from which deb is installed
            installed_apt_source = re.match(RE_APT_SOURCE, lines[index + 1])
            if installed_apt_source is None:
                raise RuntimeError(
                    "Unable to process apt-policy line {}".format(
                        lines[index + 1]
                    )
                )
            assert_that(
                installed_apt_source.groupdict()["source"],
                contains_string(apt_source),
            )
            return
    raise AssertionError(
        "Package {package} is not installed".format(package=package)
    )


@then(
    "I verify that `{packages}` are installed from apt source `{apt_source}`"
)
def verify_packages_are_installed_from_apt_source(
    context, packages, apt_source
):
    for package in packages.split(" "):
        verify_package_is_installed_from_apt_source(
            context, package, apt_source
        )


@when("I install third-party / unknown packages in the machine")
def when_i_install_packages(context):
    # The `code` deb package sets up an apt remote for updates,
    # and is then listed as third-party.
    # https://code.visualstudio.com/download

    # The `gh` deb package is just installed locally,
    # and is then listed as unknown
    # https://github.com/cli/cli/releases
    when_i_run_command(context, "apt-get update", "with sudo")
    when_i_run_command(
        context,
        (
            "curl -L "
            "https://az764295.vo.msecnd.net/stable/"
            "e4503b30fc78200f846c62cf8091b76ff5547662/"
            "code_1.70.2-1660629410_amd64.deb "
            "-o /tmp/code.deb"
        ),
        "with sudo",
    )
    when_i_run_command(
        context,
        (
            "curl -L "
            "https://github.com/cli/cli/releases/download/"
            "v2.14.4/gh_2.14.4_linux_amd64.deb "
            "-o /tmp/gh.deb"
        ),
        "with sudo",
    )
    when_i_run_command(
        context, "apt-get install -y /tmp/code.deb", "with sudo"
    )
    when_i_run_command(context, "apt-get install -y /tmp/gh.deb", "with sudo")
    when_i_run_command(context, "apt-get update", "with sudo")
