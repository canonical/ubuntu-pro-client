import json

from uaclient import config, entitlements, messages, status
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand


def action_help(args, *, cfg, **kwargs):
    service = args.service

    if not service:
        # Avoiding a circular import
        from uaclient.cli import get_parser

        get_parser().print_help()
        return 0

    if not cfg:
        cfg = config.UAConfig()

    help_response = status.help(cfg, service)

    if args.format == "json":
        print(json.dumps(help_response))
    else:
        for key, value in help_response.items():
            print("{}:\n{}\n".format(key.title(), value))

    return 0


help_command = ProCommand(
    "help",
    help=messages.CLI_ROOT_HELP,
    description=messages.CLI_HELP_DESC,
    action=action_help,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "service",
                    help=messages.CLI_HELP_SERVICE.format(
                        options=", ".join(
                            entitlements.valid_services(cfg=config.UAConfig())
                        )
                    ),
                    action="store",
                    nargs="?",
                ),
                ProArgument(
                    "--format",
                    help=(messages.CLI_FORMAT_DESC.format(default="tabular")),
                    action="store",
                    choices=["tabular", "json", "yaml"],
                    default="tabular",
                ),
                ProArgument(
                    "--all", help=messages.CLI_HELP_ALL, action="store_true"
                ),
            ]
        )
    ],
)
