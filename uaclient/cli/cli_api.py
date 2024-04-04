import json
import sys
from collections import OrderedDict
from typing import Any, Optional  # noqa: F401

from uaclient import exceptions, messages
from uaclient.api import AbstractProgress
from uaclient.api.api import call_api


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


def add_parser(subparsers, cfg):
    """Build or extend an arg parser for the api subcommand."""
    parser = subparsers.add_parser("api", help=messages.CLI_ROOT_API)
    parser.prog = "api"
    parser.description = messages.CLI_API_DESC
    parser.add_argument(
        "endpoint_path", metavar="endpoint", help=messages.CLI_API_ENDPOINT
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help=messages.CLI_API_SHOW_PROGRESS,
    )
    parser.add_argument(
        "--args",
        dest="options",
        default=[],
        nargs="*",
        help=messages.CLI_API_ARGS,
    )
    parser.add_argument(
        "--data", dest="data", default="", help=messages.CLI_API_DATA
    )
    parser.set_defaults(action=action_api)
    return parser
