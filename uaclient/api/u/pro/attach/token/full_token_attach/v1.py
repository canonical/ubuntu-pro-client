from typing import Dict, List  # noqa: F401

from uaclient import exceptions, lock, util
from uaclient.actions import attach_with_token
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo, ErrorWarningObject
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)


class FullTokenAttachOptions(DataObject):
    fields = [
        Field("token", StringDataValue),
        Field("auto_enable_services", BoolDataValue, False),
    ]

    def __init__(self, token: str, auto_enable_services: bool = True):
        self.token = token
        self.auto_enable_services = auto_enable_services


class FullTokenAttachResult(DataObject, AdditionalInfo):
    fields = [
        Field("enabled", data_list(StringDataValue)),
        Field("reboot_required", BoolDataValue),
    ]

    def __init__(
        self,
        enabled: List[str],
        reboot_required: bool,
    ):
        self.enabled = enabled
        self.reboot_required = reboot_required


def _full_token_attach(
    options: FullTokenAttachOptions, cfg: UAConfig
) -> FullTokenAttachResult:
    if not util.we_are_currently_root():
        raise exceptions.NonRootUserError

    if _is_attached(cfg).is_attached:
        return FullTokenAttachResult(
            enabled=[],
            reboot_required=False,
        )

    try:
        with lock.RetryLock(
            lock_holder="pro.api.u.pro.attach.token.full_token_attach.v1",
        ):
            ret = _full_token_attach_in_lock(options, cfg)
    except Exception as e:
        lock.clear_lock_file_if_present()
        raise e
    return ret


def _full_token_attach_in_lock(
    options: FullTokenAttachOptions, cfg: UAConfig
) -> FullTokenAttachResult:
    failed_services = []  # type: List[Dict[str, str]]

    auto_enable_services = options.auto_enable_services
    if auto_enable_services is None:
        auto_enable_services = True

    try:
        attach_with_token(
            cfg,
            options.token,
            allow_enable=auto_enable_services,
            silent=True,
        )
    except (
        exceptions.AttachFailureUnknownError,
        exceptions.AttachFailureDefaultServices,
    ) as exc:
        failed_services = exc.additional_info.get("services", [])

    enabled_services = [
        service.name for service in _enabled_services(cfg).enabled_services
    ]
    reboot_required_result = _reboot_required(cfg)

    result = FullTokenAttachResult(
        enabled=enabled_services,
        reboot_required=reboot_required_result.reboot_required == "yes",
    )

    if failed_services:
        result.warnings = [
            ErrorWarningObject(
                title=service["title"],
                code=service["code"],
                meta={"service": service["name"]},
            )
            for service in failed_services
        ]

    return result


def full_token_attach(
    options: FullTokenAttachOptions,
) -> FullTokenAttachResult:
    return _full_token_attach(options, UAConfig())


endpoint = APIEndpoint(
    version="v1",
    name="FullTokenAttach",
    fn=_full_token_attach,
    options_cls=FullTokenAttachOptions,
)
