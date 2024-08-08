import time

from uaclient import actions, config, event_logger, messages, status, util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory

event = event_logger.get_event_logger()


def action_status(args, *, cfg: config.UAConfig, **kwargs):
    if not cfg:
        cfg = config.UAConfig()
    show_all = args.all if args else False
    token = args.simulate_with_token if args else None
    active_value = status.UserFacingConfigStatus.ACTIVE.value
    status_dict, ret = actions.status(
        cfg, simulate_with_token=token, show_all=show_all
    )
    config_active = bool(status_dict["execution_status"] == active_value)

    if args and args.wait and config_active:
        while status_dict["execution_status"] == active_value:
            event.info(".", end="")
            time.sleep(1)
            status_dict, ret = actions.status(
                cfg,
                simulate_with_token=token,
                show_all=show_all,
            )
        event.info("")

    event.set_output_content(status_dict)
    output = status.format_tabular(status_dict, show_all=show_all)
    event.info(util.handle_unicode_characters(output))
    event.process_events()
    return ret


status_command = ProCommand(
    "status",
    help=messages.CLI_ROOT_STATUS,
    description=messages.CLI_STATUS_DESC,
    action=action_status,
    preserve_description=True,
    help_category=HelpCategory.QUICKSTART,
    help_position=1,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "--wait",
                    help=messages.CLI_STATUS_WAIT,
                    action="store_true",
                ),
                ProArgument(
                    "--format",
                    help=messages.CLI_FORMAT_DESC.format(default="tabular"),
                    action="store",
                    choices=["tabular", "json", "yaml"],
                    default="tabular",
                ),
                ProArgument(
                    "--simulate-with-token",
                    help=messages.CLI_STATUS_SIMULATE_WITH_TOKEN,
                    metavar="TOKEN",
                    action="store",
                ),
                ProArgument(
                    "--all", help=messages.CLI_STATUS_ALL, action="store_true"
                ),
            ]
        )
    ],
)
