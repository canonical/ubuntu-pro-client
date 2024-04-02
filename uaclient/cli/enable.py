import json
import logging
from typing import List

from uaclient import (
    api,
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    messages,
    status,
    util,
)
from uaclient.api.u.pro.services.dependencies.v1 import (
    ServiceWithDependencies,
    _dependencies,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.cli import cli_util, constants
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def prompt_for_dependency_handling(
    cfg: config.UAConfig,
    service: str,
    all_dependencies: List[ServiceWithDependencies],
    enabled_service_names: List[str],
    called_name: str,
    service_title: str,
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


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached(cli_util._raise_enable_disable_unattached_error)
@cli_util.assert_lock_file("pro enable")
def action_enable(args, *, cfg, **kwargs) -> int:
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    processed_services = []
    failed_services = []
    errors = []
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
    interactive_only_print = cli_util.create_interactive_only_print_function(
        json_output
    )

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
        ent = entitlements.entitlement_factory(cfg, ent_name, variant=variant)(
            cfg,
            assume_yes=args.assume_yes,
            allow_beta=args.beta,
            called_name=ent_name,
            access_only=access_only,
            extra_args=kwargs.get("extra_args"),
        )
        real_name = ent.name
        ent_title = ent.title

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
                    service_title=ent_title,
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
                progress = api.ProgressWrapper()
            else:
                progress = api.ProgressWrapper(
                    cli_util.CLIEnableDisableProgress()
                )

            progress.total_steps = ent.calculate_total_enable_steps()
            ent_ret, reason = ent.enable(progress)

            status.status(cfg=cfg)  # Update the status cache

            if (
                not ent_ret
                and reason is not None
                and isinstance(reason, CanEnableFailure)
            ):
                if reason.message is not None:
                    interactive_only_print(reason.message.msg)
                    failed_services.append(ent_name)
                    errors.append(
                        {
                            "type": "service",
                            "service": ent_name,
                            "message": reason.message.msg,
                            "message_code": reason.message.name,
                        }
                    )
                if reason.reason == CanEnableFailureReason.IS_BETA:
                    # if we failed because ent is in beta and there was no
                    # allow_beta flag/config, pretend it doesn't exist
                    entitlements_not_found.append(ent_name)
                interactive_only_print(
                    messages.ENABLE_FAILED.format(title=ent.title)
                )
            elif ent_ret:
                processed_services.append(ent_name)
                if args.access_only:
                    interactive_only_print(
                        messages.ACCESS_ENABLED_TMPL.format(title=ent.title)
                    )
                else:
                    interactive_only_print(
                        messages.ENABLED_TMPL.format(title=ent.title)
                    )
                ent_reboot_required = ent._check_for_reboot()
                if ent_reboot_required:
                    json_response["needs_reboot"] = True
                    interactive_only_print(
                        messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                            operation="install"
                        )
                    )
                progress.emit(
                    "message_operation", ent.messaging.get("post_enable")
                )
            elif not ent_ret and reason is None:
                failed_services.append(ent_name)
                interactive_only_print(
                    messages.ENABLE_FAILED.format(title=ent.title)
                )

            ret &= ent_ret
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
