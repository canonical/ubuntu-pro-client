from functools import wraps
from typing import Optional

from uaclient import (
    actions,
    api,
    daemon,
    entitlements,
    event_logger,
    exceptions,
    lock,
    messages,
    status,
    util,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.apt import AptProxyScope, setup_apt_proxy
from uaclient.config import UAConfig
from uaclient.files import machine_token

event = event_logger.get_event_logger()


class CLIEnableDisableProgress(api.AbstractProgress):
    def __init__(self, *, assume_yes: bool):
        self.is_interactive = not assume_yes
        self.assume_yes = assume_yes

    def progress(
        self,
        *,
        total_steps: int,
        done_steps: int,
        previous_step_message: Optional[str],
        current_step_message: Optional[str]
    ):
        if current_step_message is not None:
            print(current_step_message)

    def _on_event(self, event: str, payload):
        if event == "info":
            print(payload)
        elif event == "message_operation":
            if not util.handle_message_operations(payload, self.assume_yes):
                raise exceptions.PromptDeniedError()


def _null_print(*args, **kwargs):
    pass


def create_interactive_only_print_function(json_output: bool):
    if json_output:
        return _null_print
    else:
        return print


def assert_lock_file(lock_holder=None):
    """Decorator asserting exclusive access to lock file"""

    def wrapper(f):
        @wraps(f)
        def new_f(*args, cfg, **kwargs):
            with lock.RetryLock(lock_holder=lock_holder, sleep_time=1):
                retval = f(*args, cfg=cfg, **kwargs)
            return retval

        return new_f

    return wrapper


def assert_root(f):
    """Decorator asserting root user"""

    @wraps(f)
    def new_f(*args, **kwargs):
        if not util.we_are_currently_root():
            raise exceptions.NonRootUserError()
        else:
            return f(*args, **kwargs)

    return new_f


def verify_json_format_args(f):
    """Decorator to verify if correct params are used for json format"""

    @wraps(f)
    def new_f(cmd_args, *args, **kwargs):
        if not cmd_args:
            return f(cmd_args, *args, **kwargs)

        if cmd_args.format == "json" and not cmd_args.assume_yes:
            raise exceptions.CLIJSONFormatRequireAssumeYes()
        else:
            return f(cmd_args, *args, **kwargs)

    return new_f


def assert_attached(raise_custom_error_function=None):
    """Decorator asserting attached config.
    :param msg_function: Optional function to generate a custom message
    if raising an UnattachedError
    """

    def wrapper(f):
        @wraps(f)
        def new_f(args, cfg, **kwargs):
            if not _is_attached(cfg).is_attached:
                if raise_custom_error_function:
                    command = getattr(args, "command", "")
                    service_names = getattr(args, "service", "")
                    raise_custom_error_function(
                        command=command, service_names=service_names, cfg=cfg
                    )
                else:
                    raise exceptions.UnattachedError()
            return f(args, cfg=cfg, **kwargs)

        return new_f

    return wrapper


def assert_not_attached(f):
    """Decorator asserting unattached config."""

    @wraps(f)
    def new_f(args, cfg, **kwargs):
        if _is_attached(cfg).is_attached:
            machine_token_file = machine_token.get_machine_token_file()
            raise exceptions.AlreadyAttachedError(
                account_name=machine_token_file.account.get("name", "")
            )
        return f(args, cfg=cfg, **kwargs)

    return new_f


def _raise_enable_disable_unattached_error(command, service_names, cfg):
    """Raises a custom error for enable/disable commands when unattached.

    Takes into consideration if the services exist or not, and notify the user
    accordingly."""
    (
        entitlements_found,
        entitlements_not_found,
    ) = entitlements.get_valid_entitlement_names(names=service_names, cfg=cfg)
    if entitlements_found and entitlements_not_found:
        raise exceptions.UnattachedMixedServicesError(
            valid_service=", ".join(entitlements_found),
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="",
        )
    elif entitlements_found:
        raise exceptions.UnattachedValidServicesError(
            valid_service=", ".join(entitlements_found), operation=command
        )
    else:
        raise exceptions.UnattachedInvalidServicesError(
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="",
        )


def post_cli_attach(cfg: UAConfig) -> None:
    machine_token_file = machine_token.get_machine_token_file(cfg)
    contract_name = machine_token_file.contract_name

    if contract_name:
        event.info(
            messages.ATTACH_SUCCESS_TMPL.format(contract_name=contract_name)
        )
    else:
        event.info(messages.ATTACH_SUCCESS_NO_CONTRACT_NAME)

    daemon.stop()
    daemon.cleanup(cfg)

    status_dict, _ret = actions.status(cfg)
    output = status.format_tabular(status_dict)
    event.info(util.handle_unicode_characters(output))
    event.process_events()


def configure_apt_proxy(
    cfg: UAConfig,
    scope: AptProxyScope,
    set_key: str,
    set_value: Optional[str],
) -> None:
    """
    Handles setting part the apt proxies - global and uaclient scoped proxies
    """
    if scope == AptProxyScope.GLOBAL:
        http_proxy = cfg.global_apt_http_proxy
        https_proxy = cfg.global_apt_https_proxy
    elif scope == AptProxyScope.UACLIENT:
        http_proxy = cfg.ua_apt_http_proxy
        https_proxy = cfg.ua_apt_https_proxy
    if "https" in set_key:
        https_proxy = set_value
    else:
        http_proxy = set_value
    setup_apt_proxy(
        http_proxy=http_proxy, https_proxy=https_proxy, proxy_scope=scope
    )
