import datetime
import json
import logging
import os
import re
import shlex
import subprocess
import time

import yaml
from behave import given, then, when
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    matches_regexp,
    not_,
)

from features.environment import (
    capture_container_as_image,
    create_instance_with_uat_installed,
)
from features.util import SLOW_CMDS, emit_spinner_on_travis, nullcontext
from uaclient.defaults import DEFAULT_CONFIG_FILE, DEFAULT_MACHINE_TOKEN_PATH
from uaclient.util import DatetimeAwareJSONDecoder

CONTAINER_PREFIX = "ubuntu-behave-test"
IMAGE_BUILD_PREFIX = "ubuntu-behave-image-build"
IMAGE_PREFIX = "ubuntu-behave-image"


def add_test_name_suffix(context, series, prefix):
    pr_number = os.environ.get("UACLIENT_BEHAVE_JENKINS_CHANGE_ID")
    pr_suffix = "-" + str(pr_number) if pr_number else ""
    is_vm = bool(context.config.machine_type == "lxd.vm")
    vm_suffix = "-vm" if is_vm else ""
    time_suffix = datetime.datetime.now().strftime("-%s%f")

    return "{prefix}{pr_suffix}{vm_suffix}-{series}{time_suffix}".format(
        prefix=prefix,
        pr_suffix=pr_suffix,
        vm_suffix=vm_suffix,
        series=series,
        time_suffix=time_suffix,
    )


@given("a `{series}` machine with ubuntu-advantage-tools installed")
def given_a_machine(context, series):
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

    instance_name = add_test_name_suffix(context, series, CONTAINER_PREFIX)

    if context.config.snapshot_strategy:
        if series not in context.series_image_name:
            with emit_spinner_on_travis():
                build_container_name = add_test_name_suffix(
                    context, series, IMAGE_BUILD_PREFIX
                )
                image_inst = create_instance_with_uat_installed(
                    context, series, build_container_name
                )

                image_name = add_test_name_suffix(
                    context, series, IMAGE_PREFIX
                )
                image_inst_id = context.config.cloud_manager.get_instance_id(
                    image_inst
                )
                image_id = capture_container_as_image(
                    image_inst_id,
                    image_name=image_name,
                    cloud_api=context.config.cloud_api,
                )
                context.series_image_name[series] = image_id
                image_inst.delete(wait=False)

        inst = context.config.cloud_manager.launch(
            series=series,
            instance_name=instance_name,
            image_name=context.series_image_name[series],
            ephemeral=context.config.ephemeral_instance,
        )
    else:
        inst = create_instance_with_uat_installed(
            context, series, instance_name
        )

    context.instances = {"uaclient": inst}

    context.container_name = context.config.cloud_manager.get_instance_id(
        context.instances["uaclient"]
    )

    def cleanup_instance() -> None:
        if not context.config.destroy_instances:
            logging.info(
                "--- Leaving instance running: {}".format(
                    context.instances["uaclient"].name
                )
            )
        else:
            try:
                context.instances["uaclient"].delete(wait=False)
            except RuntimeError as e:
                logging.error(
                    "Failed to delete instance: {}\n{}".format(
                        context.instances["uaclient"].name, str(e)
                    )
                )

    context.add_cleanup(cleanup_instance)
    logging.info(
        "--- instance ip: {}".format(context.instances["uaclient"].ip)
    )


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
            logging.error(
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
        logging.info(
            "--- Retrying on exit {exit_code}: {command}".format(
                exit_code=context.process.returncode, command=command
            )
        )
        when_i_run_command(context, command, user_spec, verify_return=False)
    assert_that(context.process.returncode, equal_to(0))


@when("I run `{command}` `{user_spec}` and stdin `{stdin}`")
def when_i_run_command_with_stdin(
    context, command, user_spec, stdin, instance_name="uaclient"
):
    when_i_run_command(
        context=context, command=command, user_spec=user_spec, stdin=stdin
    )


@when("I run `{command}` {user_spec}")
def when_i_run_command(
    context,
    command,
    user_spec,
    verify_return=True,
    stdin=None,
    instance_name="uaclient",
):
    if "<ci-proxy-ip>" in command:
        command = command.replace(
            "<ci-proxy-ip>", context.instances["proxy"].ip
        )
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
        logging.error("Error executing command: {}".format(command))
        logging.error("stdout: {}".format(result.stdout))
        logging.error("stderr: {}".format(result.stderr))

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
            logging.info(
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
    if "<ci-proxy-ip>" in text:
        text = text.replace("<ci-proxy-ip>", context.instances["proxy"].ip)
    cmd = "printf '{}\n' > {}".format(text, file_path)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I delete the file `{file_path}`")
def when_i_delete_file(context, file_path):
    cmd = "rm -rf {}".format(file_path)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I reboot the `{series}` machine")
def when_i_reboot_the_machine(context, series):
    context.instances["uaclient"].restart(wait=True)


@when("I wait `{seconds}` seconds")
def when_i_wait(context, seconds):
    time.sleep(int(seconds))


@then("I will see the following on stdout")
def then_i_will_see_on_stdout(context):
    assert_that(context.process.stdout.strip(), equal_to(context.text))


@then("if `{value1}` in `{value2}` and stdout matches regexp")
def then_conditional_stdout_matches_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_matches_regexp(context, "stdout")


@then("if `{value1}` in `{value2}` and stdout does not match regexp")
def then_conditional_stdout_does_not_match_regexp(context, value1, value2):
    """Only apply regex assertion if value1 in value2."""
    if value1 in value2.split(" or "):
        then_stream_does_not_match_regexp(context, "stdout")


@then("stdout is formatted as `{output_format}` and has keys")
def then_stdout_is_formatted_and_has_keys(context, output_format):
    output = context.process.stdout.strip()
    if output_format == "json":
        data = json.loads(output)
    elif output_format == "yaml":
        data = yaml.safe_load(output)

    keys = set(context.text.split())
    output_keys = set(data.keys())

    if keys != output_keys:
        message = """
        Missing keys in output: {}
        Extra keys in output: {}
        """.format(
            keys - output_keys or "", output_keys - keys or ""
        )
        raise AssertionError(message)


@then("{stream} does not match regexp")
def then_stream_does_not_match_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    assert_that(content, not_(matches_regexp(context.text)))


@then("{stream} matches regexp")
def then_stream_matches_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    assert_that(content, matches_regexp(context.text))


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


@when(
    "I verify that running `{cmd_name}` `{spec}` and stdin `{stdin}` exits `{exit_codes}`"  # noqa
)
def then_i_verify_that_running_cmd_with_spec_and_stdin_exits_with_codes(
    context, cmd_name, spec, stdin, exit_codes
):
    when_i_run_command(
        context, cmd_name, spec, stdin=stdin, verify_return=False
    )

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


@then("I verify that the timer interval for `{job}` is `{interval}`")
def verify_timer_interval_for_job(context, job, interval):
    when_i_run_command(
        context, "cat /var/lib/ubuntu-advantage/jobs-status.json", "with sudo"
    )
    jobs_status = json.loads(
        context.process.stdout.strip(), cls=DatetimeAwareJSONDecoder
    )
    last_run = jobs_status[job]["last_run"]
    next_run = jobs_status[job]["next_run"]
    run_diff = next_run - last_run

    assert_that(run_diff.seconds, equal_to(int(interval)))


def systemd_timer_info(context, timer_name, all=False):
    all_flag = " --all" if all else ""
    when_i_run_command(
        context,
        "systemctl list-timers {}.timer{}".format(timer_name, all_flag),
        "with sudo",
    )
    output = context.process.stdout.strip()
    lines = output.split("\n")
    return next((line for line in lines if timer_name in line), None)


@then("I verify the `{timer_name}` systemd timer is disabled")
def verify_systemd_timer_disabled(context, timer_name):
    timer_info_str = systemd_timer_info(context, timer_name)
    if timer_info_str is not None:
        raise AssertionError(
            "timer {} is not disabled:\n{}".format(timer_name, timer_info_str)
        )


@then(
    "I verify the `{timer_name}` systemd timer ran within the last `{seconds}` seconds"  # noqa: E501
)
def verify_systemd_timer_ran(context, timer_name, seconds):
    timer_info_str = systemd_timer_info(context, timer_name, all=True)
    if timer_info_str is None:
        raise AssertionError(
            "timer {} is not enabled or does not exist".format(timer_name)
        )
    match = re.match(r".*(left|n/a|ago)\s+(.+) UTC\s+(.+) ago", timer_info_str)
    if match is None:
        raise AssertionError(
            "timer {} has never run:\n{}".format(timer_name, timer_info_str)
        )
    datestr = match.group(2)
    last_ran = datetime.datetime.strptime(datestr, "%a %Y-%m-%d %H:%M:%S")
    if (datetime.datetime.utcnow() - last_ran) > datetime.timedelta(
        seconds=int(seconds)
    ):
        raise AssertionError(
            "timer {} has not run within {} seconds:\n{}".format(
                timer_name, seconds, timer_info_str
            )
        )


@then(
    "I verify the `{timer_name}` systemd timer is scheduled to run within `{minutes}` minutes"  # noqa: E501
)
def verify_systemd_timer_scheduled(context, timer_name, minutes):
    timer_info_str = systemd_timer_info(context, timer_name)
    if timer_info_str is None:
        raise AssertionError(
            "timer {} is not enabled or does not exist".format(timer_name)
        )
    match = re.match(r"^(.+) UTC\s+(.+) left", timer_info_str)
    if match is None:
        raise AssertionError(
            "timer {} is not scheduled to run:\n{}".format(
                timer_name, timer_info_str
            )
        )
    datestr = match.group(1)
    next_run = datetime.datetime.strptime(datestr, "%a %Y-%m-%d %H:%M:%S")
    if (next_run - datetime.datetime.utcnow()) > datetime.timedelta(
        minutes=int(minutes)
    ):
        raise AssertionError(
            "timer {} is not scheduled to run within {} minutes:\n{}".format(
                timer_name, minutes, timer_info_str
            )
        )


@then(
    "I verify the `{timer_name}` systemd timer either ran within the past `{seconds}` seconds OR is scheduled to run within `{minutes}` minutes"  # noqa: E501
)
def verify_systemd_timer_ran_or_scheduled(
    context, timer_name, seconds, minutes
):
    ran_error = None
    going_to_run_error = None
    try:
        verify_systemd_timer_ran(context, timer_name, seconds)
    except AssertionError as e:
        ran_error = e
    try:
        verify_systemd_timer_scheduled(context, timer_name, minutes)
    except AssertionError as e:
        going_to_run_error = e

    if ran_error and going_to_run_error:
        raise AssertionError("{}\n{}".format(ran_error, going_to_run_error))


@when("I save the `{key}` value from the contract")
def i_save_the_key_value_from_contract(context, key):
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_MACHINE_TOKEN_PATH),
        "with sudo",
    )
    output = context.process.stdout.strip()

    if output:
        if not hasattr(context, "saved_values"):
            setattr(context, "saved_values", {})

        context.saved_values[key] = output


def _get_saved_attr(context, key):
    saved_value = getattr(context, "saved_values", {}).get(key)

    if saved_value is None:
        raise AssertionError(
            "Value for key {} was not previously saved\n".format(key)
        )

    return saved_value


@then("I verify that `{key}` value has been updated on the contract")
def i_verify_that_key_value_has_been_updated(context, key):
    saved_value = _get_saved_attr(context, key)
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_MACHINE_TOKEN_PATH),
        "with sudo",
    )
    assert_that(context.process.stdout.strip(), not_(equal_to(saved_value)))


@then("I verify that `{key}` value has not been updated on the contract")
def i_verify_that_key_value_has_not_been_updated(context, key):
    saved_value = _get_saved_attr(context, key)
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_MACHINE_TOKEN_PATH),
        "with sudo",
    )
    assert_that(context.process.stdout.strip(), equal_to(saved_value))


@when("I restore the saved `{key}` value on contract")
def i_restore_the_saved_key_value_on_contract(context, key):
    saved_value = _get_saved_attr(context, key)
    when_i_update_contract_field_to_new_value(
        context=context,
        contract_field=key.split(".")[-1],
        new_value=saved_value,
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
