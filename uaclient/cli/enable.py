import json
import logging
from typing import Optional

from uaclient import (
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    lock,
    messages,
    status,
    util,
)
from uaclient.api import AbstractProgress, ProgressWrapper
from uaclient.api.u.pro.services.dependencies.v1 import _dependencies
from uaclient.api.u.pro.services.enable.v1 import (
    EnableOptions,
    EnableResult,
    _enable,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.cli import cli_constants as cli_constants
from uaclient.cli import cli_util

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def _enable_landscape(
    cfg: config.UAConfig,
    args,
    progress_object: Optional[AbstractProgress] = None,
):
    """
    Landscape gets special treatment because it currently not supported by our
    enable API. This function is a temporary workaround until we have a proper
    API for enabling landscape, which will happen after Landscape is fully
    integrated with the contracts backend.
    """
    progress = ProgressWrapper(progress_object)
    landscape = entitlements.LandscapeEntitlement(
        cfg,
        assume_yes=args.assume_yes,
        allow_beta=args.beta,
        called_name="landscape",
        access_only=args.access_only,
        extra_args=args.extra_args,
    )
    success = False
    fail_reason = None

    try:
        with lock.SpinLock(
            cfg=cfg,
            lock_holder="u.pro.services.enable.v1",
        ):
            success, fail_reason = landscape.enable(progress=progress)
    except Exception as e:
        lock.clear_lock_file_if_present()
        raise e

    if not success:
        if fail_reason is not None and fail_reason.message is not None:
            reason = fail_reason.message
        else:
            reason = messages.GENERIC_UNKNOWN_ISSUE
        raise exceptions.EntitlementNotEnabledError(
            service="landscape", reason=reason
        )
    return EnableResult(
        enabled=["landscape"], disabled=[], reboot_required=False, messages=[]
    )


def action_enable_json(args, *, cfg) -> int:
    processed_services = []
    failed_services = []
    errors = []
    warnings = []

    response = {
        "_schema_version": event_logger.JSON_SCHEMA_VERSION,
        "result": "success",
        "needs_reboot": False,
    }

    try:
        contract.refresh(cfg)
    except exceptions.UbuntuProError:
        # Inability to refresh is not a critical issue during enable
        warnings.append(
            {
                "type": "system",
                "message": messages.E_REFRESH_CONTRACT_FAILURE.msg,
                "message_code": messages.E_REFRESH_CONTRACT_FAILURE.name,
            }
        )

    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(args.service, cfg)
    enabled_service_names = [
        s.name for s in _enabled_services(cfg).enabled_services
    ]
    entitlements_already_enabled = set(enabled_service_names).intersection(
        set(entitlements_found)
    )
    entitlements_to_enable = (
        set(entitlements_found) - entitlements_already_enabled
    )

    result = True
    for ent_name in entitlements.order_entitlements_for_enabling(
        cfg, list(entitlements_to_enable)
    ):
        try:
            if ent_name == "landscape":
                enable_result = _enable_landscape(cfg, args)
            else:
                enable_result = _enable(
                    EnableOptions(
                        service=ent_name,
                        variant=args.variant,
                        access_only=args.access_only,
                    ),
                    cfg,
                )
            processed_services.append(ent_name)
            if enable_result.reboot_required:
                response["needs_reboot"] = True
        except exceptions.UbuntuProError as e:
            failed_services.append(ent_name)
            errors.append(
                {
                    "type": "service",
                    "service": ent_name,
                    "message": e.msg,
                    "message_code": e.msg_code,
                }
            )
            result = False

    for ent_name in entitlements_already_enabled:
        failed_services.append(ent_name)
        msg = messages.ALREADY_ENABLED.format(title=ent_name)
        errors.append(
            {
                "type": "service",
                "service": ent_name,
                "message": msg.msg,
                "message_code": msg.name,
            }
        )
        result = False

    for ent_name in entitlements_not_found:
        failed_services.append(ent_name)
        msg = messages.E_INVALID_SERVICE_OP_FAILURE.format(
            operation="enable",
            invalid_service=ent_name,
            service_msg="",
        )
        errors.append(
            {
                "type": "service",
                "service": ent_name,
                "message": msg.msg,
                "message_code": msg.name,
            }
        )
        result = False

    processed_services.sort()
    failed_services.sort()

    response["result"] = "success" if result else "failure"
    response["processed_services"] = processed_services
    response["failed_services"] = failed_services
    response["errors"] = errors
    response["warnings"] = warnings
    print(
        json.dumps(response, cls=util.DatetimeAwareJSONEncoder, sort_keys=True)
    )
    return 0 if result else 1


class CLIEnableProgress(AbstractProgress):
    def __init__(self, messaging):
        self.messaging = messaging

    def progress(
        self,
        *,
        total_steps: int,
        done_steps: int,
        previous_step_message: Optional[str],
        current_step_message: Optional[str]
    ):
        if current_step_message is not None:
            print(current_step_message)

    def _on_event(self, event: str, payload):
        if event == "info":
            print(payload)
            return
        # otherwise, we assume it's a messaging hook
        if not util.handle_message_operations(
            self.messaging.get(event, None), print
        ):
            raise exceptions.PromptDeniedError()


def prompt_for_dependency_handling(
    cfg, service, all_dependencies, enabled_service_names, called_name
):
    incompatible_services = []
    required_services = []

    dependencies = next(
        (s for s in all_dependencies if s.name == service), None
    )
    if dependencies is not None:
        incompatible_services = [
            s.name
            for s in dependencies.incompatible_with
            if s.name in enabled_service_names
        ]
        required_services = [
            s.name
            for s in dependencies.depends_on
            if s.name not in enabled_service_names
        ]

    for incompatible_service in incompatible_services:
        cfg_block_disable_on_enable = util.is_config_value_true(
            config=cfg.cfg,
            path_to_value="features.block_disable_on_enable",
        )
        user_msg = messages.INCOMPATIBLE_SERVICE.format(
            service_being_enabled=called_name,
            incompatible_service=incompatible_service,
        )
        if cfg_block_disable_on_enable or not util.prompt_for_confirmation(
            msg=user_msg
        ):
            raise exceptions.IncompatibleServiceStopsEnable(
                service_being_enabled=called_name,
                incompatible_service=incompatible_service,
            )

    for required_service in required_services:
        user_msg = messages.REQUIRED_SERVICE.format(
            service_being_enabled=service,
            required_service=required_service,
        )
        if not util.prompt_for_confirmation(msg=user_msg):
            raise exceptions.RequiredServiceStopsEnable(
                service_being_enabled=service,
                required_service=required_service,
            )


def action_enable_normal(args, *, cfg) -> int:
    print(messages.REFRESH_CONTRACT_ENABLE)
    try:
        contract.refresh(cfg)
    except exceptions.UbuntuProError:
        # Inability to refresh is not a critical issue during enable
        LOG.warning("Failed to refresh contract", exc_info=True)

    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(args.service, cfg)
    enabled_service_names = [
        s.name for s in _enabled_services(cfg).enabled_services
    ]
    entitlements_already_enabled = set(enabled_service_names).intersection(
        set(entitlements_found)
    )
    entitlements_to_enable = (
        set(entitlements_found) - entitlements_already_enabled
    )

    all_dependencies = _dependencies(cfg).services

    reboot_required = False
    result = True
    for ent_name in entitlements.order_entitlements_for_enabling(
        cfg, list(entitlements_to_enable)
    ):
        ent = entitlements.entitlement_factory(
            cfg, ent_name, variant=args.variant
        )(
            cfg,
            assume_yes=args.assume_yes,
            allow_beta=args.beta,
            called_name=ent_name,
        )
        real_name = ent.name
        progress = CLIEnableProgress(ent.messaging)
        try:
            if not args.assume_yes:
                prompt_for_dependency_handling(
                    cfg,
                    real_name,
                    all_dependencies,
                    enabled_service_names,
                    called_name=ent_name,
                )

            if real_name == "landscape":
                enable_result = _enable_landscape(
                    cfg, args, progress_object=progress
                )
            else:
                enable_result = _enable(
                    EnableOptions(
                        service=ent_name,
                        variant=args.variant,
                        access_only=args.access_only,
                    ),
                    cfg,
                    progress_object=progress,
                )
            reboot_required = reboot_required or enable_result.reboot_required
            if args.access_only:
                print(messages.ACCESS_ENABLED_TMPL.format(title=ent.title))
            else:
                print(messages.ENABLED_TMPL.format(title=ent.title))
        except exceptions.UbuntuProError as e:
            LOG.exception(e)
            print(e.msg)
            print(messages.ENABLE_FAILED.format(title=ent.title))
            result = False

    for ent_name in entitlements_already_enabled:
        LOG.error(
            "User requested to enable %s, but it is already enabled", ent_name
        )
        print(messages.ALREADY_ENABLED.format(title=ent.title).msg)
        result = False

    for ent_name in entitlements_not_found:
        LOG.error(
            "User requested to enable %s, but it is not a valid service",
            ent_name,
        )
        print(
            messages.E_INVALID_SERVICE_OP_FAILURE.format(
                operation="enable", invalid_service=ent.title, service_msg=""
            )
        )
        result = False

    return 0 if result else 1


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached(cli_util._raise_enable_disable_unattached_error)
def action_enable(args, *, cfg, **kwargs) -> int:
    """Perform the enable action on a named entitlements.

    @return: 0 on success, 1 otherwise
    """

    if args.variant and args.access_only:
        raise exceptions.InvalidOptionCombination(
            option1="--access-only", option2="--variant"
        )

    if args.variant and len(args.service) > 1:
        raise exceptions.InvalidOptionCombination(
            option1=args.service, option2="--variant"
        )

    try:
        if args.format == "json":
            ret = action_enable_json(args, cfg=cfg)
        else:
            ret = action_enable_normal(args, cfg=cfg)
    finally:
        status.status(cfg=cfg)  # Update the status cache
        contract_client = contract.UAContractClient(cfg)
        contract_client.update_activity_token()

    return ret


def add_parser(subparsers, cfg: config.UAConfig):
    parser = subparsers.add_parser("enable", help=messages.CLI_ROOT_ENABLE)
    parser.set_defaults(action=action_enable)
    parser.description = messages.CLI_ENABLE_DESC
    parser.usage = cli_constants.USAGE_TMPL.format(
        name=cli_constants.NAME, command="enable <service> [<service>]"
    )
    parser.prog = "enable"
    parser._positionals.title = messages.CLI_ARGS
    parser._optionals.title = messages.CLI_FLAGS
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            messages.CLI_ENABLE_SERVICE.format(
                options=", ".join(entitlements.valid_services(cfg=cfg))
            )
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help=messages.CLI_ASSUME_YES.format(command="enable"),
    )
    parser.add_argument(
        "--access-only",
        action="store_true",
        help=messages.CLI_ENABLE_ACCESS_ONLY,
    )
    parser.add_argument(
        "--beta", action="store_true", help=messages.CLI_ENABLE_BETA
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=messages.CLI_FORMAT_DESC.format(default="cli"),
    )
    parser.add_argument(
        "--variant", action="store", help=messages.CLI_ENABLE_VARIANT
    )
    return parser
