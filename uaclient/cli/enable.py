import json
import logging
from typing import Any, Dict, List, NamedTuple, Optional

from uaclient import (
    api,
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
from uaclient.api.u.pro.services.dependencies.v1 import (
    ServiceWithDependencies,
    _dependencies,
)
from uaclient.api.u.pro.services.enable.v1 import (
    EnableOptions,
    EnableResult,
    _enable,
)
from uaclient.api.u.pro.status.enabled_services.v1 import (
    EnabledService,
    _enabled_services,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

_EnableOneServiceResult = NamedTuple(
    "_EnableOneServiceResult",
    [
        ("success", bool),
        ("needs_reboot", bool),
        ("error", Optional[Dict[str, Any]]),
    ],
)


def _enable_landscape(
    cfg: config.UAConfig,
    access_only: bool,
    extra_args,
    progress_object: Optional[api.AbstractProgress] = None,
):
    """
    Landscape gets special treatment because it currently not supported by our
    enable API. This function is a temporary workaround until we have a proper
    API for enabling landscape, which will happen after Landscape is fully
    integrated with the contracts backend.
    """
    progress = api.ProgressWrapper(progress_object)
    landscape = entitlements.LandscapeEntitlement(
        cfg,
        called_name="landscape",
        access_only=access_only,
        extra_args=extra_args,
    )
    success = False
    fail_reason = None

    try:
        with lock.RetryLock(
            lock_holder="cli.enable._enable_landscape",
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


def prompt_for_dependency_handling(
    cfg: config.UAConfig,
    service: str,
    all_dependencies: List[ServiceWithDependencies],
    enabled_services: List[EnabledService],
    called_name: str,
    variant: str,
    service_title: str,
):
    incompatible_services = []
    required_services = []
    enabled_service_names = [s.name for s in enabled_services]

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
        incompatible_service_title = entitlements.get_title(
            cfg, incompatible_service
        )
        user_msg = messages.INCOMPATIBLE_SERVICE.format(
            service_being_enabled=service_title,
            incompatible_service=incompatible_service_title,
        )
        if cfg_block_disable_on_enable or not util.prompt_for_confirmation(
            msg=user_msg
        ):
            raise exceptions.IncompatibleServiceStopsEnable(
                service_being_enabled=service_title,
                incompatible_service=incompatible_service_title,
            )

    for required_service in required_services:
        required_service_title = entitlements.get_title(cfg, required_service)
        user_msg = messages.REQUIRED_SERVICE.format(
            service_being_enabled=service_title,
            required_service=required_service_title,
        )
        if not util.prompt_for_confirmation(msg=user_msg):
            raise exceptions.RequiredServiceStopsEnable(
                service_being_enabled=service_title,
                required_service=required_service_title,
            )

    variant_enabled = next(
        (
            s
            for s in enabled_services
            if s.name == service
            and s.variant_enabled
            and s.variant_name != variant
        ),
        None,
    )
    if variant_enabled is not None and variant is not None:
        to_be_enabled_title = entitlements.get_title(cfg, service, variant)
        enabled_variant_title = entitlements.get_title(
            cfg, service, variant_enabled.variant_name
        )
        cfg_block_disable_on_enable = util.is_config_value_true(
            config=cfg.cfg,
            path_to_value="features.block_disable_on_enable",
        )
        user_msg = messages.INCOMPATIBLE_SERVICE.format(
            service_being_enabled=to_be_enabled_title,
            incompatible_service=enabled_variant_title,
        )
        if cfg_block_disable_on_enable or not util.prompt_for_confirmation(
            msg=user_msg
        ):
            raise exceptions.IncompatibleServiceStopsEnable(
                service_being_enabled=to_be_enabled_title,
                incompatible_service=enabled_variant_title,
            )


def _print_json_output(
    json_output: bool,
    json_response: Dict[str, Any],
    processed_services: List[str],
    failed_services: List[str],
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    success: bool,
):
    if json_output:
        processed_services.sort()
        failed_services.sort()

        json_response["result"] = "success" if success else "failure"
        json_response["processed_services"] = processed_services
        json_response["failed_services"] = failed_services
        json_response["errors"] = errors
        json_response["warnings"] = warnings

        print(
            json.dumps(
                json_response,
                cls=util.DatetimeAwareJSONEncoder,
                sort_keys=True,
            )
        )


def _enable_one_service(
    cfg: config.UAConfig,
    ent_name: str,
    variant: str,
    access_only: bool,
    assume_yes: bool,
    json_output: bool,
    extra_args: Optional[List[str]],
    enabled_services: List[EnabledService],
    all_dependencies: List[ServiceWithDependencies],
) -> _EnableOneServiceResult:
    interactive_only_print = cli_util.create_interactive_only_print_function(
        json_output
    )
    ent = entitlements.entitlement_factory(
        cfg,
        ent_name,
        variant=variant,
        access_only=access_only,
        extra_args=extra_args,
    )
    real_name = ent.name
    ent_title = ent.title

    already_enabled = next(
        (
            s
            for s in enabled_services
            if s.name == real_name
            and (
                not variant
                or (s.variant_enabled and s.variant_name == variant)
            )
        ),
        None,
    )
    if already_enabled is not None:
        msg = messages.ALREADY_ENABLED.format(title=ent_title)
        interactive_only_print(msg.msg)
        interactive_only_print(messages.ENABLE_FAILED.format(title=ent_title))
        return _EnableOneServiceResult(
            success=False,
            needs_reboot=False,
            error={
                "type": "service",
                "service": ent_name,
                "message": msg.msg,
                "message_code": msg.name,
            },
        )

    if not assume_yes:
        # this never happens for json output because we assert earlier that
        # assume_yes must be True for json output
        try:
            prompt_for_dependency_handling(
                cfg,
                real_name,
                all_dependencies,
                enabled_services,
                called_name=ent_name,
                variant=variant,
                service_title=ent_title,
            )
        except exceptions.UbuntuProError as e:
            LOG.exception(e)
            interactive_only_print(e.msg)
            interactive_only_print(
                messages.ENABLE_FAILED.format(title=ent_title)
            )
            return _EnableOneServiceResult(
                success=False,
                needs_reboot=False,
                error=None,
            )

    try:
        if json_output:
            progress = None
        else:
            progress = cli_util.CLIEnableDisableProgress(assume_yes=assume_yes)

        if real_name == "landscape":
            enable_result = _enable_landscape(
                cfg,
                access_only,
                extra_args=extra_args,
                progress_object=progress,
            )
        else:
            enable_result = _enable(
                EnableOptions(
                    service=ent_name,
                    variant=variant,
                    access_only=access_only,
                ),
                cfg,
                progress_object=progress,
            )

        status.status(cfg=cfg)  # Update the status cache

        if access_only:
            interactive_only_print(
                messages.ACCESS_ENABLED_TMPL.format(title=ent_title)
            )
        else:
            interactive_only_print(
                messages.ENABLED_TMPL.format(title=ent_title)
            )

        needs_reboot = enable_result.reboot_required
        if needs_reboot:
            interactive_only_print(
                messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation="install"
                )
            )

        for message in enable_result.messages:
            interactive_only_print(message)

        return _EnableOneServiceResult(
            success=True,
            needs_reboot=needs_reboot,
            error=None,
        )

    except exceptions.EntitlementNotEnabledError as e:
        reason = e.additional_info["reason"]
        err_code = reason["code"]
        err_msg = reason["title"]
        err_info = reason["additional_info"]
        interactive_only_print(err_msg)
        interactive_only_print(messages.ENABLE_FAILED.format(title=ent_title))
        return _EnableOneServiceResult(
            success=False,
            needs_reboot=False,
            error={
                "type": "service",
                "service": ent_name,
                "message": err_msg,
                "message_code": err_code,
                "additional_info": err_info,
            },
        )
    except exceptions.UbuntuProError as e:
        interactive_only_print(e.msg)
        interactive_only_print(messages.ENABLE_FAILED.format(title=ent_title))
        return _EnableOneServiceResult(
            success=False,
            needs_reboot=False,
            error={
                "type": "service",
                "service": ent_name,
                "message": e.msg,
                "message_code": e.msg_code,
                "additional_info": e.additional_info,
            },
        )


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached(cli_util._raise_enable_disable_unattached_error)
def action_enable(args, *, cfg, **kwargs) -> int:
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    processed_services = []  # type: List[str]
    failed_services = []  # type: List[str]
    errors = []  # type: List[Dict[str, Any]]
    warnings = []

    json_response = {
        "_schema_version": event_logger.JSON_SCHEMA_VERSION,
        "needs_reboot": False,
    }

    json_output = args.format == "json"
    # HACK NOTICE: interactive_only_print here will be a no-op "null_print"
    # function defined above if args.format == "json". We use this function
    # throughout enable for things that should get printed in the normal
    # interactive output so that they don't get printed for the json output.
    interactive_only_print = cli_util.create_interactive_only_print_function(
        json_output
    )

    variant = getattr(args, "variant", "")
    access_only = args.access_only
    assume_yes = args.assume_yes

    if variant and access_only:
        raise exceptions.InvalidOptionCombination(
            option1="--access-only", option2="--variant"
        )

    interactive_only_print(messages.REFRESH_CONTRACT_ENABLE)
    try:
        contract.refresh(cfg)
    except (exceptions.ConnectivityError, exceptions.UbuntuProError):
        # Inability to refresh is not a critical issue during enable
        LOG.warning("Failed to refresh contract", exc_info=True)
        warnings.append(
            {
                "type": "system",
                "message": messages.E_REFRESH_CONTRACT_FAILURE.msg,
                "message_code": messages.E_REFRESH_CONTRACT_FAILURE.name,
            }
        )

    if not _is_attached(cfg).is_attached_and_contract_valid:
        expired_err = exceptions.ContractExpiredError()
        interactive_only_print(expired_err.msg)
        errors.append(
            {
                "type": "system",
                "message": expired_err.msg,
                "message_code": expired_err.msg_code,
            }
        )
        _print_json_output(
            json_output,
            json_response,
            processed_services,
            failed_services,
            errors,
            warnings,
            success=False,
        )
        return 1

    names = getattr(args, "service", [])
    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(names, cfg)
    enabled_services = _enabled_services(cfg).enabled_services
    all_dependencies = _dependencies(cfg).services

    ret = True
    for ent_name in entitlements.order_entitlements_for_enabling(
        cfg, entitlements_found
    ):
        result = _enable_one_service(
            cfg,
            ent_name,
            variant,
            access_only,
            assume_yes,
            json_output,
            kwargs.get("extra_args"),
            enabled_services,
            all_dependencies,
        )
        if result.success:
            processed_services.append(ent_name)
            if result.needs_reboot:
                json_response["needs_reboot"] = True
        else:
            ret = False
            failed_services.append(ent_name)
            if result.error is not None:
                errors.append(result.error)

    if entitlements_not_found:
        ret = False
        failed_services += entitlements_not_found
        err = entitlements.create_enable_entitlements_not_found_error(
            entitlements_not_found, cfg=cfg
        )
        interactive_only_print(err.msg)
        errors.append(
            {
                "type": "system",
                "service": None,
                "message": err.msg,
                "message_code": err.msg_code,
                "additional_info": err.additional_info,
            }
        )

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    _print_json_output(
        json_output,
        json_response,
        processed_services,
        failed_services,
        errors,
        warnings,
        success=ret,
    )

    return 0 if ret else 1


enable_command = ProCommand(
    "enable",
    help=messages.CLI_ROOT_ENABLE,
    description=messages.CLI_ENABLE_DESC,
    action=action_enable,
    help_category=HelpCategory.QUICKSTART,
    help_position=3,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "service",
                    help=messages.CLI_ENABLE_SERVICE.format(
                        options=", ".join(
                            entitlements.valid_services(cfg=config.UAConfig())
                        )
                    ),
                    action="store",
                    nargs="+",
                ),
                ProArgument(
                    "--assume-yes",
                    help=messages.CLI_ASSUME_YES.format(command="enable"),
                    action="store_true",
                ),
                ProArgument(
                    "--access-only",
                    help=messages.CLI_ENABLE_ACCESS_ONLY,
                    action="store_true",
                ),
                ProArgument(
                    "--beta",
                    help=messages.CLI_ENABLE_BETA,
                    action="store_true",
                ),
                ProArgument(
                    "--format",
                    help=messages.CLI_FORMAT_DESC.format(default="cli"),
                    action="store",
                    choices=["cli", "json"],
                    default="cli",
                ),
                ProArgument(
                    "--variant",
                    help=messages.CLI_ENABLE_VARIANT,
                    action="store",
                ),
            ]
        )
    ],
)
