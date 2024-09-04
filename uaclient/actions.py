import datetime
import glob
import json
import logging
import os
import re
import shutil
from typing import List, Optional

from uaclient import (
    api,
    clouds,
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    livepatch,
)
from uaclient import log as pro_log
from uaclient import messages, secret_manager
from uaclient import status as ua_status
from uaclient import system, timer, util
from uaclient.defaults import (
    APPARMOR_PROFILES,
    CLOUD_BUILD_INFO,
    DEFAULT_CONFIG_FILE,
    DEFAULT_LOG_PREFIX,
)
from uaclient.files import machine_token, notices
from uaclient.files.state_files import (
    AttachmentData,
    attachment_data_file,
    machine_id_file,
    timer_jobs_state_file,
)

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


UA_SERVICES = (
    "apt-news.service",
    "esm-cache.service",
    "ua-timer.service",
    "ua-timer.timer",
    "ua-auto-attach.path",
    "ua-auto-attach.service",
    "ua-reboot-cmds.service",
    "ubuntu-advantage.service",
)

USER_LOG_COLLECTED_LIMIT = 10


def _handle_partial_attach(
    cfg: config.UAConfig,
    contract_client: contract.UAContractClient,
    attached_at: datetime.datetime,
):
    from uaclient.timer.update_messaging import update_motd_messages

    attachment_data_file.write(AttachmentData(attached_at=attached_at))
    ua_status.status(cfg=cfg)
    update_motd_messages(cfg)
    contract_client.update_activity_token()


def _enable_default_services(
    cfg: config.UAConfig,
    services_to_be_enabled: List[contract.EnableByDefaultService],
    contract_client: contract.UAContractClient,
    attached_at: datetime.datetime,
    silent: bool = False,
):
    ret = True
    failed_services = []
    unexpected_errors = []

    try:
        for enable_by_default_service in services_to_be_enabled:
            ent_ret, reason = enable_entitlement_by_name(
                cfg=cfg,
                name=enable_by_default_service.name,
                variant=enable_by_default_service.variant,
                silent=silent,
            )
            ret &= ent_ret

            if not ent_ret:
                failed_services.append(enable_by_default_service.name)
            else:
                event.service_processed(service=enable_by_default_service.name)
    except exceptions.ConnectivityError as exc:
        event.service_failed(enable_by_default_service.name)
        _handle_partial_attach(cfg, contract_client, attached_at)
        raise exc
    except exceptions.UbuntuProError:
        failed_services.append(enable_by_default_service.name)
        ret = False
    except Exception as e:
        ret = False
        failed_services.append(enable_by_default_service.name)
        unexpected_errors.append(e)

    if not ret:
        # Persist updated status in the event of partial attach
        _handle_partial_attach(cfg, contract_client, attached_at)
        event.services_failed(failed_services)

        if unexpected_errors:
            raise exceptions.AttachFailureUnknownError(
                failed_services=[
                    (
                        name,
                        messages.UNEXPECTED_ERROR.format(
                            error_msg=str(exception),
                            log_path=pro_log.get_user_or_root_log_file_path(),
                        ),
                    )
                    for name, exception in zip(
                        failed_services, unexpected_errors
                    )
                ]
            )
        else:
            raise exceptions.AttachFailureDefaultServices(
                failed_services=[
                    (name, messages.E_ATTACH_FAILURE_DEFAULT_SERVICES)
                    for name in failed_services
                ]
            )


def attach_with_token(
    cfg: config.UAConfig,
    token: str,
    allow_enable: bool,
    silent: bool = False,
) -> None:
    """
    Common functionality to take a token and attach via contract backend
    :raise ConnectivityError: On unexpected connectivity issues to contract
        server or inability to access identity doc from metadata service.
    :raise ContractAPIError: On unexpected errors when talking to the contract
        server.
    """
    from uaclient.entitlements import (
        check_entitlement_apt_directives_are_unique,
    )
    from uaclient.timer.update_messaging import update_motd_messages

    secret_manager.secrets.add_secret(token)
    machine_token_file = machine_token.get_machine_token_file(cfg)
    contract_client = contract.UAContractClient(cfg)
    attached_at = datetime.datetime.now(tz=datetime.timezone.utc)
    new_machine_token = contract_client.add_contract_machine(
        contract_token=token, attachment_dt=attached_at
    )
    current_series = system.get_release_info().series

    contractInfo = new_machine_token.get("machineTokenInfo", {}).get(
        "contractInfo", {}
    )
    support_resource = dict(
        (e.get("type"), e)
        for e in contractInfo.get("resourceEntitlements", [])
        if e.get("type") == "support"
    )
    only_series = (
        support_resource.get("support", {})
        .get("affordances", {})
        .get("onlySeries", None)
    )
    if only_series:
        allowed_release = system.get_distro_info(only_series)
        if only_series != current_series:
            raise exceptions.AttachFailureRestrictedRelease(
                release=allowed_release.release,
                series_codename=allowed_release.series_codename,
            )
        notices.add(
            notices.Notice.LIMITED_TO_RELEASE,
            release=allowed_release.release,
            series_codename=allowed_release.series_codename,
        )

    machine_token_file.write(new_machine_token)
    try:
        check_entitlement_apt_directives_are_unique(cfg)
    except exceptions.EntitlementsAPTDirectivesAreNotUnique as e:
        machine_token_file.delete()
        raise e

    system.get_machine_id.cache_clear()
    machine_id = new_machine_token.get("machineTokenInfo", {}).get(
        "machineId", system.get_machine_id(cfg)
    )
    machine_id_file.write(machine_id)

    if allow_enable:
        services_to_be_enabled = contract.get_enabled_by_default_services(
            cfg, machine_token_file.entitlements()
        )
        _enable_default_services(
            cfg=cfg,
            services_to_be_enabled=services_to_be_enabled,
            contract_client=contract_client,
            attached_at=attached_at,
            silent=silent,
        )

    attachment_data_file.write(AttachmentData(attached_at=attached_at))
    update_motd_messages(cfg)
    timer.start()


def auto_attach(
    cfg: config.UAConfig,
    cloud: clouds.AutoAttachCloudInstance,
    allow_enable=True,
) -> None:
    """
    :raise ConnectivityError: On unexpected connectivity issues to contract
        server or inability to access identity doc from metadata service.
    :raise ContractAPIError: On unexpected errors when talking to the contract
        server.
    :raise NonAutoAttachImageError: If this cloud type does not have
        auto-attach support.
    """
    contract_client = contract.UAContractClient(cfg)
    tokenResponse = contract_client.get_contract_token_for_cloud_instance(
        instance=cloud
    )

    token = tokenResponse["contractToken"]

    attach_with_token(cfg, token=token, allow_enable=allow_enable)


def enable_entitlement_by_name(
    cfg: config.UAConfig,
    name: str,
    *,
    access_only: bool = False,
    variant: str = "",
    silent: bool = False,
    extra_args: Optional[List[str]] = None
):
    """
    Constructs an entitlement based on the name provided. Passes kwargs onto
    the entitlement constructor.
    :raise EntitlementNotFoundError: If no entitlement with the given name is
        found, then raises this error.
    """
    entitlement = entitlements.entitlement_factory(
        cfg=cfg,
        name=name,
        variant=variant,
        access_only=access_only,
        extra_args=extra_args,
    )

    if not silent:
        event.info(messages.ENABLING_TMPL.format(title=entitlement.title))

    ent_ret, reason = entitlement.enable(api.ProgressWrapper())

    if ent_ret and not silent:
        event.info(messages.ENABLED_TMPL.format(title=entitlement.title))

    return ent_ret, reason


def status(
    cfg: config.UAConfig,
    *,
    simulate_with_token: Optional[str] = None,
    show_all: bool = False
):
    """
    Construct the current Pro status dictionary.
    """
    if simulate_with_token:
        status, ret = ua_status.simulate_status(
            cfg=cfg,
            token=simulate_with_token,
            show_all=show_all,
        )
    else:
        status = ua_status.status(cfg=cfg, show_all=show_all)
        ret = 0

    return status, ret


def _write_apparmor_logs_to_file(filename: str) -> None:
    """
    Helper which gets ubuntu_pro apparmor logs from the kernel from the last
    day and writes them to the specified filename.
    """
    # can't use journalctl's --grep, because xenial doesn't support it :/
    cmd = ["journalctl", "-b", "-k", "--since=1 day ago"]
    # all profiles are prefixed with "ubuntu_pro_"
    apparmor_re = r"apparmor=\".*(profile=\"ubuntu_pro_|name=\"ubuntu_pro_)"
    kernel_logs = None
    try:
        kernel_logs, _ = system.subp(cmd)
    except exceptions.ProcessExecutionError as e:
        LOG.warning("Failed to collect kernel logs:\n%s", str(e))
        system.write_file("{}-error".format(filename), str(e))
    else:
        if kernel_logs:  # some unit tests mock subp to return (None,None)
            apparmor_logs = []
            # filter out only what interests us
            for kernel_line in kernel_logs.split("\n"):
                if re.search(apparmor_re, kernel_line):
                    apparmor_logs.append(kernel_line)
            system.write_file(filename, "\n".join(apparmor_logs))


def _write_command_output_to_file(
    cmd, filename: str, return_codes: Optional[List[int]] = None
) -> None:
    """Helper which runs a command and writes output or error to filename."""
    try:
        out, err = system.subp(cmd.split(), rcs=return_codes)
    except exceptions.ProcessExecutionError as e:
        system.write_file("{}-error".format(filename), str(e))
    else:
        system.write_file(
            filename, "stdout:\n{}\n\nstderr:\n{}".format(out, err)
        )


def _get_state_files(cfg: config.UAConfig):
    # include cfg log files here because they could be set to non default
    return [
        cfg.cfg_path or DEFAULT_CONFIG_FILE,
        cfg.log_file,
        timer_jobs_state_file.ua_file.path,
        CLOUD_BUILD_INFO,
        *(
            entitlement_cls(cfg).repo_file
            for entitlement_cls in entitlements.ENTITLEMENT_CLASSES
            if issubclass(entitlement_cls, entitlements.repo.RepoEntitlement)
        ),
    ]


def collect_logs(cfg: config.UAConfig, output_dir: str):
    """
    Write all relevant Ubuntu Pro logs to the specified directory
    """
    _write_command_output_to_file(
        "cloud-id", "{}/cloud-id.txt".format(output_dir)
    )
    _write_command_output_to_file(
        "{} status".format(livepatch.LIVEPATCH_CMD),
        "{}/livepatch-status.txt".format(output_dir),
    )
    _write_command_output_to_file(
        "systemctl list-timers --all",
        "{}/systemd-timers.txt".format(output_dir),
    )
    _write_command_output_to_file(
        (
            "journalctl --boot=0 -o short-precise "
            "-u cloud-init-local.service "
            "-u cloud-init-config.service "
            "-u cloud-config.service"
        ),
        "{}/cloud-init-journal.txt".format(output_dir),
    )
    _write_command_output_to_file(
        ("journalctl -o short-precise " "{}").format(
            " ".join(
                ["-u {}".format(s) for s in UA_SERVICES if ".service" in s]
            )
        ),
        "{}/pro-journal.txt".format(output_dir),
    )
    for service in UA_SERVICES:
        _write_command_output_to_file(
            "systemctl status {}".format(service),
            "{}/{}.txt".format(output_dir, service),
            return_codes=[0, 3],
        )
    pro_status, _ = status(cfg=cfg, show_all=False)
    system.write_file(
        "{}/pro-status.json".format(output_dir),
        json.dumps(pro_status, cls=util.DatetimeAwareJSONEncoder),
    )
    env_vars = util.get_pro_environment()
    system.write_file(
        "{}/environment_vars.json".format(output_dir),
        json.dumps(env_vars),
    )

    state_files = _get_state_files(cfg)
    user_log_files = (
        pro_log.get_all_user_log_files()[:USER_LOG_COLLECTED_LIMIT]
        if util.we_are_currently_root()
        else [pro_log.get_user_log_file()]
    )
    # save log file in compressed file
    for log_file_idx, log_file in enumerate(user_log_files):
        try:
            content = util.redact_sensitive_logs(system.load_file(log_file))
            system.write_file(
                os.path.join(output_dir, "user{}.log".format(log_file_idx)),
                content,
            )
        except Exception as e:
            LOG.warning(
                "Failed to collect user log file: %s\n%s", log_file, str(e)
            )

    # also get default logrotated log files
    for f in state_files + glob.glob(DEFAULT_LOG_PREFIX + "*"):
        if os.path.isfile(f):
            try:
                content = system.load_file(f)
            except Exception as e:
                # If we fail to load that file for any reason we will
                # not break the command, we will instead warn the user
                # about the issue and try to process the other files
                LOG.warning("Failed to load file: %s\n%s", f, str(e))
                continue
            content = util.redact_sensitive_logs(content)
            if util.we_are_currently_root():
                # if root, overwrite the original with redacted content
                system.write_file(f, content)

            system.write_file(
                os.path.join(output_dir, os.path.basename(f)), content
            )

    # get apparmor logs
    _write_apparmor_logs_to_file("{}/apparmor_logs.txt".format(output_dir))

    # include apparmor profiles
    for f in APPARMOR_PROFILES:
        if os.path.isfile(f):
            try:
                shutil.copy(f, output_dir)
            except Exception as e:
                LOG.warning("Failed to copy file: %s\n%s", f, str(e))
                continue
