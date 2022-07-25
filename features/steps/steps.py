import datetime
import json
import logging
import os
import re
import shlex
import subprocess
import time

import jsonschema  # type: ignore
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
    UA_PPA_TEMPLATE,
    build_debs_from_sbuild,
    capture_container_as_image,
    create_instance_with_uat_installed,
)
from features.util import (
    InstallationSource,
    SafeLoaderWithoutDatetime,
    cleanup_instance,
)
from uaclient.defaults import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_PRIVATE_MACHINE_TOKEN_PATH,
)
from uaclient.util import DatetimeAwareJSONDecoder

CONTAINER_PREFIX = "ubuntu-behave-test"
IMAGE_BUILD_PREFIX = "ubuntu-behave-image-build"
IMAGE_PREFIX = "ubuntu-behave-image"

ERROR_CODE = "1"


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
def given_a_machine(context, series, custom_user_data=None):
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

    if context.config.snapshot_strategy and not custom_user_data:
        if series not in context.series_image_name:
            build_container_name = add_test_name_suffix(
                context, series, IMAGE_BUILD_PREFIX
            )
            image_inst = create_instance_with_uat_installed(
                context, series, build_container_name, custom_user_data
            )

            image_name = add_test_name_suffix(context, series, IMAGE_PREFIX)
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
            context, series, instance_name, custom_user_data
        )

    context.series = series
    context.instances = {"uaclient": inst}

    context.container_name = context.config.cloud_manager.get_instance_id(
        context.instances["uaclient"]
    )

    context.add_cleanup(cleanup_instance(context, "uaclient"))
    logging.info(
        "--- instance ip: {}".format(context.instances["uaclient"].ip)
    )


@when("I take a snapshot of the machine")
def when_i_take_a_snapshot(context):
    cloud = context.config.cloud_manager
    inst = context.instances["uaclient"]

    snapshot = cloud.api.snapshot(inst)

    context.instance_snapshot = snapshot

    def cleanup_image() -> None:
        try:
            context.config.cloud_manager.api.delete_image(
                context.instance_snapshot
            )
        except RuntimeError as e:
            logging.error(
                "Failed to delete image: {}\n{}".format(
                    context.instance_snapshot, str(e)
                )
            )

    context.add_cleanup(cleanup_image)


@given(
    "a `{series}` machine with ubuntu-advantage-tools installed adding this cloud-init user_data"  # noqa
)
def given_a_machine_with_user_data(context, series):
    custom_user_data = context.text
    given_a_machine(context, series, custom_user_data)


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
    "I launch a `{series}` `{instance_name}` machine with ingress ports `{ports}`"  # noqa
)
def launch_machine_with_ingress_ports(context, series, instance_name, ports):
    launch_machine(
        context=context,
        series=series,
        instance_name=instance_name,
        ports=ports,
    )


@when("I launch a `{series}` `{instance_name}` machine")
def launch_machine(context, series, instance_name, ports=None):
    now = datetime.datetime.now()
    date_prefix = now.strftime("-%s%f")
    name = CONTAINER_PREFIX + series + date_prefix + "-" + instance_name

    kwargs = {"series": series, "instance_name": name}
    if ports:
        kwargs["inbound_ports"] = ports.split(",")
    context.instances[instance_name] = context.config.cloud_manager.launch(
        **kwargs
    )

    context.add_cleanup(cleanup_instance(context, instance_name))


@when("I launch a `{instance_name}` machine from the snapshot")
def launch_machine_from_snapshot(context, instance_name):
    now = datetime.datetime.now()
    date_prefix = now.strftime("-%s%f")
    name = CONTAINER_PREFIX + date_prefix + "-" + instance_name

    context.instances[instance_name] = context.config.cloud_manager.launch(
        context.series,
        instance_name=name,
        image_name=context.instance_snapshot,
    )

    context.add_cleanup(cleanup_instance(context, instance_name))


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
    command = 'sh -c "cat {} | wc -l"'.format(file_name)
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
    context, command, user_spec, stdin, instancedebug_name="uaclient"
):
    when_i_run_command(
        context=context, command=command, user_spec=user_spec, stdin=stdin
    )


@when("I do a preflight check for `{contract_token}` {user_spec}")
def when_i_preflight(context, contract_token, user_spec, verify_return=True):
    token = getattr(context.config, contract_token, "invalid_token")
    command = "pro status --simulate-with-token {}".format(token)
    if user_spec == "with the all flag":
        command += " --all"
    if "formatted as" in user_spec:
        output_format = user_spec.split()[2]
        command += " --format {}".format(output_format)
    when_i_run_command(
        context=context,
        command=command,
        user_spec="as non-root",
        verify_return=verify_return,
    )


@when("I initiate the magic attach flow")
def when_i_initiate_magic_attach(context):
    when_i_run_command(
        context=context,
        command="pro api u.pro.attach.magic.initiate.v1",
        user_spec="as non-root",
    )

    magic_attach_resp = json.loads(
        context.process.stdout.strip(), cls=DatetimeAwareJSONDecoder
    )

    context.magic_token = magic_attach_resp["data"]["attributes"]["token"]


@when("I revoke the magic attach token")
def when_i_revoke_the_magic_attach_token(context):
    when_i_run_command(
        context=context,
        command="pro api u.pro.attach.magic.revoke.v1 --args magic_token={}".format(  # noqa
            context.magic_token
        ),
        user_spec="as non-root",
    )


@when("I wait for the magic attach token to be activated")
def when_i_wait_for_magic_attach_token(context):
    when_i_run_command(
        context=context,
        command="pro api u.pro.attach.magic.wait.v1 --args magic_token={}".format(  # noqa
            context.magic_token
        ),
        user_spec="as non-root",
    )


@when(
    "I verify that a preflight check for `{contract_token}` {user_spec} exits {exit_codes}"  # noqa
)
def when_i_attempt_preflight(context, contract_token, user_spec, exit_codes):
    when_i_preflight(context, contract_token, user_spec, verify_return=False)

    expected_codes = exit_codes.split(",")
    assert str(context.process.returncode) in expected_codes


@when("I run `{command}` {user_spec}")
def when_i_run_command(
    context,
    command,
    user_spec,
    verify_return=True,
    stdin=None,
    instance_name="uaclient",
):
    if "<ci-proxy-ip>" in command and "proxy" in context.instances:
        command = command.replace(
            "<ci-proxy-ip>", context.instances["proxy"].ip
        )
    prefix = get_command_prefix_for_user_spec(user_spec)

    full_cmd = prefix + shlex.split(command)
    result = context.instances[instance_name].execute(full_cmd, stdin=stdin)

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
    else:
        logging.debug("stdout: {}".format(result.stdout))
        logging.debug("stderr: {}".format(result.stderr))

    if verify_return:
        assert_that(process.returncode, equal_to(0))

    context.process = process


@when("I run shell command `{command}` {user_spec}")
def when_i_run_shell_command(context, command, user_spec):
    when_i_run_command(context, 'sh -c "{}"'.format(command), user_spec)


@when("I fix `{issue}` by attaching to a subscription with `{token_type}`")
def when_i_fix_a_issue_by_attaching(context, issue, token_type):
    token = getattr(context.config, token_type)

    if (
        token_type == "contract_token_staging"
        or token_type == "contract_token_staging_expired"
    ):
        change_contract_endpoint_to_staging(context, user_spec="with sudo")
    else:
        change_contract_endpoint_to_production(context, user_spec="with sudo")

    when_i_run_command(
        context=context,
        command="pro fix {}".format(issue),
        user_spec="with sudo",
        stdin="a\n{}\n".format(token),
        verify_return=False,
    )


@when("I fix `{issue}` by enabling required service")
def when_i_fix_a_issue_by_enabling_service(context, issue):
    when_i_run_command(
        context=context,
        command="pro fix {}".format(issue),
        user_spec="with sudo",
        stdin="e\n",
    )


@when("I fix `{issue}` by updating expired token")
def when_i_fix_a_issue_by_updating_expired_token(context, issue):
    token = getattr(context.config, "contract_token")
    when_i_run_command(
        context=context,
        command="pro fix {}".format(issue),
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
            DEFAULT_PRIVATE_MACHINE_TOKEN_PATH,
        ),
        user_spec="with sudo",
    )


@when("I change contract to staging {user_spec}")
def change_contract_endpoint_to_staging(context, user_spec):
    when_i_run_command(
        context,
        "sed -i 's/contracts.can/contracts.staging.can/' {}".format(
            DEFAULT_CONFIG_FILE
        ),
        user_spec,
    )


def change_contract_endpoint_to_production(context, user_spec):
    when_i_run_command(
        context,
        "sed -i 's/contracts.staging.can/contracts.can/' {}".format(
            DEFAULT_CONFIG_FILE
        ),
        user_spec,
    )


@when("I attach `{token_type}` {user_spec} and options `{options}`")
def when_i_attach_staging_token_with_options(
    context, token_type, user_spec, options
):
    when_i_attach_staging_token(
        context, token_type, user_spec, options=options
    )


@when("I attach `{token_type}` {user_spec}")
def when_i_attach_staging_token(
    context, token_type, user_spec, verify_return=True, options=""
):
    token = getattr(context.config, token_type)
    if (
        token_type == "contract_token_staging"
        or token_type == "contract_token_staging_expired"
    ):
        change_contract_endpoint_to_staging(context, user_spec)
    cmd = "pro attach {} {}".format(token, options).strip()
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
    if "<ci-proxy-ip>" in text and "proxy" in context.instances:
        text = text.replace("<ci-proxy-ip>", context.instances["proxy"].ip)
    cmd = "printf '{}\n' > {}".format(text, file_path)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I delete the file `{file_path}`")
def when_i_delete_file(context, file_path):
    cmd = "rm -rf {}".format(file_path)
    cmd = 'sh -c "{}"'.format(cmd)
    when_i_run_command(context, cmd, "with sudo")


@when("I reboot the machine")
def when_i_reboot_the_machine(context):
    context.instances["uaclient"].restart(wait=True)


@when("I reboot the `{machine}` machine")
def when_i_reboot_the_machine_name(context, machine):
    context.instances[machine].restart(wait=True)


@when("I wait `{seconds}` seconds")
def when_i_wait(context, seconds):
    time.sleep(int(seconds))


@when("I replace `{original}` in `{filename}` with `{new}`")
def when_i_replace_string_in_file(context, original, filename, new):
    new = new.replace("\\", r"\\")
    new = new.replace("/", r"\/")
    new = new.replace("&", r"\&")
    when_i_run_command(
        context,
        "sed -i 's/{original}/{new}/' {filename}".format(
            original=original, new=new, filename=filename
        ),
        "with sudo",
    )


@when("I replace `{original}` in `{filename}` with token `{token_name}`")
def when_i_replace_string_in_file_with_token(
    context, original, filename, token_name
):
    token = getattr(context.config, token_name)
    when_i_replace_string_in_file(context, original, filename, token)


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


@then("{stream} does not match regexp")
def then_stream_does_not_match_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    assert_that(content, not_(matches_regexp(context.text)))


@then("{stream} matches regexp")
def then_stream_matches_regexp(context, stream):
    content = getattr(context.process, stream).strip()
    text = context.text
    if "<ci-proxy-ip>" in text and "proxy" in context.instances:
        text = text.replace("<ci-proxy-ip>", context.instances["proxy"].ip)
    assert_that(content, matches_regexp(text))


@then("{stream} contains substring")
def then_stream_contains_substring(context, stream):
    content = getattr(context.process, stream).strip()
    assert_that(content, contains_string(context.text))


@then("I will see the following on stderr")
def then_i_will_see_on_stderr(context):
    assert_that(context.process.stderr.strip(), equal_to(context.text))


@then("I will see the uaclient version on stdout")
def then_i_will_see_the_uaclient_version_on_stdout(context):
    python_import = "from uaclient.version import get_version"

    cmd = "python3 -c '{}; print(get_version())'".format(python_import)

    actual_version = context.process.stdout.strip()
    when_i_run_command(context, cmd, "as non-root")
    expected_version = context.process.stdout.strip()

    assert_that(expected_version, equal_to(actual_version))


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
    "I verify that running attach `{spec}` with json response exits `{exit_codes}`"  # noqa
)
def when_i_verify_attach_with_json_response(context, spec, exit_codes):
    cmd = "pro attach {} --format json".format(context.config.contract_token)
    then_i_verify_that_running_cmd_with_spec_exits_with_codes(
        context=context, cmd_name=cmd, spec=spec, exit_codes=exit_codes
    )


@when(
    "I verify that running attach `{spec}` using expired token with json response fails"  # noqa
)
def when_i_verify_attach_expired_token_with_json_response(context, spec):
    change_contract_endpoint_to_staging(context, user_spec="with sudo")
    cmd = "pro attach {} --format json".format(
        context.config.contract_token_staging_expired
    )
    then_i_verify_that_running_cmd_with_spec_exits_with_codes(
        context=context, cmd_name=cmd, spec=spec, exit_codes=ERROR_CODE
    )


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
        "jq -r '.{}' {}".format(key, DEFAULT_PRIVATE_MACHINE_TOKEN_PATH),
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


@then(
    "I verify that `{key}` value has been updated on the contract on the `{machine}` machine"  # noqa: E501
)
def i_verify_that_key_value_has_been_updated_on_machine(context, key, machine):
    i_verify_that_key_value_has_been_updated(context, key, machine)


@then("I verify that `{key}` value has been updated on the contract")
def i_verify_that_key_value_has_been_updated(context, key, machine="uaclient"):
    saved_value = _get_saved_attr(context, key)
    when_i_run_command_on_machine(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_PRIVATE_MACHINE_TOKEN_PATH),
        "with sudo",
        instance_name=machine,
    )
    assert_that(context.process.stdout.strip(), not_(equal_to(saved_value)))


@then("I verify that `{key}` value has not been updated on the contract")
def i_verify_that_key_value_has_not_been_updated(context, key):
    saved_value = _get_saved_attr(context, key)
    when_i_run_command(
        context,
        "jq -r '.{}' {}".format(key, DEFAULT_PRIVATE_MACHINE_TOKEN_PATH),
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


@then("stdout is a {output_format} matching the `{schema}` schema")
def stdout_matches_the_json_schema(context, output_format, schema):
    if output_format == "json":
        instance = json.loads(context.process.stdout.strip())
    elif output_format == "yaml":
        instance = yaml.load(
            context.process.stdout.strip(), SafeLoaderWithoutDatetime
        )
    with open("features/schemas/{}.json".format(schema), "r") as schema_file:
        jsonschema.validate(instance=instance, schema=json.load(schema_file))


@then("the {output_format} API response data matches the `{schema}` schema")
def api_response_matches_schema(context, output_format, schema):
    if output_format == "json":
        instance = json.loads(context.process.stdout.strip())
    elif output_format == "yaml":
        instance = yaml.load(
            context.process.stdout.strip(), SafeLoaderWithoutDatetime
        )
    with open("features/schemas/{}.json".format(schema), "r") as schema_file:
        jsonschema.validate(
            instance=instance.get("data", {}).get("attributes"),
            schema=json.load(schema_file),
        )


@then("`{file_name}` is not present in any docker image layer")
def file_is_not_present_in_any_docker_image_layer(context, file_name):
    when_i_run_command(
        context,
        "find /var/lib/docker/overlay2 -name {}".format(file_name),
        "with sudo",
    )
    results = context.process.stdout.strip()
    if results:
        raise AssertionError(
            'found "{}"'.format(", ".join(results.split("\n")))
        )


# This defines "not significantly larger" as "less than 2MB larger"
@then(
    "docker image `{name}` is not significantly larger than `ubuntu:{series}` with `{package}` installed"  # noqa: E501
)
def docker_image_is_not_larger(context, name, series, package):
    base_image_name = "ubuntu:{}".format(series)
    base_upgraded_image_name = "{}-with-test-package".format(series)

    # We need to compare against the base image after apt upgrade
    # and package install
    dockerfile = """\
    FROM {}
    RUN apt-get update \\
      && apt-get install -y {} \\
      && rm -rf /var/lib/apt/lists/*
    """.format(
        base_image_name, package
    )
    context.text = dockerfile
    when_i_create_file_with_content(context, "Dockerfile.base")
    when_i_run_command(
        context,
        "docker build . -f Dockerfile.base -t {}".format(
            base_upgraded_image_name
        ),
        "with sudo",
    )

    # find image sizes
    when_i_run_shell_command(
        context, "docker inspect {} | jq .[0].Size".format(name), "with sudo"
    )
    custom_image_size = int(context.process.stdout.strip())
    when_i_run_shell_command(
        context,
        "docker inspect {} | jq .[0].Size".format(base_upgraded_image_name),
        "with sudo",
    )
    base_image_size = int(context.process.stdout.strip())

    # Get pro test deb size
    when_i_run_command(context, "du ubuntu-advantage-tools.deb", "with sudo")
    # Example out: "1234\tubuntu-advantage-tools.deb"
    ua_test_deb_size = (
        int(context.process.stdout.strip().split("\t")[0]) * 1024
    )  # KB -> B

    # Give us some space for bloat we don't control: 2MB -> B
    extra_space = 2 * 1024 * 1024

    if custom_image_size > (base_image_size + ua_test_deb_size + extra_space):
        raise AssertionError(
            "Custom image size ({}) is over 2MB greater than the base image"
            " size ({}) + pro test deb size ({})".format(
                custom_image_size, base_image_size, ua_test_deb_size
            )
        )
    logging.debug(
        "custom image size ({})\n"
        "base image size ({})\n"
        "pro test deb size ({})".format(
            custom_image_size, base_image_size, ua_test_deb_size
        )
    )


@then(
    "on `{release}`, systemd status output says memory usage is less than `{mb_limit}` MB"  # noqa
)
def systemd_memory_usage_less_than(context, release, mb_limit):
    curr_release = context.active_outline["release"]
    if release != curr_release:
        logging.debug("Skipping for {}".format(curr_release))
        return
    match = re.search(r"Memory: (.*)M", context.process.stdout.strip())
    if match is None:
        raise AssertionError(
            "Memory usage not present in current process stdout"
        )
    mb_used = float(match.group(1))
    logging.debug("Found {}M".format(mb_used))

    mb_limit_float = float(mb_limit)
    if mb_used > mb_limit_float:
        raise AssertionError(
            "Using more memory than expected ({}M)".format(mb_used)
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
