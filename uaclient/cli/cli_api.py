from uaclient import exceptions, messages
from uaclient.api import api


def action_api(args, *, cfg, **kwargs):
    if args.options and args.data:
        raise exceptions.CLIAPIOptionsXORData()

    result = api.call_api(args.endpoint_path, args.options, args.data, cfg)
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
