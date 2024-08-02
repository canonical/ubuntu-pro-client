import logging
import tarfile
import tempfile

from uaclient import messages
from uaclient.actions import collect_logs
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory
from uaclient.util import replace_top_level_logger_name

PRO_COLLECT_LOGS_FILE = "pro_logs.tar.gz"
LOG = logging.getLogger(replace_top_level_logger_name(__name__))


def action_collect_logs(args, *, cfg, **kwargs):
    output_file = args.output or PRO_COLLECT_LOGS_FILE
    with tempfile.TemporaryDirectory() as output_dir:
        collect_logs(cfg, output_dir)
        try:
            with tarfile.open(output_file, "w:gz") as results:
                results.add(output_dir, arcname="logs/")
        except PermissionError as e:
            LOG.error(e)
            return 1
    return 0


collect_logs_command = ProCommand(
    "collect-logs",
    help=messages.CLI_ROOT_COLLECT_LOGS,
    description=messages.CLI_COLLECT_LOGS_DESC,
    action=action_collect_logs,
    help_category=HelpCategory.TROUBLESHOOT,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "--output",
                    short_name="-o",
                    help=messages.CLI_COLLECT_LOGS_OUTPUT,
                )
            ]
        )
    ],
)
