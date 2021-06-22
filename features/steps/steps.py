import datetime
import logging
import os
import subprocess
import re
import shlex
import time
import yaml

from behave import given, then, when
from hamcrest import (
    assert_that,
    equal_to,
    matches_regexp,
    not_,
    contains_string,
)

from features.environment import create_uat_image
from features.util import SLOW_CMDS, emit_spinner_on_travis, nullcontext

from uaclient.defaults import DEFAULT_CONFIG_FILE, DEFAULT_MACHINE_TOKEN_PATH
from uaclient.util import load_file


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
        context.instances = {}
        context.container_name = context.reuse_container[series]
        context.instances["uaclient"] = context.config.cloud_api.get_instance(
            context.container_name
        )
        if "pro" in context.config.machine_type:
            context.instances[
                "uaclient"
            ] = context.config.cloud_api.get_instance(context.container_name)
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

    context.instances = {
        "uaclient": context.config.cloud_manager.launch(
            series=series,
            instance_name=instance_name,
            image_name=context.series_image_name[series],
        )
    }

    context.container_name = context.config.cloud_manager.get_instance_id(
        context.instances["uaclient"]
    )

    def cleanup_instance() -> None:
        if not context.config.destroy_instances:
            print(
                "--- Leaving instance running: {}".format(
                    context.instances["uaclient"].name
                )
            )
        else:
            try:
                context.instances["uaclient"].delete(wait=False)
            except RuntimeError as e:
                print(
                    "Failed to delete instance: {}\n{}".format(
                        context.instances["uaclient"].name, str(e)
                    )
                )

    context.add_cleanup(cleanup_instance)
    logging.warning(
        "--- instance ip: {}".format(context.instances["uaclient"].ip)
    )
    print("--- instance ip: {}".format(context.instances["uaclient"].ip))


@when("I launch a `{series}` `{instance_name}` machine")
def launch_machine(context, series, instance_name):
    now = datetime.datetime.now()
    date_prefix = now.strftime("-%s%f")
    name = CONTAINER_PREFIX + series + date_prefix + "-" + instance_name

    context.instances[instance_name] = context.config.cloud_manager.launch(
        series=series, instance_name=name
    )

    def cleanup_instance() -> None:
        try:
            context.instances[instance_name].delete(wait=False)
        except RuntimeError as e:
            print(
                "Failed to delete instance: {}\n{}".format(
                    context.instances[instance_name].name, str(e)
                )
            )

    context.add_cleanup(cleanup_instance)


@when("I add this text on `{file_name}` on `{instance_name}` above `{line}`")
def when_i_add_this_text_on_file_above_line(
    context, file_name, instance_name, line
):
    command = 'sed -i "s/{}/{}\\n{}/" {}'.format(
        line, context.text, line, file_name
    )
    when_i_run_command(
        context, command, "with sudo", instance_name=instance_name
    )


@when("I run `{command}` `{user_spec}` on the `{instance_name}` machine")
def when_i_run_command_on_machine(context, command, user_spec, instance_name):
    when_i_run_command(
        context, command, user_spec, instance_name=instance_name
    )


@when(
    "I configure uaclient `{proxy_cfg}` proxy to use `{instance_name}` machine"
)
def when_i_configure_uaclient_using_proxy_machine(
    context, proxy_cfg, instance_name
):
    proxy_ip = context.instances[instance_name].ip

    # We can modify this code to get this info directly from squid.conf,
    # But I don't think we need this at this moment.
    port = "3128"

    # we are not configuring a full https proxy for the tests
    proxy_type = "http"

    proxy_cfg_value = "{}://{}:{}".format(proxy_type, proxy_ip, port)

    tmp_local_conf = "/tmp/uaclient.conf"
    context.instances["uaclient"].pull_file(
        DEFAULT_CONFIG_FILE, tmp_local_conf
    )
    cfg = yaml.safe_load(load_file(tmp_local_conf))

    if "ua_config" not in cfg:
        cfg["ua_config"] = {}
    cfg["ua_config"][proxy_cfg + "_proxy"] = proxy_cfg_value

    context.text = yaml.dump(cfg)
    when_i_append_to_uaclient_config(context)


@when("I verify `{file_name}` is empty on `{instance_name}` machine")
def when_i_verify_file_is_empty_on_machine(context, file_name, instance_name):
    command = 'sh -c "cat {} | wc -l"'
    when_i_run_command(
        context, command, user_spec="with sudo", instance_name=instance_name
    )

    assert_that(context.process.stdout.strip(), matches_regexp("0"))


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


@when("I run `{command}` {user_spec}, and provide the following stdin")
def when_i_run_command_with_stdin(context, command, user_spec):
    when_i_run_command(context, command, user_spec, stdin=context.text)


@when("I run `{command}` {user_spec}")
def when_i_run_command(
    context,
    command,
    user_spec,
    verify_return=True,
    stdin=None,
    instance_name="uaclient",
):
    prefix = get_command_prefix_for_user_spec(user_spec)
    slow_cmd_spinner = nullcontext
    for slow_cmd in SLOW_CMDS:
        if slow_cmd in command:
            slow_cmd_spinner = emit_spinner_on_travis
            break

    full_cmd = prefix + shlex.split(command)
    with slow_cmd_spinner():
        result = context.instances[instance_name].execute(
            full_cmd, stdin=stdin
        )

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


@when("I fix `{issue}` by attaching to a subscription with `{token_type}`")
def when_i_fix_a_issue_by_attaching(context, issue, token_type):
    token = getattr(context.config, token_type)
    when_i_run_command(
        context=context,
        command="ua fix {}".format(issue),
        user_spec="with sudo",
        stdin="a\n{}\n".format(token),
    )


@when("I fix `{issue}` by enabling required service")
def when_i_fix_a_issue_by_enabling_service(context, issue):
    when_i_run_command(
        context=context,
        command="ua fix {}".format(issue),
        user_spec="with sudo",
        stdin="e\n",
    )


@when("I fix `{issue}` by updating expired token")
def when_i_fix_a_issue_by_updating_expired_token(context, issue):
    token = getattr(context.config, "contract_token")
    when_i_run_command(
        context=context,
        command="ua fix {}".format(issue),
        user_spec="with sudo",
        stdin="r\n{}\n".format(token),
    )


@when("I update contract to use `{contract_field}` as `{new_value}`")
def when_i_update_contract_field_to_new_value(
    context, contract_field, new_value
):
    if contract_field == "effectiveTo":
        if "days=" in new_value:  # Set timedelta offset from current day
            now = datetime.datetime.utcnow()
            contract_expiry = now + datetime.timedelta(days=int(new_value[5:]))
            new_value = contract_expiry.strftime("%Y-%m-%dT00:00:00Z")
    when_i_run_command(
        context,
        'sed -i \'s/"{}": "[^"]*"/"{}": "{}"/g\' {}'.format(
            contract_field,
            contract_field,
            new_value,
            DEFAULT_MACHINE_TOKEN_PATH,
        ),
        user_spec="with sudo",
    )


@when("I attach `{token_type}` {user_spec}")
def when_i_attach_staging_token(
    context, token_type, user_spec, verify_return=True
):
    token = getattr(context.config, token_type)
    if (
        token_type == "contract_token_staging"
        or token_type == "contract_token_staging_expired"
    ):
        when_i_run_command(
            context,
            "sed -i 's/contracts.can/contracts.staging.can/' {}".format(
                DEFAULT_CONFIG_FILE
            ),
            user_spec,
        )
    cmd = "ua attach {}".format(token)
    when_i_run_command(context, cmd, user_spec, verify_return=False)

    if verify_return:
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


@when("I attempt to attach `{token_type}` {user_spec}")
def when_i_attempt_to_attach_staging_token(context, token_type, user_spec):
    when_i_attach_staging_token(
        context, token_type, user_spec, verify_return=False
    )


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
    context.instances["uaclient"].restart(wait=True)


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("if `{value1}` in `{value2}` and stdout matches regexp")
def then_conditional_stdout_matches_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stdout_matches_regexp(context)


@then("if `{value1}` in `{value2}` and stdout does not match regexp")
def then_conditional_stdout_does_not_match_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stdout_does_not_match_regexp(context)


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
