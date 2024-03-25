import json
import logging
from typing import Any, Dict, List, Optional  # noqa: F401

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
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.cli import cli_util, constants

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def _enable_landscape(
    cfg: config.UAConfig,
    args,
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
        assume_yes=args.assume_yes,
        allow_beta=args.beta,
        called_name="landscape",
        access_only=args.access_only,
        extra_args=extra_args,
    )
    success = False
    fail_reason = None

    try:
        with lock.RetryLock(
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


class CLIEnableProgress(api.AbstractProgress):
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
        elif event == "message_operation":
            if not util.handle_message_operations(payload, print):
                raise exceptions.PromptDeniedError()


def prompt_for_dependency_handling(
    cfg: config.UAConfig,
    service: str,
    all_dependencies: List[ServiceWithDependencies],
    enabled_service_names: List[str],
    called_name: str,
):
    incompatible_services = []
    required_services = []
    service_title = entitlements.ENTITLEMENT_NAME_TO_TITLE.get(
        service, service
    )

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
        incompatible_service_title = (
            entitlements.ENTITLEMENT_NAME_TO_TITLE.get(
                incompatible_service, incompatible_service
            )
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
        required_service_title = entitlements.ENTITLEMENT_NAME_TO_TITLE.get(
            required_service, required_service
        )
        user_msg = messages.REQUIRED_SERVICE.format(
            service_being_enabled=service_title,
            required_service=required_service_title,
        )
        if not util.prompt_for_confirmation(msg=user_msg):
            raise exceptions.RequiredServiceStopsEnable(
                service_being_enabled=service_title,
                required_service=required_service_title,
            )


def _null_print(*args, **kwargs):
    pass


def _create_print_function(json_output: bool):
    if json_output:
        return _null_print
    else:
        return print


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached(cli_util._raise_enable_disable_unattached_error)
def action_enable(args, *, cfg, **kwargs) -> int:
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    processed_services = []
    failed_services = []
    errors = []  # type: List[Dict[str, Any]]
    warnings = []

    json_response = {
        "_schema_version": event_logger.JSON_SCHEMA_VERSION,
        "result": "success",
        "needs_reboot": False,
    }

    json_output = args.format == "json"
    # HACK NOTICE: interactive_only_print here will be a no-op "null_print"
    # function defined above if args.format == "json". We use this function
    # throughout enable for things that should get printed in the normal
    # interactive output so that they don't get printed for the json output.
    interactive_only_print = _create_print_function(json_output)

    variant = getattr(args, "variant", "")
    access_only = args.access_only

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

    names = getattr(args, "service", [])
    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(names, cfg)
    enabled_service_names = [
        s.name for s in _enabled_services(cfg).enabled_services
    ]
    all_dependencies = _dependencies(cfg).services

    ret = True
    for ent_name in entitlements.order_entitlements_for_enabling(
        cfg, entitlements_found
    ):
        try:
            ent = entitlements.entitlement_factory(cfg, ent_name)
            real_name = ent.name
            ent_title = ent.title
        except exceptions.UbuntuProError:
            real_name = ent_name
            ent_title = ent_name

        if ent_name in enabled_service_names:
            failed_services.append(ent_name)
            msg = messages.ALREADY_ENABLED.format(title=ent_title)
            interactive_only_print(msg.msg)
            interactive_only_print(
                messages.ENABLE_FAILED.format(title=ent_title)
            )
            errors.append(
                {
                    "type": "service",
                    "service": ent_name,
                    "message": msg.msg,
                    "message_code": msg.name,
                }
            )
            ret = False
            continue

        if not args.assume_yes:
            # this never happens for json output because we assert earlier that
            # assume_yes must be True for json output
            try:
                prompt_for_dependency_handling(
                    cfg,
                    real_name,
                    all_dependencies,
                    enabled_service_names,
                    called_name=ent_name,
                )
            except exceptions.UbuntuProError as e:
                LOG.exception(e)
                interactive_only_print(e.msg)
                interactive_only_print(
                    messages.ENABLE_FAILED.format(title=ent_title)
                )
                ret = False
                continue

        try:
            if json_output:
                progress = None
            else:
                progress = CLIEnableProgress()

            if real_name == "landscape":
                enable_result = _enable_landscape(
                    cfg,
                    args,
                    extra_args=kwargs.get("extra_args"),
                    progress_object=progress,
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

            processed_services.append(ent_name)

            status.status(cfg=cfg)  # Update the status cache

            if args.access_only:
                interactive_only_print(
                    messages.ACCESS_ENABLED_TMPL.format(title=ent_title)
                )
            else:
                interactive_only_print(
                    messages.ENABLED_TMPL.format(title=ent_title)
                )

            if enable_result.reboot_required:
                json_response["needs_reboot"] = True
                interactive_only_print(
                    messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="install"
                    )
                )

            for message in enable_result.messages:
                interactive_only_print(message)

        except exceptions.EntitlementNotEnabledError as e:
            failed_services.append(ent_name)
            reason = e.additional_info["reason"]
            err_code = reason["code"]
            err_msg = reason["title"]
            err_info = reason["additional_info"]
            interactive_only_print(err_msg)
            interactive_only_print(
                messages.ENABLE_FAILED.format(title=ent_title)
            )
            errors.append(
                {
                    "type": "service",
                    "service": ent_name,
                    "message": err_msg,
                    "message_code": err_code,
                    "additional_info": err_info,
                }
            )
            ret = False
        except exceptions.UbuntuProError as e:
            failed_services.append(ent_name)
            interactive_only_print(e.msg)
            interactive_only_print(
                messages.ENABLE_FAILED.format(title=ent_title)
            )
            errors.append(
                {
                    "type": "service",
                    "service": ent_name,
                    "message": e.msg,
                    "message_code": e.msg_code,
                    "additional_info": e.additional_info,
                }
            )
            ret = False

    if entitlements_not_found:
        ret = False
        failed_services += entitlements_not_found
        err = entitlements.create_enable_entitlements_not_found_error(
            entitlements_not_found, cfg=cfg, allow_beta=args.beta
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

    if json_output:
        processed_services.sort()
        failed_services.sort()

        json_response["result"] = "success" if ret else "failure"
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

    return 0 if ret else 1


def add_parser(subparsers, cfg: config.UAConfig):
    parser = subparsers.add_parser("enable", help=messages.CLI_ROOT_ENABLE)
    parser.set_defaults(action=action_enable)
    parser.description = messages.CLI_ENABLE_DESC
    parser.usage = constants.USAGE_TMPL.format(
        name=constants.NAME, command="enable <service> [<service>]"
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
