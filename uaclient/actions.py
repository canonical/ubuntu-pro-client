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
from uaclient.clouds import identity
from uaclient.defaults import (
    CLOUD_BUILD_INFO,
    DEFAULT_CONFIG_FILE,
    DEFAULT_LOG_PREFIX,
)
from uaclient.entitlements.livepatch import LIVEPATCH_CMD

LOG = logging.getLogger("ua.actions")
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
    cfg: config.UAConfig, cloud: clouds.AutoAttachCloudInstance
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
    try:
        tokenResponse = contract_client.request_auto_attach_contract_token(
            instance=cloud
        )
    except exceptions.ContractAPIError as e:
        if e.code and 400 <= e.code < 500:
            raise exceptions.NonAutoAttachImageError(
                messages.UNSUPPORTED_AUTO_ATTACH
            )
        raise e

    token = tokenResponse["contractToken"]

    attach_with_token(cfg, token=token, allow_enable=True)


def enable_entitlement_by_name(
    cfg: config.UAConfig,
    name: str,
    *,
    assume_yes: bool = False,
    allow_beta: bool = False
):
    """
    Constructs an entitlement based on the name provided. Passes kwargs onto
    the entitlement constructor.
    :raise EntitlementNotFoundError: If no entitlement with the given name is
        found, then raises this error.
    """
    ent_cls = entitlements.entitlement_factory(cfg=cfg, name=name)
    entitlement = ent_cls(
        cfg, assume_yes=assume_yes, allow_beta=allow_beta, called_name=name
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
    cmd, filename: str, return_codes: List[int] = None
) -> None:
    """Helper which runs a command and writes output or error to filename."""
    try:
        out, _ = system.subp(cmd.split(), rcs=return_codes)
    except exceptions.ProcessExecutionError as e:
        system.write_file("{}-error".format(filename), str(e))
    else:
        system.write_file(filename, out)


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

    # include cfg log files here because they could be set to non default
    state_files = [
        cfg.cfg_path or DEFAULT_CONFIG_FILE,
        cfg.log_file,
        cfg.timer_log_file,
        cfg.daemon_log_file,
        cfg.data_path("jobs-status"),
        CLOUD_BUILD_INFO,
        *(
            entitlement.repo_list_file_tmpl.format(name=entitlement.name)
            for entitlement in entitlements.ENTITLEMENT_CLASSES
            if issubclass(entitlement, entitlements.repo.RepoEntitlement)
        ),
    ]

    # also get default logrotated log files
    for f in state_files + glob.glob(DEFAULT_LOG_PREFIX + "*"):
        if os.path.isfile(f):
            try:
                content = system.load_file(f)
            except PermissionError as e:
                logging.warning(e)
            content = util.redact_sensitive_logs(content)
            if os.getuid() == 0:
                # if root, overwrite the original with redacted content
                system.write_file(f, content)
            system.write_file(
                os.path.join(output_dir, os.path.basename(f)), content
            )
