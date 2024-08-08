from typing import List, Optional, Tuple

from uaclient import actions, contract, event_logger, lock, messages, util
from uaclient.api import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.clouds import identity
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.entitlements import order_entitlements_for_enabling
from uaclient.entitlements.entitlement_status import CanEnableFailure
from uaclient.files import machine_token

event = event_logger.get_event_logger()


class FullAutoAttachOptions(DataObject):
    fields = [
        Field(
            "enable",
            data_list(StringDataValue),
            False,
            doc="Optional list of services to enable after auto-attaching.",
        ),
        Field(
            "enable_beta",
            data_list(StringDataValue),
            False,
            doc=(
                "Optional list of beta services to enable after"
                " auto-attaching."
            ),
        ),
        Field(
            "cloud_override",
            StringDataValue,
            False,
            doc=(
                "Ignore the result of ``cloud-id`` and act as if running on"
                " this cloud."
            ),
        ),
    ]

    def __init__(
        self,
        enable: Optional[List[str]] = None,
        enable_beta: Optional[List[str]] = None,
        cloud_override: Optional[str] = None,
    ):
        self.enable = enable
        self.enable_beta = enable_beta
        self.cloud_override = cloud_override


class FullAutoAttachResult(DataObject, AdditionalInfo):
    pass


def _enable_services_by_name(
    cfg: UAConfig, services: List[str]
) -> List[Tuple[str, messages.NamedMessage]]:
    failed_services = []
    for name in order_entitlements_for_enabling(cfg, services):
        try:
            ent_ret, reason = actions.enable_entitlement_by_name(cfg, name)
        except exceptions.UbuntuProError as e:
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
    return _full_auto_attach(options, UAConfig())


def _full_auto_attach(
    options: FullAutoAttachOptions,
    cfg: UAConfig,
    *,
    mode: event_logger.EventLoggerMode = event_logger.EventLoggerMode.JSON
) -> FullAutoAttachResult:
    """
    This endpoint runs the whole auto-attach process on the system.
    """
    try:
        with lock.RetryLock(
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
    machine_token_file = machine_token.get_machine_token_file(cfg)

    if _is_attached(cfg).is_attached:
        raise exceptions.AlreadyAttachedError(
            account_name=machine_token_file.account.get("name", "")
        )

    if util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.disable_auto_attach"
    ):
        raise exceptions.AutoAttachDisabledError()

    instance = identity.cloud_instance_factory(
        cloud_override=options.cloud_override
    )
    enable_default_services = (
        options.enable is None and options.enable_beta is None
    )
    actions.auto_attach(cfg, instance, allow_enable=enable_default_services)

    failed = []
    if options.enable is not None:
        failed += _enable_services_by_name(cfg, options.enable)
    if options.enable_beta is not None:
        failed += _enable_services_by_name(cfg, options.enable_beta)

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    if len(failed) > 0:
        raise exceptions.EntitlementsNotEnabledError(failed)

    return FullAutoAttachResult()


endpoint = APIEndpoint(
    version="v1",
    name="FullAutoAttach",
    fn=_full_auto_attach,
    options_cls=FullAutoAttachOptions,
)

_doc = {
    "introduced_in": "27.11",
    "requires_network": True,
    "extra_args_content": """
.. note::

    If none of the lists are set, the services will be enabled based on the
    contract definitions.
""",
    "example_python": """
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import full_auto_attach, FullAutoAttachOptions

options = FullAutoAttachOptions(enable=["<service1>", "<service2>"], enable_beta=["<beta_service3>"])
result = full_auto_attach(options)
""",  # noqa: E501
    "result_class": FullAutoAttachResult,
    "exceptions": [
        (
            exceptions.AlreadyAttachedError,
            (
                "Raised if running on a machine which is already attached to a"
                " Pro subscription."
            ),
        ),
        (
            exceptions.AutoAttachDisabledError,
            "Raised if ``disable_auto_attach: true`` in ``uaclient.conf``.",
        ),
        (
            exceptions.ConnectivityError,
            (
                "Raised if it is not possible to connect to the contracts"
                " service."
            ),
        ),
        (
            exceptions.ContractAPIError,
            (
                "Raised if there is an unexpected error in the contracts"
                " service interaction."
            ),
        ),
        (
            exceptions.EntitlementsNotEnabledError,
            (
                "Raised if the Client fails to enable any of the entitlements"
                " (whether present in any of the lists or listed in the"
                " contract)."
            ),
        ),
        (
            exceptions.LockHeldError,
            (
                "Raised if another Client process is holding the lock on the"
                " machine."
            ),
        ),
        (
            exceptions.NonAutoAttachImageError,
            (
                "Raised if the cloud where the system is running does not"
                " support auto-attach."
            ),
        ),
    ],
    "example_cli": 'pro api u.pro.attach.auto.full_auto_attach.v1 --data {"enable": ["esm-infra", "esm-apps"]}',  # noqa: E501
    "example_json": """
{}
""",
}
