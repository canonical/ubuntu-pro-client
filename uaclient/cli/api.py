import json
import sys
from collections import OrderedDict
from typing import Any, Optional  # noqa: F401

from uaclient import exceptions, messages
from uaclient.api import AbstractProgress
from uaclient.api.api import call_api
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory


class CLIAPIProgress(AbstractProgress):
    def progress(
        self,
        *,
        total_steps: int,
        done_steps: int,
        previous_step_message: Optional[str],
        current_step_message: Optional[str]
    ):
        d = OrderedDict()  # type: OrderedDict[str, Any]
        d["total_steps"] = total_steps
        d["done_steps"] = done_steps
        d["previous_step_message"] = previous_step_message
        d["current_step_message"] = current_step_message
        print(json.dumps(d))


def action_api(args, *, cfg, **kwargs):
    if args.options and args.data:
        raise exceptions.CLIAPIOptionsXORData()

    if args.data and args.data == "-":
        if not sys.stdin.isatty():
            args.data = sys.stdin.read()

    if args.show_progress:
        progress = CLIAPIProgress()
    else:
        progress = None

    result = call_api(
        args.endpoint_path, args.options, args.data, cfg, progress
    )
    print(result.to_json())
    return 0 if result.result == "success" else 1


api_command = ProCommand(
    "api",
    help=messages.CLI_ROOT_API,
    description=messages.CLI_API_DESC,
    action=action_api,
    help_category=HelpCategory.OTHER,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "endpoint_path",
                    help=messages.CLI_API_ENDPOINT,
                    metavar="endpoint",
                ),
                ProArgument(
                    "--show-progress",
                    help=messages.CLI_API_SHOW_PROGRESS,
                    action="store_true",
                ),
                ProArgument(
                    "--args",
                    help=messages.CLI_API_ARGS,
                    dest="options",
                    default=[],
                    nargs="*",
                ),
                ProArgument(
                    "--data",
                    help=messages.CLI_API_DATA,
                    dest="data",
                    default="",
                ),
            ]
        )
    ],
)
