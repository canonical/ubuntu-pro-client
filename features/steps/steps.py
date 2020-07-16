import datetime
import subprocess
import shlex

from behave import given, then, when
from hamcrest import assert_that, equal_to, matches_regexp

from features.util import (
    launch_lxd_container,
    launch_ec2,
    lxc_exec,
    wait_for_boot,
)

from uaclient.defaults import DEFAULT_CONFIG_FILE


CONTAINER_PREFIX = "behave-test-"


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
        if context.config.machine_type == "pro.aws":
            context.instance = context.config.ec2_api.get_instance(
                context.container_name
            )
    elif context.config.machine_type == "pro.aws":
        context.instance = launch_ec2(
            context,
            series=series,
            image_name=context.series_image_name[series],
        )
        context.container_name = context.instance.id
    else:
        is_vm = bool(context.config.machine_type == "lxd.vm")
        now = datetime.datetime.now()
        vm_prefix = "vm-" if is_vm else ""
        context.container_name = (
            CONTAINER_PREFIX + vm_prefix + series + now.strftime("-%s%f")
        )
        launch_lxd_container(
            context,
            series=series,
            image_name=context.series_image_name[series],
            container_name=context.container_name,
            is_vm=is_vm,
        )


@when("I run `{command}` {user_spec}")
def when_i_run_command(context, command, user_spec):
    prefix = get_command_prefix_for_user_spec(user_spec)
    full_cmd = prefix + shlex.split(command)
    if context.config.machine_type == "pro.aws":
        result = context.instance.execute(full_cmd)
        process = subprocess.CompletedProcess(
            args=full_cmd,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.return_code,
        )
    else:
        process = lxc_exec(
            context.container_name, full_cmd, capture_output=True, text=True
        )
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
    when_i_run_command(context, "ua attach %s" % token, user_spec)


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
    when_i_run_command(context, cmd, "as non-root")


@when("I reboot the `{series}` machine")
def when_i_reboot_the_machine(context, series):
    when_i_run_command(context, "reboot", "with sudo")

    is_vm = bool(context.config.machine_type == "lxd.vm")
    wait_for_boot(
        container_name=context.container_name, series=series, is_vm=is_vm
    )


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("stdout matches regexp")
def then_stdout_matches_regexp(context):
    assert_that(context.process.stdout.strip(), matches_regexp(context.text))


@then("stderr matches regexp")
def then_stderr_matches_regexp(context):
    assert_that(context.process.stderr.strip(), matches_regexp(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))


@then("I will see the uaclient version on stdout")
def then_i_will_see_the_uaclient_version_on_stdout(context, feature_str=None):
    python_import = "from uaclient.version import get_version"

    cmd = "python3 -c '{}; print(get_version())'".format(python_import)

    actual_version = context.process.stdout.strip()
    when_i_run_command(context, cmd, "as non-root")
    expected_version = context.process.stdout.strip() + feature_str

    assert_that(expected_version, equal_to(actual_version))


@then("I will see the uaclient version on stdout with features `{features}`")
def then_i_will_see_the_uaclient_version_with_feature_suffix(context, features):
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
