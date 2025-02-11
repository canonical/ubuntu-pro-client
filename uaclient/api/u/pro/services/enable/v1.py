import logging
from typing import Iterable, List, Optional, Tuple, Type

from uaclient import entitlements, lock, messages, status, util
from uaclient.api import AbstractProgress, ProgressWrapper, exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo, ErrorWarningObject
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

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class EnableOptions(DataObject):
    fields = [
        Field("service", StringDataValue, doc="Pro service to be enabled"),
        Field(
            "variant",
            StringDataValue,
            False,
            doc="Optional variant of the Pro service to be enabled.",
        ),
        Field(
            "access_only",
            BoolDataValue,
            False,
            doc=(
                "If true and the target service supports it, only enable"
                " access to the service (default: false)"
            ),
        ),
    ]

    def __init__(
        self,
        *,
        service: str,
        variant: Optional[str] = None,
        access_only: bool = False
    ):
        self.service = service
        self.variant = variant
        self.access_only = access_only


class EnableResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "enabled",
            data_list(StringDataValue),
            doc="List of services that were enabled.",
        ),
        Field(
            "disabled",
            data_list(StringDataValue),
            doc="List of services that were disabled.",
        ),
        Field(
            "reboot_required",
            BoolDataValue,
            doc=(
                "True if one of the services that was enabled requires a"
                " reboot."
            ),
        ),
        Field(
            "messages",
            data_list(StringDataValue),
            doc=(
                "List of information message strings about the service that"
                " was just enabled. Possibly translated."
            ),
        ),
    ]

    def __init__(
        self,
        *,
        enabled: List[str],
        disabled: List[str],
        reboot_required: bool,
        messages: List[str]
    ):
        self.enabled = enabled
        self.disabled = disabled
        self.reboot_required = reboot_required
        self.messages = messages


def _auto_select_variant(
    cfg: UAConfig,
    progress: ProgressWrapper,
    entitlement: entitlements.UAEntitlement,
    available_variants: Iterable[Type[entitlements.UAEntitlement]],
    access_only: bool,
) -> Tuple[entitlements.UAEntitlement, Optional[ErrorWarningObject]]:
    variant = None
    for v_cls in available_variants:
        v = v_cls(cfg=cfg, access_only=access_only)
        if (
            v.applicability_status()[0]
            == entitlements.ApplicabilityStatus.APPLICABLE
            and v.variant_auto_select()
        ):
            variant = v
            break
    if variant is None and entitlement.default_variant is not None:
        variant = entitlement.default_variant(cfg=cfg, access_only=access_only)
    if variant is not None:
        progress.emit(
            "message_operation",
            [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.AUTO_SELECTING_VARIANT.format(
                            variant=messages.TxtColor.BOLD
                            + variant.variant_name
                            + messages.TxtColor.ENDC
                        ),
                    },
                )
            ],
        )
        warning = messages.AUTO_SELECTED_VARIANT_WARNING.format(
            variant_name=variant.variant_name
        )
        return variant, ErrorWarningObject(
            title=warning.msg,
            code=warning.name,
            meta={"variant_name": variant.variant_name},
        )
    else:
        return entitlement, None


def _enabled_services_names(cfg: UAConfig) -> List[str]:
    return [s.name for s in _enabled_services(cfg).enabled_services]


def enable(
    options: EnableOptions, progress_object: Optional[AbstractProgress] = None
) -> EnableResult:
    return _enable(options, UAConfig(), progress_object=progress_object)


def _enable(
    options: EnableOptions,
    cfg: UAConfig,
    progress_object: Optional[AbstractProgress] = None,
) -> EnableResult:
    """
    Enable a Pro service. This will automatically disable incompatible services
    and enable required services that that target service depends on.
    """
    progress = ProgressWrapper(progress_object)
    warnings = []

    if not util.we_are_currently_root():
        raise exceptions.NonRootUserError()

    if not _is_attached(cfg).is_attached:
        raise exceptions.UnattachedError()

    if options.service == "landscape":
        raise exceptions.NotSupported()

    enabled_services_before = _enabled_services_names(cfg)

    already_enabled = next(
        (
            s
            for s in _enabled_services(cfg).enabled_services
            if s.name == options.service
            and (
                not options.variant
                or (s.variant_enabled and s.variant_name == options.variant)
            )
        ),
        None,
    )
    if already_enabled:
        # nothing to do
        return EnableResult(
            enabled=[],
            disabled=[],
            reboot_required=False,
            messages=[],
        )

    entitlement = entitlements.entitlement_factory(
        cfg=cfg,
        name=options.service,
        variant=options.variant or "",
        access_only=options.access_only,
    )

    applicability, _ = entitlement.applicability_status()
    available_variants = entitlement.variants
    if all(
        [
            applicability == entitlements.ApplicabilityStatus.APPLICABLE,
            not entitlement.is_variant,
            available_variants,
        ]
    ):
        entitlement, auto_select_warning = _auto_select_variant(
            cfg=cfg,
            progress=progress,
            entitlement=entitlement,
            available_variants=available_variants.values(),
            access_only=options.access_only,
        )
        if auto_select_warning:
            warnings.append(auto_select_warning)

    progress.total_steps = entitlement.calculate_total_enable_steps()

    success = False
    fail_reason = None

    try:
        with lock.RetryLock(
            lock_holder="u.pro.services.enable.v1",
        ):
            success, fail_reason = entitlement.enable(progress)
    except Exception as e:
        lock.clear_lock_file_if_present()
        raise e

    if not success:
        if fail_reason is not None and fail_reason.message is not None:
            reason = fail_reason.message
        else:
            reason = messages.GENERIC_UNKNOWN_ISSUE
        raise exceptions.EntitlementNotEnabledError(
            service=options.service, reason=reason
        )

    enabled_services_after = _enabled_services_names(cfg)

    post_enable_messages = [
        msg
        for msg in (entitlement.messaging.get("post_enable", []) or [])
        if isinstance(msg, str)
    ]

    status.status(cfg=cfg)  # Update the status cache
    progress.finish()

    result = EnableResult(
        enabled=sorted(
            list(
                set(enabled_services_after).difference(
                    set(enabled_services_before)
                )
            )
        ),
        disabled=sorted(
            list(
                set(enabled_services_before).difference(
                    set(enabled_services_after)
                )
            )
        ),
        reboot_required=entitlement._check_for_reboot(),
        messages=post_enable_messages,
    )
    result.warnings = warnings
    return result


endpoint = APIEndpoint(
    version="v1",
    name="EnableService",
    fn=_enable,
    options_cls=EnableOptions,
    supports_progress=True,
)

_doc = {
    "introduced_in": "32",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.services.enable.v1 import enable, EnableOptions
result = enable(EnableOptions(service="usg"))
""",
    "result_class": EnableResult,
    "exceptions": [
        (exceptions.NonRootUserError, "When called as non-root user"),
        (
            exceptions.UnattachedError,
            (
                "When called on a machine that is not attached to a Pro"
                " subscription"
            ),
        ),
        (
            exceptions.NotSupported,
            (
                "When called for a service that doesn't support being enabled"
                " via API (currently only Landscape)"
            ),
        ),
        (
            exceptions.EntitlementNotFoundError,
            (
                "When the service argument is not a valid Pro service name or"
                " if the variant is not a valid variant of the target service"
            ),
        ),
        (
            exceptions.LockHeldError,
            "When another Ubuntu Pro related operation is in progress",
        ),
        (
            exceptions.EntitlementNotEnabledError,
            "When the service fails to enable",
        ),
    ],
    "example_cli": "pro api u.pro.services.enable.v1 --args service=usg",
    "example_json": """
{
    "disabled": [],
    "enabled": [
        "usg"
    ],
    "messages": [],
    "reboot_required": false
}
""",
}
