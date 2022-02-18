import logging
import sys
from typing import Optional  # noqa: F401

from uaclient import (
    clouds,
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    messages,
)
from uaclient.clouds import identity

LOG = logging.getLogger("ua.actions")
event = event_logger.get_event_logger()


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
        cfg.status()  # Persist updated status in the event of partial attach
        update_apt_and_motd_messages(cfg)
        raise exc
    except exceptions.UserFacingError as exc:
        event.info(exc.msg, file_type=sys.stderr)
        cfg.status()  # Persist updated status in the event of partial attach
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
    ent_cls = entitlements.entitlement_factory(name)
    entitlement = ent_cls(
        cfg, assume_yes=assume_yes, allow_beta=allow_beta, called_name=name
    )
    return entitlement.enable()


def status(
    cfg: config.UAConfig,
    *,
    simulate_with_token: Optional[str] = None,
    show_beta: bool = False
):
    """
    Construct the current UA status dictionary.
    """
    if simulate_with_token:
        status, ret = cfg.simulate_status(
            token=simulate_with_token, show_beta=show_beta
        )
    else:
        status = cfg.status(show_beta=show_beta)
        ret = 0

    return status, ret
