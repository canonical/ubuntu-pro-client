from functools import wraps

from uaclient import entitlements, exceptions, lock, util
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached


def assert_lock_file(lock_holder=None):
    """Decorator asserting exclusive access to lock file"""

    def wrapper(f):
        @wraps(f)
        def new_f(*args, cfg, **kwargs):
            with lock.SpinLock(lock_holder=lock_holder, sleep_time=1):
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
            raise exceptions.AlreadyAttachedError(
                account_name=cfg.machine_token_file.account.get("name", "")
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
            valid_service=", ".join(entitlements_found)
        )
    else:
        raise exceptions.UnattachedInvalidServicesError(
            operation=command,
            invalid_service=", ".join(entitlements_not_found),
            service_msg="",
        )
