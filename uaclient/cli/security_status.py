import json

from uaclient import messages, security_status, util
from uaclient.cli.commands import (
    ProArgument,
    ProArgumentGroup,
    ProArgumentMutuallyExclusiveGroup,
    ProCommand,
)
from uaclient.cli.parser import HelpCategory
from uaclient.yaml import safe_dump


def action_security_status(args, *, cfg, **kwargs):
    if args.format == "text":
        if args.thirdparty:
            security_status.list_third_party_packages()
        elif args.unavailable:
            security_status.list_unavailable_packages()
        elif args.esm_infra:
            security_status.list_esm_infra_packages(cfg)
        elif args.esm_apps:
            security_status.list_esm_apps_packages(cfg)
        else:
            security_status.security_status(cfg)
    elif args.format == "json":
        print(
            json.dumps(
                security_status.security_status_dict(cfg),
                sort_keys=True,
                cls=util.DatetimeAwareJSONEncoder,
            )
        )
    else:
        print(
            safe_dump(
                security_status.security_status_dict(cfg),
                default_flow_style=False,
            )
        )
    return 0


security_status_command = ProCommand(
    "security-status",
    help=messages.CLI_ROOT_SECURITY_STATUS,
    description=messages.CLI_SS_DESC,
    preserve_description=True,
    action=action_security_status,
    help_category=HelpCategory.QUICKSTART,
    help_position=5,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "--format",
                    help=messages.CLI_FORMAT_DESC.format(default="text"),
                    choices=("json", "yaml", "text"),
                    default="text",
                )
            ],
            mutually_exclusive_groups=[
                ProArgumentMutuallyExclusiveGroup(
                    arguments=[
                        ProArgument(
                            "--thirdparty",
                            help=messages.CLI_SS_THIRDPARTY,
                            action="store_true",
                        ),
                        ProArgument(
                            "--unavailable",
                            help=messages.CLI_SS_UNAVAILABLE,
                            action="store_true",
                        ),
                        ProArgument(
                            "--esm-infra",
                            help=messages.CLI_SS_ESM_INFRA,
                            action="store_true",
                        ),
                        ProArgument(
                            "--esm-apps",
                            help=messages.CLI_SS_ESM_APPS,
                            action="store_true",
                        ),
                    ]
                )
            ],
        )
    ],
)
