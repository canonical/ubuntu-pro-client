from typing import List

from uaclient import (
    daemon,
    entitlements,
    exceptions,
    lock,
    messages,
    timer,
    util,
)
from uaclient.api import ProgressWrapper
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo, ErrorWarningObject
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)
from uaclient.files import state_files
from uaclient.timer.update_messaging import update_motd_messages


class DetachResult(DataObject, AdditionalInfo):
    fields = [
        Field("disabled", data_list(StringDataValue)),
        Field("reboot_required", BoolDataValue),
    ]

    def __init__(self, disabled: List[str], reboot_required: bool):
        self.disabled = disabled
        self.reboot_required = reboot_required


def detach() -> DetachResult:
    return _detach(UAConfig())


def _detach(cfg: UAConfig) -> DetachResult:
    if not util.we_are_currently_root():
        raise exceptions.NonRootUserError

    try:
        with lock.RetryLock(
            lock_holder="pro.api.u.pro.detach.v1",
        ):
            ret = _detach_in_lock(cfg)
    except Exception as e:
        lock.clear_lock_file_if_present()
        raise e
    return ret


def _detach_in_lock(cfg: UAConfig) -> DetachResult:
    if not _is_attached(cfg).is_attached:
        return DetachResult(
            disabled=[],
            reboot_required=False,
        )

    disabled = []
    warnings = []  # type: List[ErrorWarningObject]
    for ent_name in entitlements.entitlements_disable_order(cfg):
        try:
            ent = entitlements.entitlement_factory(
                cfg=cfg, name=ent_name, assume_yes=True
            )
        except exceptions.EntitlementNotFoundError:
            continue

        # For detach, we should not consider that a service
        # cannot be disabled because of dependent services,
        # since we are going to disable all of them anyway
        can_disable, _ = ent.can_disable(ignore_dependent_services=True)
        if can_disable:
            ret, reason = ent.disable(ProgressWrapper())
            if not ret:
                if reason and reason.message:
                    msg = reason.message.msg
                    code = reason.message.name
                else:
                    msg = messages.DISABLE_FAILED_TMPL.format(title=ent_name)
                    code = ""

                warnings.append(
                    ErrorWarningObject(
                        title=msg,
                        code=code,
                        meta={"service": ent_name},
                    )
                )
            else:
                disabled.append(ent_name)

    state_files.delete_state_files()
    cfg.machine_token_file.delete()
    update_motd_messages(cfg)
    daemon.start()
    timer.stop()

    reboot_required_result = _reboot_required(cfg)

    result = DetachResult(
        disabled=sorted(disabled),
        reboot_required=reboot_required_result.reboot_required == "yes",
    )
    result.warnings = warnings

    return result


endpoint = APIEndpoint(
    version="v1",
    name="Detach",
    fn=_detach,
    options_cls=None,
)
