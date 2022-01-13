import logging

from uaclient import clouds, config, contract, exceptions, status, util
from uaclient.clouds import identity

LOG = logging.getLogger("ua.actions")


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
    except util.UrlError as exc:
        with util.disable_log_to_console():
            LOG.exception(exc)
        cfg.status()  # Persist updated status in the event of partial attach
        update_apt_and_motd_messages(cfg)
        raise exc
    except exceptions.UserFacingError as exc:
        LOG.warning(exc.msg)
        cfg.status()  # Persist updated status in the event of partial attach
        update_apt_and_motd_messages(cfg)
        raise exc

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
    except contract.ContractAPIError as e:
        if e.code and 400 <= e.code < 500:
            raise exceptions.NonAutoAttachImageError(
                status.MESSAGE_UNSUPPORTED_AUTO_ATTACH
            )
        raise e
    current_iid = identity.get_instance_id()
    if current_iid:
        cfg.write_cache("instance-id", current_iid)

    token = tokenResponse["contractToken"]

    attach_with_token(cfg, token=token, allow_enable=True)
