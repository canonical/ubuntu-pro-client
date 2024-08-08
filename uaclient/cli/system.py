from uaclient import event_logger, messages
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.cli.commands import ProCommand
from uaclient.cli.parser import HelpCategory

event = event_logger.get_event_logger()


def action_reboot_required(args, *, cfg, **kwargs):
    result = _reboot_required(cfg)
    event.info(result.reboot_required)
    return 0


def action_system(args, *, cfg, **kwargs):
    # Avoiding a circular import
    from uaclient.cli import get_parser

    get_parser().print_help_for_command("system")


reboot_required_subcommand = ProCommand(
    "reboot-required",
    help=messages.CLI_SYSTEM_REBOOT_REQUIRED,
    description=messages.CLI_SYSTEM_REBOOT_REQUIRED_DESC,
    action=action_reboot_required,
    preserve_description=True,
)

system_command = ProCommand(
    "system",
    help=messages.CLI_ROOT_SYSTEM,
    description=messages.CLI_SYSTEM_DESC,
    action=action_system,
    help_category=HelpCategory.QUICKSTART,
    help_position=4,
    subcommands=[reboot_required_subcommand],
)
