import logging

from uaclient import (
    actions,
    config,
    contract,
    entitlements,
    event_logger,
    exceptions,
    messages,
    status,
    util,
)
from uaclient.cli import cli_util, constants
from uaclient.entitlements.entitlement_status import (
    CanEnableFailure,
    CanEnableFailureReason,
)

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached(cli_util._raise_enable_disable_unattached_error)
@cli_util.assert_lock_file("pro enable")
def action_enable(args, *, cfg, **kwargs):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    variant = getattr(args, "variant", "")
    access_only = args.access_only

    if variant and access_only:
        raise exceptions.InvalidOptionCombination(
            option1="--access-only", option2="--variant"
        )

    event.info(messages.REFRESH_CONTRACT_ENABLE)
    try:
        contract.refresh(cfg)
    except (exceptions.ConnectivityError, exceptions.UbuntuProError):
        # Inability to refresh is not a critical issue during enable
        LOG.warning("Failed to refresh contract", exc_info=True)
        event.warning(warning_msg=messages.E_REFRESH_CONTRACT_FAILURE)

    names = getattr(args, "service", [])
    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(names, cfg)
    ret = True
    for ent_name in entitlements_found:
        try:
            ent_ret, reason = actions.enable_entitlement_by_name(
                cfg,
                ent_name,
                assume_yes=args.assume_yes,
                allow_beta=args.beta,
                access_only=access_only,
                variant=variant,
                extra_args=kwargs.get("extra_args"),
            )
            status.status(cfg=cfg)  # Update the status cache

            if (
                not ent_ret
                and reason is not None
                and isinstance(reason, CanEnableFailure)
            ):
                if reason.message is not None:
                    event.info(reason.message.msg)
                    event.error(
                        error_msg=reason.message.msg,
                        error_code=reason.message.name,
                        service=ent_name,
                    )
                if reason.reason == CanEnableFailureReason.IS_BETA:
                    # if we failed because ent is in beta and there was no
                    # allow_beta flag/config, pretend it doesn't exist
                    entitlements_not_found.append(ent_name)
            elif ent_ret:
                event.service_processed(service=ent_name)
            elif not ent_ret and reason is None:
                event.service_failed(service=ent_name)

            ret &= ent_ret
        except exceptions.UbuntuProError as e:
            event.info(e.msg)
            event.error(
                error_msg=e.msg,
                error_code=e.msg_code,
                service=ent_name,
                additional_info=e.additional_info,
            )
            ret = False

    if entitlements_not_found:
        event.services_failed(entitlements_not_found)
        raise entitlements.create_enable_entitlements_not_found_error(
            entitlements_not_found, cfg=cfg, allow_beta=args.beta
        )

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    event.process_events()
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
