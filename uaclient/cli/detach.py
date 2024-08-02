from uaclient import (
    config,
    daemon,
    entitlements,
    event_logger,
    exceptions,
    messages,
    timer,
    util,
)
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.disable import perform_disable
from uaclient.cli.parser import HelpCategory
from uaclient.files import machine_token, state_files
from uaclient.timer.update_messaging import update_motd_messages

event = event_logger.get_event_logger()


@cli_util.verify_json_format_args
@cli_util.assert_root
@cli_util.assert_attached()
@cli_util.assert_lock_file("pro detach")
def action_detach(args, *, cfg, **kwargs) -> int:
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    ret = _detach(
        cfg, assume_yes=args.assume_yes, json_output=(args.format == "json")
    )
    if ret == 0:
        daemon.start()
        timer.stop()
    event.process_events()
    return ret


def _detach(cfg: config.UAConfig, assume_yes: bool, json_output: bool) -> int:
    """Detach the machine from the active Ubuntu Pro subscription,

    :param cfg: a ``config.UAConfig`` instance
    :param assume_yes: Assume a yes answer to any prompts requested.
         In this case, it means automatically disable any service during
         detach.
    :param json_output: output should be json only

    @return: 0 on success, 1 otherwise
    """
    to_disable = []
    for ent_name in entitlements.entitlements_disable_order(cfg):
        try:
            ent = entitlements.entitlement_factory(
                cfg=cfg,
                name=ent_name,
            )
        except exceptions.EntitlementNotFoundError:
            continue

        # For detach, we should not consider that a service
        # cannot be disabled because of dependent services,
        # since we are going to disable all of them anyway
        ret, _ = ent.can_disable(ignore_dependent_services=True)
        if ret:
            to_disable.append(ent)

    if to_disable:
        event.info(messages.DETACH_WILL_DISABLE.pluralize(len(to_disable)))
        for ent in to_disable:
            event.info("    {}".format(ent.name))
    if not util.prompt_for_confirmation(assume_yes=assume_yes):
        return 1
    for ent in to_disable:
        perform_disable(
            ent,
            cfg,
            json_output=json_output,
            assume_yes=assume_yes,
            update_status=False,
        )

    machine_token_file = machine_token.get_machine_token_file(cfg)
    machine_token_file.delete()
    state_files.delete_state_files()
    update_motd_messages(cfg)
    event.info(messages.DETACH_SUCCESS)
    return 0


detach_command = ProCommand(
    "detach",
    help=messages.CLI_ROOT_DETACH,
    description=messages.CLI_DETACH_DESC,
    action=action_detach,
    help_category=HelpCategory.OTHER,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "--assume-yes",
                    help=messages.CLI_ASSUME_YES.format(command="detach"),
                    action="store_true",
                ),
                ProArgument(
                    "--format",
                    help=messages.CLI_FORMAT_DESC.format(default="cli"),
                    action="store",
                    choices=["cli", "json"],
                    default="cli",
                ),
            ]
        )
    ],
)
