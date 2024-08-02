import json
import logging
import textwrap
from typing import Dict, List  # noqa: F401

from uaclient import (
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    messages,
    status,
    util,
)
from uaclient.api import ProgressWrapper
from uaclient.api.u.pro.services.dependencies.v1 import (
    ServiceWithDependencies,
    _dependencies,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory
from uaclient.entitlements.entitlement_status import CanDisableFailure

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def prompt_for_dependency_handling(
    cfg: config.UAConfig,
    service: str,
    all_dependencies: List[ServiceWithDependencies],
    enabled_service_names: List[str],
    called_name: str,
    service_title: str,
):
    dependent_services = []
    for s in all_dependencies:
        if s.name == service or s.name not in enabled_service_names:
            continue
        for requirement in s.depends_on:
            if requirement.name == service:
                dependent_services.append(s.name)

    for dependent_service in dependent_services:
        dependent_service_title = entitlements.get_title(
            cfg, dependent_service
        )
        user_msg = messages.DEPENDENT_SERVICE.format(
            service_being_disabled=service_title,
            dependent_service=dependent_service_title,
        )
        if not util.prompt_for_confirmation(msg=user_msg):
            raise exceptions.DependentServiceStopsDisable(
                service_being_disabled=service_title,
                dependent_service=dependent_service_title,
            )


def perform_disable(
    entitlement, cfg, *, json_output, assume_yes, update_status=True
):
    """Perform the disable action on a named entitlement.

    :param entitlement_name: the name of the entitlement to enable
    :param cfg: the UAConfig to pass to the entitlement
    :param json_output: output should be json only

    @return: True on success, False otherwise
    """
    # Make sure we have the correct variant of the service
    # This can affect what packages get uninstalled
    variant = entitlement.enabled_variant
    if variant is not None:
        entitlement = variant

    if json_output:
        progress = ProgressWrapper()
    else:
        progress = ProgressWrapper(
            cli_util.CLIEnableDisableProgress(assume_yes=assume_yes)
        )

    ret, reason = entitlement.disable(progress)

    if not ret:
        event.service_failed(entitlement.name)

        if reason is not None and isinstance(reason, CanDisableFailure):
            if reason.message is not None:
                event.info(reason.message.msg)
                event.error(
                    error_msg=reason.message.msg,
                    error_code=reason.message.name,
                    service=entitlement.name,
                )
    else:
        event.service_processed(entitlement.name)

    if update_status:
        status.status(cfg=cfg)  # Update the status cache

    return ret


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached(cli_util._raise_enable_disable_unattached_error)
@cli_util.assert_lock_file("pro disable")
def action_disable(args, *, cfg, **kwargs):
    """Perform the disable action on a list of entitlements.

    @return: 0 on success, 1 otherwise
    """
    processed_services = []
    failed_services = []
    errors = []
    warnings = []  # type: List[Dict[str, str]]

    json_response = {
        "_schema_version": event_logger.JSON_SCHEMA_VERSION,
        "result": "success",
        "needs_reboot": False,
    }

    json_output = args.format == "json"
    assume_yes = args.assume_yes
    # HACK NOTICE: interactive_only_print here will be a no-op "null_print"
    # function defined above if args.format == "json". We use this function
    # throughout enable for things that should get printed in the normal
    # interactive output so that they don't get printed for the json output.
    interactive_only_print = cli_util.create_interactive_only_print_function(
        json_output
    )

    if args.purge and assume_yes:
        raise exceptions.InvalidOptionCombination(
            option1="--purge", option2="--assume-yes"
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
    for ent_name in entitlements_found:
        ent = entitlements.entitlement_factory(
            cfg=cfg,
            name=ent_name,
            purge=args.purge,
        )

        variant = ent.enabled_variant
        if variant is not None:
            ent = variant

        if not assume_yes:
            # this never happens for json output because we assert earlier that
            # assume_yes must be True for json output
            try:
                prompt_for_dependency_handling(
                    cfg,
                    ent.name,
                    all_dependencies,
                    enabled_service_names,
                    called_name=ent_name,
                    service_title=ent.title,
                )
            except exceptions.UbuntuProError as e:
                LOG.exception(e)
                interactive_only_print(e.msg)
                interactive_only_print(
                    messages.ENABLE_FAILED.format(title=ent.title)
                )
                ret = False
                continue

        if json_output:
            progress = ProgressWrapper()
        else:
            progress = ProgressWrapper(
                cli_util.CLIEnableDisableProgress(assume_yes=assume_yes)
            )
        progress.total_steps = ent.calculate_total_disable_steps()
        try:
            disable_ret, reason = ent.disable(progress)
            status.status(cfg=cfg)  # Update the status cache

            if not disable_ret:
                ret = False
                failed_services.append(ent_name)
                if reason is not None and isinstance(
                    reason, CanDisableFailure
                ):
                    if reason.message is not None:
                        interactive_only_print(reason.message.msg)
                        errors.append(
                            {
                                "type": "service",
                                "service": ent.name,
                                "message": reason.message.msg,
                                "message_code": reason.message.name,
                            }
                        )
            else:
                processed_services.append(ent_name)
                ent_reboot_required = ent._check_for_reboot()
                if ent_reboot_required:
                    json_response["needs_reboot"] = True
                    interactive_only_print(
                        messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                            operation="disable operation"
                        )
                    )
        except exceptions.UbuntuProError as e:
            ret = False
            failed_services.append(ent_name)
            interactive_only_print(e.msg)
            interactive_only_print(
                messages.DISABLE_FAILED_TMPL.format(title=ent.title)
            )
            errors.append(
                {
                    "type": "service",
                    "service": ent.name,
                    "message": e.msg,
                    "message_code": e.msg_code,
                    "additional_info": e.additional_info,
                }
            )

    if entitlements_not_found:
        ret = False
        valid_names = (
            "Try " + ", ".join(entitlements.valid_services(cfg=cfg)) + "."
        )
        service_msg = "\n".join(
            textwrap.wrap(
                valid_names,
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
        err = exceptions.InvalidServiceOpError(
            operation="disable",
            invalid_service=", ".join(entitlements_not_found),
            service_msg=service_msg,
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


disable_command = ProCommand(
    "disable",
    help=messages.CLI_ROOT_DISABLE,
    description=messages.CLI_DISABLE_DESC,
    action=action_disable,
    help_category=HelpCategory.OTHER,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "service",
                    help=messages.CLI_DISABLE_SERVICE.format(
                        options=", ".join(
                            entitlements.valid_services(cfg=config.UAConfig())
                        )
                    ),
                    action="store",
                    nargs="+",
                ),
                ProArgument(
                    "--assume-yes",
                    help=messages.CLI_ASSUME_YES.format(command="disable"),
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
                    "--purge",
                    help=messages.CLI_PURGE,
                    action="store_true",
                ),
            ]
        )
    ],
)
