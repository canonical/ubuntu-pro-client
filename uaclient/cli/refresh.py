import logging

from uaclient import apt_news, config, contract, exceptions, messages, util
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory
from uaclient.timer.update_messaging import refresh_motd, update_motd_messages

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def _action_refresh_config(args, cfg: config.UAConfig):
    try:
        cfg.process_config()
    except RuntimeError as exc:
        LOG.exception(exc)
        raise exceptions.RefreshConfigFailure()
    print(messages.REFRESH_CONFIG_SUCCESS)


@cli_util.assert_attached()
def _action_refresh_contract(_args, cfg: config.UAConfig):
    try:
        contract.refresh(cfg)
    except exceptions.ConnectivityError:
        raise exceptions.RefreshContractFailure()
    print(messages.REFRESH_CONTRACT_SUCCESS)


def _action_refresh_messages(_args, cfg: config.UAConfig):
    # Not performing any exception handling here since both of these
    # functions should raise UbuntuProError exceptions, which are
    # covered by the main_error_handler decorator
    try:
        update_motd_messages(cfg)
        refresh_motd()
        if cfg.apt_news:
            apt_news.update_apt_news(cfg)
    except Exception as exc:
        LOG.exception(exc)
        raise exceptions.RefreshMessagesFailure()
    else:
        print(messages.REFRESH_MESSAGES_SUCCESS)


@cli_util.assert_root
@cli_util.assert_lock_file("pro refresh")
def action_refresh(args, *, cfg: config.UAConfig, **kwargs):
    if args.target is None or args.target == "config":
        _action_refresh_config(args, cfg)

    if args.target is None or args.target == "contract":
        _action_refresh_contract(args, cfg)

    if args.target is None or args.target == "messages":
        _action_refresh_messages(args, cfg)

    return 0


refresh_command = ProCommand(
    "refresh",
    help=messages.CLI_ROOT_REFRESH,
    description=messages.CLI_REFRESH_DESC,
    action=action_refresh,
    preserve_description=True,
    help_category=HelpCategory.OTHER,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "target",
                    help=messages.CLI_REFRESH_TARGET,
                    nargs="?",
                    choices=["contract", "config", "messages"],
                    default=None,
                )
            ]
        )
    ],
)
