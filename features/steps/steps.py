import datetime
import logging
import os
import subprocess
import re
import shlex
import time

from behave import given, then, when
from hamcrest import (
    assert_that,
    equal_to,
    matches_regexp,
    not_,
    contains_string,
)

from features.environment import (
    USERDATA_BLOCK_AUTO_ATTACH_TESTS,
    create_uat_image,
)
from features.util import SLOW_CMDS, emit_spinner_on_travis, nullcontext

from uaclient.defaults import DEFAULT_CONFIG_FILE


CONTAINER_PREFIX = "ubuntu-behave-test-"


@given("a `{series}` machine with ubuntu-advantage-tools installed")
def given_a_machine(context, series):
    filter_series = context.config.filter_series
    if filter_series and series not in filter_series:
        context.scenario.skip(
            reason=(
                "Skipping scenario outline series {series}."
                " Cmdline provided @series tags: {cmdline_series}".format(
                    series=series, cmdline_series=filter_series
                )
            )
        )
        return
    if series in context.reuse_container:
        context.container_name = context.reuse_container[series]
        context.instance = context.config.cloud_api.get_instance(
            context.container_name
        )
        if "pro" in context.config.machine_type:
            context.instance = context.config.cloud_api.get_instance(
                context.container_name
            )
        return

    if series not in context.series_image_name:
        with emit_spinner_on_travis():
            create_uat_image(context, series)

    is_vm = bool(context.config.machine_type == "lxd.vm")
    pr_number = os.environ.get("UACLIENT_BEHAVE_JENKINS_CHANGE_ID")
    now = datetime.datetime.now()

    vm_prefix = "vm-" if is_vm else ""
    pr_prefix = str(pr_number) + "-" if pr_number else ""
    date_prefix = now.strftime("-%s%f")

    instance_name = (
        CONTAINER_PREFIX + pr_prefix + vm_prefix + series + date_prefix
    )
    if "pro" in context.config.machine_type:
        user_data = USERDATA_BLOCK_AUTO_ATTACH_TESTS
    else:
        user_data = ""

    context.instance = context.config.cloud_manager.launch(
        series=series,
        instance_name=instance_name,
        image_name=context.series_image_name[series],
        user_data=user_data,
    )

    context.container_name = context.config.cloud_manager.get_instance_id(
        context.instance
    )

    def cleanup_instance() -> None:
        if not context.config.destroy_instances:
            print(
                "--- Leaving instance running: {}".format(
                    context.instance.name
                )
            )
        else:
            try:
                context.instance.delete(wait=False)
            except RuntimeError as e:
                print(
                    "Failed to delete instance: {}\n{}".format(
                        context.instance.name, str(e)
                    )
                )

    context.add_cleanup(cleanup_instance)
    print("--- instance ip: {}".format(context.instance.ip))


@when("I run `{command}` {user_spec}, retrying exit [{exit_codes}]")
def when_i_retry_run_command(context, command, user_spec, exit_codes):
    when_i_run_command(context, command, user_spec, verify_return=False)
    retries = [5, 5, 10]  # Sleep times to wait between retries
    while str(context.process.returncode) in exit_codes.split(","):
        try:
            time.sleep(retries.pop(0))
        except IndexError:  # no more timeouts
            logging.warning(
                "Exhausted retries waiting for exit codes: %s", exit_codes
            )
            break
        print(
            "--- Retrying on exit {exit_code}: {command}".format(
                exit_code=context.process.returncode, command=command
            )
        )
        when_i_run_command(context, command, user_spec, verify_return=False)
    assert_that(context.process.returncode, equal_to(0))


@when("I run `{command}` {user_spec}")
def when_i_run_command(context, command, user_spec, verify_return=True):
    prefix = get_command_prefix_for_user_spec(user_spec)
    slow_cmd_spinner = nullcontext
    for slow_cmd in SLOW_CMDS:
        if slow_cmd in command:
            slow_cmd_spinner = emit_spinner_on_travis
            break

    full_cmd = prefix + shlex.split(command)
    with slow_cmd_spinner():
        result = context.instance.execute(full_cmd)

    process = subprocess.CompletedProcess(
        args=full_cmd,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.return_code,
    )

    if verify_return and result.return_code != 0:
        print("Error executing command: {}".format(command))
        print("stdout: {}".format(result.stdout))
        print("stderr: {}".format(result.stderr))

    if verify_return:
        assert_that(process.returncode, equal_to(0))

    context.process = process


@when("I attach `{token_type}` {user_spec}")
def when_i_attach_staging_token(context, token_type, user_spec):
    token = getattr(context.config, token_type)
    if token_type == "contract_token_staging":
        when_i_run_command(
            context,
            "sed -i 's/contracts.can/contracts.staging.can/' {}".format(
                DEFAULT_CONFIG_FILE
            ),
            user_spec,
        )
    cmd = "ua attach {}".format(token)
    when_i_run_command(context, cmd, user_spec, verify_return=False)

    retries = [5, 5, 10]  # Sleep times to wait between retries
    while context.process.returncode != 0:
        try:
            time.sleep(retries.pop(0))
        except IndexError:  # no more timeouts
            logging.warning("Exhausted retries waiting for exit code: 0")
            break
        print(
            "--- Retrying on exit {exit_code}: {cmd}".format(
                exit_code=context.process.returncode, cmd=cmd
            )
        )
        when_i_run_command(context, cmd, user_spec, verify_return=False)


@when("I append the following on uaclient config")
def when_i_append_to_uaclient_config(context):
    cmd = "printf '{}\n' > /tmp/uaclient.conf".format(context.text)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "as non-root")

    cmd = "cat /tmp/uaclient.conf >> {}".format(DEFAULT_CONFIG_FILE)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I create the file `{file_path}` with the following")
def when_i_create_file_with_content(context, file_path):
    text = context.text.replace('"', '\\"')

    cmd = "printf '{}\n' > {}".format(text, file_path)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I reboot the `{series}` machine")
def when_i_reboot_the_machine(context, series):
    if series == "trusty":
        # TODO(LP: #1899299: LTS upgrade T->X pickled ds breaks Paths.run_dir)
        # When Fix is SRUd to Xenial, we can drop the trusty clause
        logging.warning(
            "LP: #1899299: Not raising cloud-init-errors across Trusty reboot"
        )
        context.instance.shutdown(wait=True)
        context.instance.start(wait=False)
        # Trusty -> Xenial upgrades would raise a Paths no run_dir attr failure
        context.instance.wait()
    else:
        context.instance.restart(wait=True)


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("if `{value1}` in `{value2}` and stdout matches regexp")
def then_conditional_stdout_matches_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stdout_matches_regexp(context)


@then("stdout matches regexp")
def then_stdout_matches_regexp(context):
    assert_that(context.process.stdout.strip(), matches_regexp(context.text))


@then("stdout does not match regexp")
def then_stdout_does_not_match_regexp(context):
    assert_that(
        context.process.stdout.strip(), not_(matches_regexp(context.text))
    )


@then("stderr matches regexp")
def then_stderr_matches_regexp(context):
    assert_that(context.process.stderr.strip(), matches_regexp(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))


@then("I will see the uaclient version on stdout")
def then_i_will_see_the_uaclient_version_on_stdout(context, feature_str=""):
    python_import = "from uaclient.version import get_version"

    cmd = "python3 -c '{}; print(get_version())'".format(python_import)

    actual_version = context.process.stdout.strip()
    when_i_run_command(context, cmd, "as non-root")
    expected_version = context.process.stdout.strip() + feature_str

    assert_that(expected_version, equal_to(actual_version))


@then("I will see the uaclient version on stdout with features `{features}`")
def then_i_will_see_the_uaclient_version_with_feature_suffix(
    context, features
):
    then_i_will_see_the_uaclient_version_on_stdout(
        context, feature_str=features
    )


@then("I verify that the `{cmd_name}` command is not found")
def then_i_should_see_that_the_command_is_not_found(context, cmd_name):
    cmd = "which {} || echo FAILURE".format(cmd_name)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "as non-root")

    expected_return = "FAILURE"
    actual_return = context.process.stdout.strip()
    assert_that(expected_return, equal_to(actual_return))


@then("I verify that running `{cmd_name}` `{spec}` exits `{exit_codes}`")
def then_i_verify_that_running_cmd_with_spec_exits_with_codes(
    context, cmd_name, spec, exit_codes
):
    when_i_run_command(context, cmd_name, spec, verify_return=False)

    expected_codes = exit_codes.split(",")
    assert str(context.process.returncode) in expected_codes


@when("I verify that running `{cmd_name}` `{spec}` exits `{exit_codes}`")
def when_i_verify_that_running_cmd_with_spec_exits_with_codes(
    context, cmd_name, spec, exit_codes
):
    then_i_verify_that_running_cmd_with_spec_exits_with_codes(
        context, cmd_name, spec, exit_codes
    )


@then("apt-cache policy for the following url has permission `{perm_id}`")
def then_apt_cache_policy_for_the_following_url_has_permission_perm_id(
    context, perm_id
):
    full_url = "{} {}".format(perm_id, context.text)
    assert_that(context.process.stdout.strip(), matches_regexp(full_url))


@then("I verify that files exist matching `{path_regex}`")
def there_should_be_files_matching_regex(context, path_regex):
    when_i_run_command(
        context, "ls {}".format(path_regex), "with sudo", verify_return=False
    )
    if context.process.returncode != 0:
        raise AssertionError("Missing expected files: {}".format(path_regex))


@then("I verify that no files exist matching `{path_regex}`")
def there_should_be_no_files_matching_regex(context, path_regex):
    when_i_run_command(
        context, "ls {}".format(path_regex), "with sudo", verify_return=False
    )
    if context.process.returncode == 0:
        raise AssertionError(
            "Unexpected files found: {}".format(context.process.stdout.strip())
        )


@then("I verify that `{package}` installed version matches regexp `{regex}`")
def verify_installed_package_matches_version_regexp(context, package, regex):
    when_i_run_command(
        context,
        "dpkg-query --showformat='${{Version}}' --show {}".format(package),
        "as non-root",
    )
    assert_that(context.process.stdout.strip(), matches_regexp(regex))


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


def get_command_prefix_for_user_spec(user_spec):
    prefix = []
    if user_spec == "with sudo":
        prefix = ["sudo"]
    elif user_spec != "as non-root":
        raise Exception(
            "The two acceptable values for user_spec are: 'with sudo',"
            " 'as non-root'"
        )
    return prefix
