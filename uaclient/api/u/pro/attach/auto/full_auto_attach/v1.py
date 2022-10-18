from typing import List, Optional, Tuple

from uaclient import actions, event_logger, lock, messages, util
from uaclient.api import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.entitlements import order_entitlements_for_enabling
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


def _enable_services_by_name(
    cfg: UAConfig, services: List[str], allow_beta: bool
) -> List[Tuple[str, messages.NamedMessage]]:
    failed_services = []
    for name in order_entitlements_for_enabling(cfg, services):
        try:
            ent_ret, reason = actions.enable_entitlement_by_name(
                cfg, name, assume_yes=True, allow_beta=allow_beta
            )
        except exceptions.UserFacingError as e:
            failed_services.append(
                (name, messages.NamedMessage(e.msg_code or "unknown", e.msg))
            )
            continue
        if not ent_ret:
            if (
                reason is not None
                and isinstance(reason, CanEnableFailure)
                and reason.message is not None
            ):
                failed_services.append((name, reason.message))
            else:
                failed_services.append(
                    (
                        name,
                        messages.NamedMessage("unknown", "failed to enable"),
                    )
                )
    return failed_services


def full_auto_attach(options: FullAutoAttachOptions) -> FullAutoAttachResult:
    return _full_auto_attach(options, UAConfig(root_mode=True))


def _full_auto_attach(
    options: FullAutoAttachOptions,
    cfg: UAConfig,
    *,
    mode: event_logger.EventLoggerMode = event_logger.EventLoggerMode.JSON
) -> FullAutoAttachResult:
    try:
        with lock.SpinLock(
            cfg=cfg,
            lock_holder="pro.api.u.pro.attach.auto.full_auto_attach.v1",
        ):
            ret = _full_auto_attach_in_lock(options, cfg, mode=mode)
    except Exception as e:
        lock.clear_lock_file_if_present()
        raise e
    return ret


def _full_auto_attach_in_lock(
    options: FullAutoAttachOptions,
    cfg: UAConfig,
    mode: event_logger.EventLoggerMode,
) -> FullAutoAttachResult:
    event.set_event_mode(mode)

    if cfg.is_attached:
        raise exceptions.AlreadyAttachedError(
            cfg.machine_token_file.account.get("name", "")
        )

    if util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.disable_auto_attach"
    ):
        raise exceptions.AutoAttachDisabledError()

    instance = actions.get_cloud_instance(cfg)
    enable_default_services = (
        options.enable is None and options.enable_beta is None
    )
    actions.auto_attach(cfg, instance, allow_enable=enable_default_services)

    failed = []
    if options.enable is not None:
        failed += _enable_services_by_name(
            cfg, options.enable, allow_beta=False
        )
    if options.enable_beta is not None:
        failed += _enable_services_by_name(
            cfg, options.enable_beta, allow_beta=True
        )

    if len(failed) > 0:
        raise exceptions.EntitlementsNotEnabledError(failed)

    return FullAutoAttachResult()


endpoint = APIEndpoint(
    version="v1",
    name="FullAutoAttach",
    fn=_full_auto_attach,
    options_cls=FullAutoAttachOptions,
)
