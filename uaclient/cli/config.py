from uaclient import (
    apt_news,
    config,
    entitlements,
    event_logger,
    exceptions,
    http,
    messages,
)
from uaclient.apt import AptProxyScope
from uaclient.cli import cli_util
from uaclient.cli.commands import ProArgument, ProArgumentGroup, ProCommand
from uaclient.cli.parser import HelpCategory
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.files import state_files
from uaclient.livepatch import (
    configure_livepatch_proxy,
    unconfigure_livepatch_proxy,
)
from uaclient.snap import configure_snap_proxy, unconfigure_snap_proxy

event = event_logger.get_event_logger()


def action_config(args, *, cfg, **kwargs):
    # Avoiding a circular import
    from uaclient.cli import get_parser

    get_parser().print_help_for_command("config")
    return 0


def action_config_show(args, *, cfg, **kwargs):
    """Perform the 'config show' action optionally limit output to a single key

    :return: 0 on success
    :raise UbuntuProError: on invalid keys
    """
    if args.key:  # limit reporting config to a single config key
        if args.key not in config.UA_CONFIGURABLE_KEYS:
            raise exceptions.InvalidArgChoice(
                arg="'{}'".format(args.key),
                choices=", ".join(config.UA_CONFIGURABLE_KEYS),
            )
        print(
            "{key} {value}".format(
                key=args.key, value=getattr(cfg, args.key, None)
            )
        )
        return 0

    col_width = str(max([len(x) for x in config.UA_CONFIGURABLE_KEYS]) + 1)
    row_tmpl = "{key: <" + col_width + "} {value}"

    for key in config.UA_CONFIGURABLE_KEYS:
        print(row_tmpl.format(key=key, value=getattr(cfg, key, None)))

    if (cfg.global_apt_http_proxy or cfg.global_apt_https_proxy) and (
        cfg.ua_apt_http_proxy or cfg.ua_apt_https_proxy
    ):
        print(messages.CLI_CONFIG_GLOBAL_XOR_UA_PROXY)


@cli_util.assert_root
def action_config_set(args, *, cfg, **kwargs):
    """Perform the 'config set' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.cli import get_parser

    parser = get_parser()
    try:
        set_key, set_value = args.key_value_pair.split("=")
    except ValueError:
        parser.print_help_for_command("config set")
        raise exceptions.GenericInvalidFormat(
            expected="<key>=<value>", actual=args.key_value_pair
        )
    if set_key not in config.UA_CONFIGURABLE_KEYS:
        parser.print_help_for_command("config set")
        raise exceptions.InvalidArgChoice(
            arg="<key>", choices=", ".join(config.UA_CONFIGURABLE_KEYS)
        )
    if not set_value.strip():
        parser.print_help_for_command("config set")
        raise exceptions.EmptyConfigValue(arg=set_key)
    if set_key in ("http_proxy", "https_proxy"):
        protocol_type = set_key.split("_")[0]
        if protocol_type == "http":
            validate_url = http.PROXY_VALIDATION_SNAP_HTTP_URL
        else:
            validate_url = http.PROXY_VALIDATION_SNAP_HTTPS_URL
        http.validate_proxy(protocol_type, set_value, validate_url)

        kwargs = {set_key: set_value}
        configure_snap_proxy(**kwargs)
        # Only set livepatch proxy if livepatch is enabled
        entitlement = entitlements.livepatch.LivepatchEntitlement(cfg)
        livepatch_status, _ = entitlement.application_status()
        if livepatch_status == ApplicationStatus.ENABLED:
            configure_livepatch_proxy(**kwargs)
    elif set_key in cfg.ua_scoped_proxy_options:
        protocol_type = set_key.split("_")[2]
        if protocol_type == "http":
            validate_url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = http.PROXY_VALIDATION_APT_HTTPS_URL
        http.validate_proxy(protocol_type, set_value, validate_url)
        unset_current = bool(
            cfg.global_apt_http_proxy or cfg.global_apt_https_proxy
        )
        if unset_current:
            print(
                messages.WARNING_APT_PROXY_OVERWRITE.format(
                    current_proxy="pro scoped apt", previous_proxy="global apt"
                )
            )
        cli_util.configure_apt_proxy(
            cfg, AptProxyScope.UACLIENT, set_key, set_value
        )
        cfg.global_apt_http_proxy = None
        cfg.global_apt_https_proxy = None

    elif set_key in (
        cfg.deprecated_global_scoped_proxy_options
        + cfg.global_scoped_proxy_options
    ):
        # setup_apt_proxy is destructive for unprovided values. Source complete
        # current config values from uaclient.conf before applying set_value.

        protocol_type = "https" if "https" in set_key else "http"
        if protocol_type == "http":
            validate_url = http.PROXY_VALIDATION_APT_HTTP_URL
        else:
            validate_url = http.PROXY_VALIDATION_APT_HTTPS_URL

        if set_key in cfg.deprecated_global_scoped_proxy_options:
            print(
                messages.WARNING_CONFIG_FIELD_RENAME.format(
                    old="apt_{}_proxy".format(protocol_type),
                    new="global_apt_{}_proxy".format(protocol_type),
                )
            )
            set_key = "global_" + set_key

        http.validate_proxy(protocol_type, set_value, validate_url)

        unset_current = bool(cfg.ua_apt_http_proxy or cfg.ua_apt_https_proxy)

        if unset_current:
            print(
                messages.WARNING_APT_PROXY_OVERWRITE.format(
                    current_proxy="global apt", previous_proxy="pro scoped apt"
                )
            )
        cli_util.configure_apt_proxy(
            cfg, AptProxyScope.GLOBAL, set_key, set_value
        )
        cfg.ua_apt_http_proxy = None
        cfg.ua_apt_https_proxy = None

    elif set_key in (
        "update_messaging_timer",
        "metering_timer",
    ):
        try:
            set_value = int(set_value)
            if set_value < 0:
                raise ValueError("Invalid interval for {}".format(set_key))
        except ValueError:
            parser.print_help_for_command("config set")
            # More readable in the CLI, without breaking the line in the logs
            print("")
            raise exceptions.InvalidPosIntConfigValue(
                key=set_key, value=set_value
            )
    elif set_key == "apt_news":
        set_value = set_value.lower() == "true"
        if set_value:
            apt_news.update_apt_news(cfg)
        else:
            state_files.apt_news_contents_file.delete()

    setattr(cfg, set_key, set_value)


@cli_util.assert_root
def action_config_unset(args, *, cfg, **kwargs):
    """Perform the 'config unset' action.

    @return: 0 on success, 1 otherwise
    """
    from uaclient.cli import get_parser

    if args.key not in config.UA_CONFIGURABLE_KEYS:
        parser = get_parser()
        parser.print_help_for_command("config unset")
        raise exceptions.InvalidArgChoice(
            arg="<key>", choices=", ".join(config.UA_CONFIGURABLE_KEYS)
        )
    if args.key in ("http_proxy", "https_proxy"):
        protocol_type = args.key.split("_")[0]
        unconfigure_snap_proxy(protocol_type=protocol_type)
        # Only unset livepatch proxy if livepatch is enabled
        entitlement = entitlements.livepatch.LivepatchEntitlement(cfg)
        livepatch_status, _ = entitlement.application_status()
        if livepatch_status == ApplicationStatus.ENABLED:
            unconfigure_livepatch_proxy(protocol_type=protocol_type)
    elif args.key in cfg.ua_scoped_proxy_options:
        cli_util.configure_apt_proxy(
            cfg, AptProxyScope.UACLIENT, args.key, None
        )
    elif args.key in (
        cfg.deprecated_global_scoped_proxy_options
        + cfg.global_scoped_proxy_options
    ):
        if args.key in cfg.deprecated_global_scoped_proxy_options:
            protocol_type = "https" if "https" in args.key else "http"
            event.info(
                messages.WARNING_CONFIG_FIELD_RENAME.format(
                    old="apt_{}_proxy".format(protocol_type),
                    new="global_apt_{}_proxy".format(protocol_type),
                )
            )
            args.key = "global_" + args.key
        cli_util.configure_apt_proxy(cfg, AptProxyScope.GLOBAL, args.key, None)

    setattr(cfg, args.key, None)
    return 0


show_subcommand = ProCommand(
    "show",
    help=messages.CLI_CONFIG_SHOW_DESC,
    description=messages.CLI_CONFIG_SHOW_DESC,
    action=action_config_show,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "key", help=messages.CLI_CONFIG_SHOW_KEY, nargs="?"
                )
            ]
        )
    ],
)

set_subcommand = ProCommand(
    "set",
    help=messages.CLI_CONFIG_SET_DESC,
    description=messages.CLI_CONFIG_SET_DESC,
    action=action_config_set,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "key_value_pair",
                    help=(
                        messages.CLI_CONFIG_SET_KEY_VALUE.format(
                            options=", ".join(config.UA_CONFIGURABLE_KEYS)
                        )
                    ),
                )
            ]
        )
    ],
)

unset_subcommand = ProCommand(
    "unset",
    help=messages.CLI_CONFIG_UNSET_DESC,
    description=messages.CLI_CONFIG_UNSET_DESC,
    action=action_config_unset,
    argument_groups=[
        ProArgumentGroup(
            arguments=[
                ProArgument(
                    "key",
                    help=(
                        messages.CLI_CONFIG_UNSET_KEY.format(
                            options=", ".join(config.UA_CONFIGURABLE_KEYS)
                        )
                    ),
                    metavar="key",
                )
            ]
        )
    ],
)

config_command = ProCommand(
    "config",
    help=messages.CLI_ROOT_CONFIG,
    description=messages.CLI_CONFIG_DESC,
    action=action_config,
    help_category=HelpCategory.OTHER,
    subcommands=[show_subcommand, set_subcommand, unset_subcommand],
)
