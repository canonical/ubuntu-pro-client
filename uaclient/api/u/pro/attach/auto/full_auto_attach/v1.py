from typing import List, Optional, Tuple, Type  # noqa: F401

from uaclient import actions, entitlements, event_logger
from uaclient.api import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.clouds import AutoAttachCloudInstance  # noqa: F401
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.entitlements.base import UAEntitlement  # noqa: F401
from uaclient.entitlements.entitlement_status import CanEnableFailure

event = event_logger.get_event_logger()


class FullAutoAttachOptions(DataObject):
    fields = [
        Field("enable", data_list(StringDataValue), False),
        Field("enable_beta", data_list(StringDataValue), False),
    ]

    def __init__(
        self,
        enable: Optional[List[str]] = None,
        enable_beta: Optional[List[str]] = None,
    ):
        self.enable = enable
        self.enable_beta = enable_beta


class FullAutoAttachResult(DataObject, AdditionalInfo):
    pass


def _is_any_beta(cfg: UAConfig, ents: List[str]) -> Tuple[bool, str]:
    for name in ents:
        try:
            ent_cls = entitlements.entitlement_factory(cfg, name)
            if ent_cls.is_beta:
                return True, name
        except exceptions.EntitlementNotFoundError:
            continue
    return False, ""


def _is_incompatible_services_present(
    cfg, ent_list: List[str]
) -> Tuple[bool, str, List[str]]:
    ent_cls = list()  # type: List[Type[UAEntitlement]]
    for e in ent_list:
        ent_cls.append(entitlements.entitlement_factory(cfg, e))

    for ent in ent_cls:
        ent_inst = ent(cfg)
        if ent_inst.incompatible_services:
            incompat = [
                service.entitlement
                for service in ent_inst.incompatible_services
            ]
            if any(e in incompat for e in ent_cls):
                return True, ent_inst.name, [e(cfg).name for e in incompat]
    return False, "", []


def full_auto_attach(options: FullAutoAttachOptions) -> FullAutoAttachResult:
    return _full_auto_attach(options, UAConfig(root_mode=True))


def _full_auto_attach(options: FullAutoAttachOptions, cfg: UAConfig):
    event.set_event_mode(event_logger.EventLoggerMode.JSON)

    services = set()
    if options.enable:
        is_beta_found, service = _is_any_beta(cfg, options.enable)
        if is_beta_found:
            raise exceptions.BetaServiceError(
                msg="beta service found in the enable list",
                msg_code="beta-service-found",
                additional_info={"beta_service": service},
            )
        services.update(options.enable)
    if options.enable_beta:
        services.update(options.enable_beta)

    service_list = list(services)

    found, not_found = entitlements.get_valid_entitlement_names(
        service_list, cfg
    )
    if not_found:
        msg = entitlements.create_enable_entitlements_not_found_message(
            not_found, cfg=cfg, allow_beta=True
        )
        raise exceptions.EntitlementNotFoundError(msg.msg, not_found)

    incompat_detected, ent, incompat_ents = _is_incompatible_services_present(
        cfg, sorted(found)
    )  # sort for easy testing exceptions raised
    if incompat_detected:
        err_msg = "{ent} is incompatible with any of these services {incompat}"
        raise exceptions.IncompatibleEntitlementsDetected(
            msg=err_msg.format(ent=ent, incompat=incompat_ents),
            msg_code="incompatible-services-detected",
            additional_info={
                "service": ent,
                "incompatible_services": ",".join(incompat_ents),
            },
        )

    instance = actions.get_cloud_instance(cfg)
    enable_default_services = (
        options.enable is None and options.enable_beta is None
    )
    actions.auto_attach(cfg, instance, enable_default_services)

    if enable_default_services:
        return FullAutoAttachResult()

    for name in found:
        ent_ret, reason = actions.enable_entitlement_by_name(
            cfg, name, assume_yes=True, allow_beta=True
        )
        if not ent_ret:
            if (
                reason is not None
                and isinstance(reason, CanEnableFailure)
                and reason.message is not None
            ):
                raise exceptions.EntitlementNotEnabledError(
                    msg=reason.message.msg,
                    msg_code=reason.message.name,
                    additional_info={"service": name},
                )
            else:
                raise exceptions.EntitlementNotEnabledError(
                    msg="Failed to enable service: {}".format(name),
                    msg_code="entitlement-not-enabled",
                    additional_info={"service": name},
                )

    return FullAutoAttachResult()


endpoint = APIEndpoint(
    version="v1",
    name="FullAutoAttach",
    fn=_full_auto_attach,
    options_cls=FullAutoAttachOptions,
)
