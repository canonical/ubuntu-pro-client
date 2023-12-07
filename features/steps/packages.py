import re

from behave import then, when
from hamcrest import assert_that, contains_string, matches_regexp

from features.steps.shell import when_i_retry_run_command, when_i_run_command
from features.util import SUT


@when("I apt dist-upgrade")
def when_i_dist_update(context):
    when_i_run_command(
        context,
        "apt dist-upgrade --assume-yes --allow-downgrades",
        "with sudo",
    )


@then("I ensure apt update runs without errors")
def then_i_check_apt_update(context):
    when_i_run_command(
        context,
        "apt update",
        "with sudo",
    )


@when("I apt update")
@when("I apt update on the `{machine_name}` machine")
def when_i_apt_update(context, machine_name=SUT):
    when_i_retry_run_command(
        context,
        "apt update",
        "with sudo",
        machine_name=machine_name,
        exit_codes="100",
    )


@when("I apt install `{package_names}`")
@when("I apt install `{package_names}` on the `{machine_name}` machine")
def when_i_apt_install(context, package_names, machine_name=SUT):
    when_i_retry_run_command(
        context,
        " ".join(
            [
                "DEBIAN_FRONTEND=noninteractive",
                "apt",
                "install",
                "-y",
                "--allow-downgrades",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
                *package_names.split(" "),
            ]
        ),
        "with sudo",
        machine_name=machine_name,
        exit_codes="100",
    )


@then("apt-cache policy for the following url has priority `{prio_id}`")
def then_apt_cache_policy_for_the_following_url_has_priority_prio_id(
    context, prio_id
):
    full_url = "{} {}".format(prio_id, context.text)
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


@then("I verify that `{package}` is not installed")
def verify_package_not_installed(context, package):
    when_i_run_command(
        context, "apt-cache policy {}".format(package), "as non-root"
    )
    output = context.process.stdout.strip()
    if "Installed" in output:
        assert_that(
            context.process.stdout.strip(),
            contains_string("Installed: (none)"),
        )
    # If no output or it doesn't contain installation information,
    # then the package is neither installed nor known


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
    # Dummy packages are installed to serve as third-party and unknown
    # packages for the tests. Those packages are in Launchpad PPAs
    # owned by the uaclient team.
    # Many APT updates just to make sure we are up to date

    # Unknown package - we remove the PPA afterwards so there is no
    # external references for the deb.
    when_i_run_command(
        context,
        "add-apt-repository -y ppa:ua-client/pro-client-ci-test-unknown",
        "with sudo",
    )
    when_i_run_command(context, "apt-get update", "with sudo")
    when_i_run_command(
        context, "apt-get install -y pro-dummy-unknown", "with sudo"
    )
    # Why no remove-apt-repository?
    when_i_run_command(
        context,
        "add-apt-repository -y -r ppa:ua-client/pro-client-ci-test-unknown",
        "with sudo",
    )

    # PPA to install the third-party package
    when_i_run_command(
        context,
        "add-apt-repository -y ppa:ua-client/pro-client-ci-test-thirdparty",
        "with sudo",
    )
    when_i_run_command(context, "apt-get update", "with sudo")
    when_i_run_command(
        context, "apt-get install -y pro-dummy-thirdparty", "with sudo"
    )


@when("I store candidate version of package `{package}`")
def store_candidate_version(context, package):
    when_i_run_command(
        context,
        "apt-cache policy {}".format(package),
        "as non-root",
    )

    candidate_version_match = re.search(
        "Candidate:(?P<candidate>.*)", context.process.stdout
    )

    if candidate_version_match:
        context.stored_vars["candidate"] = candidate_version_match.group(
            1
        ).strip()
