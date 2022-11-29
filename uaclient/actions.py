import glob
import logging
import os
from typing import List, Optional  # noqa: F401

from uaclient import (
    clouds,
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    messages,
)
from uaclient import status as ua_status
from uaclient import system, util
from uaclient.clouds import AutoAttachCloudInstance  # noqa: F401
from uaclient.clouds import identity
from uaclient.defaults import (
    CLOUD_BUILD_INFO,
    DEFAULT_CONFIG_FILE,
    DEFAULT_LOG_PREFIX,
)
from uaclient.entitlements.livepatch import LIVEPATCH_CMD
from uaclient.files.state_files import timer_jobs_state_file

LOG = logging.getLogger("pro.actions")
event = event_logger.get_event_logger()


UA_SERVICES = (
    "ua-timer.service",
    "ua-timer.timer",
    "ua-auto-attach.path",
    "ua-auto-attach.service",
    "ua-reboot-cmds.service",
    "ubuntu-advantage.service",
)


def attach_with_token(
    cfg: config.UAConfig, token: str, allow_enable: bool
) -> None:
    """
    Common functionality to take a token and attach via contract backend
    :raise UrlError: On unexpected connectivity issues to contract
        server or inability to access identity doc from metadata service.
    :raise ContractAPIError: On unexpected errors when talking to the contract
        server.
    """
    from uaclient.jobs.update_messaging import update_apt_and_motd_messages

    try:
        contract.request_updated_contract(
            cfg, token, allow_enable=allow_enable
        )
    except exceptions.UrlError as exc:
        # Persist updated status in the event of partial attach
        ua_status.status(cfg=cfg)
        update_apt_and_motd_messages(cfg)
        raise exc
    except exceptions.UserFacingError as exc:
        # Persist updated status in the event of partial attach
        ua_status.status(cfg=cfg)
        update_apt_and_motd_messages(cfg)
        raise exc

    current_iid = identity.get_instance_id()
    if current_iid:
        cfg.write_cache("instance-id", current_iid)

    update_apt_and_motd_messages(cfg)


def auto_attach(
    cfg: config.UAConfig,
    cloud: clouds.AutoAttachCloudInstance,
    allow_enable=True,
) -> None:
    """
    :raise UrlError: On unexpected connectivity issues to contract
        server or inability to access identity doc from metadata service.
    :raise ContractAPIError: On unexpected errors when talking to the contract
        server.
    :raise NonAutoAttachImageError: If this cloud type does not have
        auto-attach support.
    """
    contract_client = contract.UAContractClient(cfg)
    tokenResponse = contract_client.request_auto_attach_contract_token(
        instance=cloud
    )

    token = tokenResponse["contractToken"]

    attach_with_token(cfg, token=token, allow_enable=allow_enable)


def enable_entitlement_by_name(
    cfg: config.UAConfig,
    name: str,
    *,
    assume_yes: bool = False,
    allow_beta: bool = False,
    access_only: bool = False
):
    """
    Constructs an entitlement based on the name provided. Passes kwargs onto
    the entitlement constructor.
    :raise EntitlementNotFoundError: If no entitlement with the given name is
        found, then raises this error.
    """
    ent_cls = entitlements.entitlement_factory(cfg=cfg, name=name)
    entitlement = ent_cls(
        cfg,
        assume_yes=assume_yes,
        allow_beta=allow_beta,
        called_name=name,
        access_only=access_only,
    )
    return entitlement.enable()


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


def _write_command_output_to_file(
    cmd, filename: str, return_codes: Optional[List[int]] = None
) -> None:
    """Helper which runs a command and writes output or error to filename."""
    try:
        out, _ = system.subp(cmd.split(), rcs=return_codes)
    except exceptions.ProcessExecutionError as e:
        system.write_file("{}-error".format(filename), str(e))
    else:
        system.write_file(filename, out)


def _get_state_files(cfg: config.UAConfig):
    # include cfg log files here because they could be set to non default
    return [
        cfg.cfg_path or DEFAULT_CONFIG_FILE,
        cfg.log_file,
        cfg.timer_log_file,
        cfg.daemon_log_file,
        timer_jobs_state_file.ua_file.path,
        CLOUD_BUILD_INFO,
        *(
            entitlement.repo_list_file_tmpl.format(name=entitlement.name)
            for entitlement in entitlements.ENTITLEMENT_CLASSES
            if issubclass(entitlement, entitlements.repo.RepoEntitlement)
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
        "pro status --format json", "{}/ua-status.json".format(output_dir)
    )
    _write_command_output_to_file(
        "{} status".format(LIVEPATCH_CMD),
        "{}/livepatch-status.txt".format(output_dir),
    )
    _write_command_output_to_file(
        "systemctl list-timers --all",
        "{}/systemd-timers.txt".format(output_dir),
    )
    _write_command_output_to_file(
        (
            "journalctl --boot=0 -o short-precise "
            "{} "
            "-u cloud-init-local.service "
            "-u cloud-init-config.service -u cloud-config.service"
        ).format(
            " ".join(
                ["-u {}".format(s) for s in UA_SERVICES if ".service" in s]
            )
        ),
        "{}/journalctl.txt".format(output_dir),
    )

    for service in UA_SERVICES:
        _write_command_output_to_file(
            "systemctl status {}".format(service),
            "{}/{}.txt".format(output_dir, service),
            return_codes=[0, 3],
        )

    state_files = _get_state_files(cfg)

    # also get default logrotated log files
    for f in state_files + glob.glob(DEFAULT_LOG_PREFIX + "*"):
        if os.path.isfile(f):
            try:
                content = system.load_file(f)
            except Exception as e:
                # If we fail to load that file for any reason we will
                # not break the command, we will instead warn the user
                # about the issue and try to process the other files
                logging.warning("Failed to load file: %s\n%s", f, str(e))
                continue
            content = util.redact_sensitive_logs(content)
            if os.getuid() == 0:
                # if root, overwrite the original with redacted content
                system.write_file(f, content)
            system.write_file(
                os.path.join(output_dir, os.path.basename(f)), content
            )


def get_cloud_instance(
    cfg: config.UAConfig,
) -> AutoAttachCloudInstance:
    instance = None  # type: Optional[AutoAttachCloudInstance]
    try:
        instance = identity.cloud_instance_factory()
    except exceptions.CloudFactoryError as e:
        if isinstance(e, exceptions.CloudFactoryNoCloudError):
            raise exceptions.UserFacingError(
                messages.UNABLE_TO_DETERMINE_CLOUD_TYPE,
                msg_code="auto-attach-cloud-type-error",
            )
        if isinstance(e, exceptions.CloudFactoryNonViableCloudError):
            raise exceptions.UserFacingError(messages.UNSUPPORTED_AUTO_ATTACH)
        if isinstance(e, exceptions.CloudFactoryUnsupportedCloudError):
            raise exceptions.NonAutoAttachImageError(
                messages.UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
                    cloud_type=e.cloud_type
                ),
                msg_code="auto-attach-unsupported-cloud-type-error",
            )
        # we shouldn't get here, but this is a reasonable default just in case
        raise exceptions.UserFacingError(
            messages.UNABLE_TO_DETERMINE_CLOUD_TYPE
        )

    if not instance:
        # we shouldn't get here, but this is a reasonable default just in case
        raise exceptions.UserFacingError(
            messages.UNABLE_TO_DETERMINE_CLOUD_TYPE
        )
    return instance
