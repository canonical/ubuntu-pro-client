from uaclient import event_logger, exceptions, messages
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
    _full_auto_attach,
)
from uaclient.cli import cli_util
from uaclient.cli.commands import ProCommand
from uaclient.cli.parser import HelpCategory

event = event_logger.get_event_logger()


@cli_util.assert_root
def action_auto_attach(args, *, cfg, **kwargs) -> int:
    try:
        _full_auto_attach(
            FullAutoAttachOptions(),
            cfg=cfg,
            mode=event_logger.EventLoggerMode.CLI,
        )
    except exceptions.ConnectivityError:
        event.info(messages.E_ATTACH_FAILURE.msg)
        return 1
    else:
        cli_util.post_cli_attach(cfg)
        return 0


auto_attach_command = ProCommand(
    "auto-attach",
    help=messages.CLI_ROOT_AUTO_ATTACH,
    description=messages.CLI_AUTO_ATTACH_DESC,
    action=action_auto_attach,
    help_category=HelpCategory.OTHER,
)
