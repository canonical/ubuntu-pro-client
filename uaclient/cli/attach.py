import argparse
import sys

from uaclient import (
    actions,
    contract,
    event_logger,
    exceptions,
    messages,
    secret_manager,
)
from uaclient.api.u.pro.attach.magic.initiate.v1 import _initiate
from uaclient.api.u.pro.attach.magic.revoke.v1 import (
    MagicAttachRevokeOptions,
    _revoke,
)
from uaclient.api.u.pro.attach.magic.wait.v1 import (
    MagicAttachWaitOptions,
    _wait,
)
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory
from uaclient.data_types import AttachActionsConfigFile, IncorrectTypeError
from uaclient.entitlements import (
    create_enable_entitlements_not_found_error,
    get_valid_entitlement_names,
)
from uaclient.entitlements.entitlement_status import CanEnableFailure
from uaclient.yaml import safe_load

event = event_logger.get_event_logger()


def _magic_attach(args, *, cfg, **kwargs):
    if args.format == "json":
        raise exceptions.MagicAttachInvalidParam(
            param="--format",
            value=args.format,
        )

    event.info(messages.CLI_MAGIC_ATTACH_INIT)
    initiate_resp = _initiate(cfg=cfg)
    event.info(
        "\n"
        + messages.CLI_MAGIC_ATTACH_SIGN_IN.format(
            user_code=initiate_resp.user_code
        )
    )

    wait_options = MagicAttachWaitOptions(magic_token=initiate_resp.token)

    try:
        wait_resp = _wait(options=wait_options, cfg=cfg)
    except exceptions.MagicAttachTokenError as e:
        event.info(messages.CLI_MAGIC_ATTACH_FAILED)

        revoke_options = MagicAttachRevokeOptions(
            magic_token=initiate_resp.token
        )
        _revoke(options=revoke_options, cfg=cfg)
        raise e

    event.info("\n" + messages.CLI_MAGIC_ATTACH_PROCESSING)
    return wait_resp.contract_token


@cli_util.assert_not_attached
@cli_util.assert_root
@cli_util.assert_lock_file("pro attach")
def action_attach(args, *, cfg, **kwargs):
    if args.token and args.attach_config:
        raise exceptions.CLIAttachTokenArgXORConfig()
    elif not args.token and not args.attach_config:
        token = _magic_attach(args, cfg=cfg)
        enable_services_override = None
    elif args.token:
        token = args.token
        secret_manager.secrets.add_secret(token)
        enable_services_override = None
    else:
        try:
            attach_config = AttachActionsConfigFile.from_dict(
                safe_load(args.attach_config)
            )
        except IncorrectTypeError as e:
            raise exceptions.AttachInvalidConfigFileError(
                config_name=args.attach_config.name, error=e.msg
            )

        token = attach_config.token
        enable_services_override = attach_config.enable_services

    allow_enable = args.auto_enable and enable_services_override is None

    try:
        actions.attach_with_token(cfg, token=token, allow_enable=allow_enable)
    except exceptions.ConnectivityError:
        raise exceptions.AttachError()
    else:
        ret = 0
        if enable_services_override is not None and args.auto_enable:
            found, not_found = get_valid_entitlement_names(
                enable_services_override, cfg
            )
            for name in found:
                ent_ret, reason = actions.enable_entitlement_by_name(cfg, name)
                if not ent_ret:
                    ret = 1
                    if (
                        reason is not None
                        and isinstance(reason, CanEnableFailure)
                        and reason.message is not None
                    ):
                        event.info(reason.message.msg)
                        event.error(
                            error_msg=reason.message.msg,
                            error_code=reason.message.name,
                            service=name,
                        )
                else:
                    event.service_processed(name)

            if not_found:
                error = create_enable_entitlements_not_found_error(
                    not_found, cfg=cfg
                )
                event.info(error.msg, file_type=sys.stderr)
                event.error(error_msg=error.msg, error_code=error.msg_code)
                ret = 1

        contract_client = contract.UAContractClient(cfg)
        contract_client.update_activity_token()

        cli_util.post_cli_attach(cfg)
        return ret


attach_command = ProCommand(
    "attach",
    help=messages.CLI_ROOT_ATTACH,
    description=messages.CLI_ATTACH_DESC,
    action=action_attach,
    preserve_description=True,
    help_category=HelpCategory.QUICKSTART,
    help_position=2,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "token", help=messages.CLI_ATTACH_TOKEN, nargs="?"
                ),
                ProArgument(
                    "--no-auto-enable",
                    help=messages.CLI_ATTACH_NO_AUTO_ENABLE,
                    action="store_false",
                    dest="auto_enable",
                ),
                ProArgument(
                    "--attach-config",
                    help=messages.CLI_ATTACH_ATTACH_CONFIG,
                    type=argparse.FileType("r"),
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
