import logging
import textwrap

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
from uaclient.cli import cli_util, constants
from uaclient.entitlements.entitlement_status import CanDisableFailure

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def _perform_disable(entitlement, cfg, *, assume_yes, update_status=True):
    """Perform the disable action on a named entitlement.

    :param entitlement_name: the name of the entitlement to enable
    :param cfg: the UAConfig to pass to the entitlement
    :param assume_yes:
        Assume a yes response for any prompts during service enable

    @return: True on success, False otherwise
    """
    # Make sure we have the correct variant of the service
    # This can affect what packages get uninstalled
    variant = entitlement.enabled_variant
    if variant is not None:
        entitlement = variant

    ret, reason = entitlement.disable()

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
    if args.purge and args.assume_yes:
        raise exceptions.InvalidOptionCombination(
            option1="--purge", option2="--assume-yes"
        )

    names = getattr(args, "service", [])
    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(names, cfg)
    ret = True

    for ent_name in entitlements_found:
        ent_cls = entitlements.entitlement_factory(cfg=cfg, name=ent_name)
        ent = ent_cls(cfg, assume_yes=args.assume_yes, purge=args.purge)

        ret &= _perform_disable(ent, cfg, assume_yes=args.assume_yes)

    if entitlements_not_found:
        valid_names = (
            "Try "
            + ", ".join(entitlements.valid_services(cfg=cfg, allow_beta=True))
            + "."
        )
        service_msg = "\n".join(
            textwrap.wrap(
                valid_names,
                width=80,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
        raise exceptions.InvalidServiceOpError(
            operation="disable",
            invalid_service=", ".join(entitlements_not_found),
            service_msg=service_msg,
        )

    contract_client = contract.UAContractClient(cfg)
    contract_client.update_activity_token()

    event.process_events()
    return 0 if ret else 1


def add_parser(subparsers, cfg: config.UAConfig):
    """Build or extend an arg parser for disable subcommand."""
    parser = subparsers.add_parser("disable", help=messages.CLI_ROOT_DISABLE)
    parser.set_defaults(action=action_disable)
    usage = constants.USAGE_TMPL.format(
        name=constants.NAME, command="disable <service> [<service>]"
    )
    parser.description = messages.CLI_DISABLE_DESC
    parser.usage = usage
    parser.prog = "disable"
    parser._positionals.title = messages.CLI_ARGS
    parser._optionals.title = messages.CLI_FLAGS
    parser.add_argument(
        "service",
        action="store",
        nargs="+",
        help=(
            messages.CLI_DISABLE_SERVICE.format(
                options=", ".join(entitlements.valid_services(cfg=cfg))
            )
        ),
    )
    parser.add_argument(
        "--assume-yes",
        action="store_true",
        help=messages.CLI_ASSUME_YES.format(command="disable"),
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=["cli", "json"],
        default="cli",
        help=messages.CLI_FORMAT_DESC.format(default="cli"),
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help=messages.CLI_PURGE,
    )
    return parser
