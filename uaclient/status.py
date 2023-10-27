import copy
import logging
import sys
import textwrap
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from uaclient import (
    event_logger,
    exceptions,
    livepatch,
    messages,
    util,
    version,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UA_CONFIGURABLE_KEYS, UAConfig
from uaclient.contract import get_available_resources, get_contract_information
from uaclient.defaults import ATTACH_FAIL_DATE_FORMAT, PRINT_WRAP_WIDTH
from uaclient.entitlements import entitlement_factory
from uaclient.entitlements.entitlement_status import (
    ContractStatus,
    UserFacingAvailability,
    UserFacingConfigStatus,
    UserFacingStatus,
)
from uaclient.files import notices, state_files
from uaclient.files.notices import Notice
from uaclient.messages import TxtColor

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


ESSENTIAL = "essential"
STANDARD = "standard"
ADVANCED = "advanced"

# Turns machine-enum value (english) into human value (potentially translated)
# Also colorizes status output for terminal
STATUS_HUMANIZE_COLORIZE = {
    UserFacingStatus.ACTIVE.value: (
        TxtColor.OKGREEN + messages.STATUS_STATUS_ENABLED + TxtColor.ENDC
    ),
    UserFacingStatus.INACTIVE.value: (
        TxtColor.FAIL + messages.STATUS_STATUS_DISABLED + TxtColor.ENDC
    ),
    UserFacingStatus.INAPPLICABLE.value: (
        TxtColor.DISABLEGREY
        + messages.STATUS_STATUS_INAPPLICABLE
        + TxtColor.ENDC
    ),
    UserFacingStatus.UNAVAILABLE.value: (
        TxtColor.DISABLEGREY
        + messages.STATUS_STATUS_UNAVAILABLE
        + TxtColor.ENDC
    ),
    UserFacingStatus.WARNING.value: (
        TxtColor.WARNINGYELLOW + messages.STATUS_STATUS_WARNING + TxtColor.ENDC
    ),
    ContractStatus.ENTITLED.value: (
        TxtColor.OKGREEN + messages.STATUS_ENTITLED_ENTITLED + TxtColor.ENDC
    ),
    ContractStatus.UNENTITLED.value: (
        TxtColor.DISABLEGREY
        + messages.STATUS_ENTITLED_UNENTITLED
        + TxtColor.ENDC
    ),
    ESSENTIAL: TxtColor.OKGREEN
    + messages.STATUS_SUPPORT_ESSENTIAL
    + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN
    + messages.STATUS_SUPPORT_STANDARD
    + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN
    + messages.STATUS_SUPPORT_ADVANCED
    + TxtColor.ENDC,
}


STATUS_UNATTACHED_TMPL = "{name: <17}{available: <11}{description}"

STATUS_SIMULATED_TMPL = """\
{name: <17}{available: <11}{entitled: <11}{auto_enabled: <16}{description}"""

STATUS_HEADER = "{name: <17}{entitled: <10}{status: <13}{description}".format(
    name=messages.STATUS_SERVICE,
    entitled=messages.STATUS_ENTITLED,
    status=messages.STATUS_STATUS,
    description=messages.STATUS_DESCRIPTION,
)
# The widths listed below for entitled and status are actually 9 characters
# less than reality because we colorize the values in entitled and status
# columns. Colorizing has an opening and closing set of unprintable characters
# that factor into formats len() calculations
STATUS_TMPL = "{name: <17}{entitled: <19}{status: <22}{description}"
VARIANT_STATUS_TMPL = (
    "{marker} {name: <15}{entitled: <19}{status: <22}{description}"
)

DEFAULT_STATUS = {
    "_doc": "Content provided in json response is currently considered"
    " Experimental and may change",
    "_schema_version": "0.1",
    "version": version.get_version(),
    "machine_id": None,
    "attached": False,
    "effective": None,
    "expires": None,  # TODO Will this break something?
    "origin": None,
    "services": [],
    "execution_status": UserFacingConfigStatus.INACTIVE.value,
    "execution_details": messages.NO_ACTIVE_OPERATIONS,
    "features": {},
    "notices": [],
    "contract": {
        "id": "",
        "name": "",
        "created_at": "",
        "products": [],
        "tech_support_level": UserFacingStatus.INAPPLICABLE.value,
    },
    "account": {
        "name": "",
        "id": "",
        "created_at": "",
        "external_account_ids": [],
    },
    "simulated": False,
}  # type: Dict[str, Any]


def _get_blocked_by_services(ent):
    return [
        {
            "name": service.entitlement.name
            if not service.entitlement.is_variant
            else service.entitlement.variant_name,
            "reason_code": service.named_msg.name,
            "reason": service.named_msg.msg,
        }
        for service in ent.blocking_incompatible_services()
    ]


def _attached_service_status(
    ent, inapplicable_resources, cfg
) -> Dict[str, Any]:
    warning = None
    status_details = ""
    description_override = ent.status_description_override()
    contract_status = ent.contract_status()
    available = "no" if ent.name in inapplicable_resources else "yes"
    variants = {}

    if contract_status == ContractStatus.UNENTITLED:
        ent_status = UserFacingStatus.UNAVAILABLE
    else:
        if ent.name in inapplicable_resources:
            ent_status = UserFacingStatus.INAPPLICABLE
            description_override = inapplicable_resources[ent.name]
        else:
            ent_status, details = ent.user_facing_status()
            if ent_status == UserFacingStatus.WARNING:
                warning = {
                    "code": details.name,
                    "message": details.msg,
                }
            elif details:
                status_details = details.msg

            if ent_status == UserFacingStatus.INAPPLICABLE:
                available = "no"

            if ent.variants:
                variants = {
                    variant_name: _attached_service_status(
                        variant_cls(cfg=cfg),
                        inapplicable_resources,
                        cfg,
                    )
                    for variant_name, variant_cls in ent.variants.items()
                }

    blocked_by = _get_blocked_by_services(ent)

    service_status = {
        "name": ent.presentation_name,
        "description": ent.description,
        "entitled": contract_status.value,
        "status": ent_status.value,
        "status_details": status_details,
        "description_override": description_override,
        "available": available,
        "blocked_by": blocked_by,
        "warning": warning,
    }

    if not ent.is_variant:
        service_status["variants"] = variants

    return service_status


def _attached_status(cfg: UAConfig) -> Dict[str, Any]:
    """Return configuration of attached status as a dictionary."""
    notices.remove(Notice.AUTO_ATTACH_RETRY_FULL_NOTICE)
    notices.remove(Notice.AUTO_ATTACH_RETRY_TOTAL_FAILURE)

    response = copy.deepcopy(DEFAULT_STATUS)
    machineTokenInfo = cfg.machine_token["machineTokenInfo"]
    contractInfo = machineTokenInfo["contractInfo"]
    tech_support_level = UserFacingStatus.INAPPLICABLE.value
    response.update(
        {
            "machine_id": machineTokenInfo["machineId"],
            "attached": True,
            "origin": contractInfo.get("origin"),
            "notices": notices.list() or [],
            "contract": {
                "id": contractInfo["id"],
                "name": contractInfo["name"],
                "created_at": contractInfo.get("createdAt", ""),
                "products": contractInfo.get("products", []),
                "tech_support_level": tech_support_level,
            },
            "account": {
                "name": cfg.machine_token_file.account["name"],
                "id": cfg.machine_token_file.account["id"],
                "created_at": cfg.machine_token_file.account.get(
                    "createdAt", ""
                ),
                "external_account_ids": cfg.machine_token_file.account.get(
                    "externalAccountIDs", []
                ),
            },
        }
    )
    if contractInfo.get("effectiveTo"):
        response["expires"] = cfg.machine_token_file.contract_expiry_datetime
    if contractInfo.get("effectiveFrom"):
        response["effective"] = contractInfo["effectiveFrom"]

    resources = cfg.machine_token.get("availableResources")
    if not resources:
        resources = get_available_resources(cfg)

    inapplicable_resources = {
        resource["name"]: resource.get("description")
        for resource in sorted(resources, key=lambda x: x.get("name", ""))
        if not resource.get("available")
    }

    for resource in resources:
        try:
            ent_cls = entitlement_factory(
                cfg=cfg, name=resource.get("name", "")
            )
        except exceptions.EntitlementNotFoundError:
            continue
        ent = ent_cls(cfg)
        response["services"].append(
            _attached_service_status(ent, inapplicable_resources, cfg)
        )
    response["services"].sort(key=lambda x: x.get("name", ""))

    support = cfg.machine_token_file.entitlements.get("support", {}).get(
        "entitlement"
    )
    if support:
        supportLevel = support.get("affordances", {}).get("supportLevel")
        if supportLevel:
            response["contract"]["tech_support_level"] = supportLevel
    return response


def _unattached_status(cfg: UAConfig) -> Dict[str, Any]:
    """Return unattached status as a dict."""

    response = copy.deepcopy(DEFAULT_STATUS)

    resources = get_available_resources(cfg)
    for resource in resources:
        if resource.get("available"):
            available = UserFacingAvailability.AVAILABLE.value
        else:
            available = UserFacingAvailability.UNAVAILABLE.value
        try:
            ent_cls = entitlement_factory(
                cfg=cfg, name=resource.get("name", "")
            )

        except exceptions.EntitlementNotFoundError:
            LOG.debug(
                "Ignoring availability of unknown service %s from contract "
                "server",
                resource.get("name", "without a 'name' key"),
            )
            continue

        # FIXME: we need a better generic unattached availability status
        # that takes into account local information.
        if (
            ent_cls.name == "livepatch"
            and livepatch.on_supported_kernel()
            == livepatch.LivepatchSupport.UNSUPPORTED
        ):
            lp = ent_cls(cfg)
            descr_override = lp.status_description_override()
        else:
            descr_override = None

        response["services"].append(
            {
                "name": resource.get("presentedAs", resource["name"]),
                "description": ent_cls.description,
                "description_override": descr_override,
                "available": available,
            }
        )
    response["services"].sort(key=lambda x: x.get("name", ""))

    return response


def _handle_beta_resources(cfg, show_all, response) -> Dict[str, Any]:
    """Remove beta services from response dict if needed"""
    config_allow_beta = util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.allow_beta"
    )
    show_all |= config_allow_beta
    if show_all:
        return response

    new_response = copy.deepcopy(response)

    released_resources = []
    for resource in new_response.get("services", {}):
        resource_name = resource["name"]
        try:
            ent_cls = entitlement_factory(cfg=cfg, name=resource_name)
        except exceptions.EntitlementNotFoundError:
            """
            Here we cannot know the status of a service,
            since it is not listed as a valid entitlement.
            Therefore, we keep this service in the list, since
            we cannot validate if it is a beta service or not.
            """
            released_resources.append(resource)
            continue

        enabled_status = UserFacingStatus.ACTIVE.value
        if not ent_cls.is_beta or resource.get("status", "") == enabled_status:
            released_resources.append(resource)

    if released_resources:
        new_response["services"] = released_resources

    return new_response


def _get_config_status(cfg) -> Dict[str, Any]:
    """Return a dict with execution_status, execution_details and notices.

    Values for execution_status will be one of UserFacingConfigStatus
    enum:
        inactive, active, reboot-required
    execution_details will provide more details about that state.
    notices is a list of tuples with label and description items.
    """
    userStatus = UserFacingConfigStatus
    status_val = userStatus.INACTIVE.value
    status_desc = messages.NO_ACTIVE_OPERATIONS
    (lock_pid, lock_holder) = cfg.check_lock_info()
    notices_list = notices.list() or []
    if lock_pid > 0:
        status_val = userStatus.ACTIVE.value
        status_desc = messages.LOCK_HELD.format(
            pid=lock_pid, lock_holder=lock_holder
        )
    elif state_files.reboot_cmd_marker_file.is_present:
        status_val = userStatus.REBOOTREQUIRED.value
        operation = "configuration changes"
        status_desc = messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
            operation=operation
        )
    ret = {
        "execution_status": status_val,
        "execution_details": status_desc,
        "notices": notices_list,
        "config_path": cfg.cfg_path,
        "config": cfg.cfg,
        "features": cfg.features,
    }
    # LP: #2004280 maintain backwards compatibility
    ua_config = {}
    for key in UA_CONFIGURABLE_KEYS:
        if hasattr(cfg, key):
            ua_config[key] = getattr(cfg, key)
    ret["config"]["ua_config"] = ua_config

    return ret


def status(cfg: UAConfig, show_all: bool = False) -> Dict[str, Any]:
    """Return status as a dict, using a cache for non-root users

    When unattached, get available resources from the contract service
    to report detailed availability of different resources for this
    machine.

    Write the status-cache when called by root.
    """
    if _is_attached(cfg).is_attached:
        response = _attached_status(cfg)
    else:
        response = _unattached_status(cfg)

    response.update(_get_config_status(cfg))

    if util.we_are_currently_root():
        cfg.write_cache("status-cache", response)

    response = _handle_beta_resources(cfg, show_all, response)

    if not show_all:
        available_services = [
            service
            for service in response.get("services", [])
            if service.get("available", "yes") == "yes"
        ]
        response["services"] = available_services

    return response


def _get_entitlement_information(
    entitlements: List[Dict[str, Any]], entitlement_name: str
) -> Dict[str, Any]:
    """Extract information from the entitlements array."""
    for entitlement in entitlements:
        if entitlement.get("type") == entitlement_name:
            return {
                "entitled": "yes" if entitlement.get("entitled") else "no",
                "auto_enabled": "yes"
                if entitlement.get("obligations", {}).get("enableByDefault")
                else "no",
                "affordances": entitlement.get("affordances", {}),
            }
    return {"entitled": "no", "auto_enabled": "no", "affordances": {}}


def simulate_status(
    cfg, token: str, show_all: bool = False
) -> Tuple[Dict[str, Any], int]:
    """Get a status dictionary based on a token.

    Returns a tuple with the status dictionary and an integer value - 0 for
    success, 1 for failure
    """
    ret = 0
    response = copy.deepcopy(DEFAULT_STATUS)

    try:
        contract_information = get_contract_information(cfg, token)
    except exceptions.ContractAPIError as e:
        if hasattr(e, "code") and e.code == 401:
            raise exceptions.AttachInvalidTokenError()
        raise e

    contract_info = contract_information.get("contractInfo", {})
    account_info = contract_information.get("accountInfo", {})

    response.update(
        {
            "contract": {
                "id": contract_info.get("id", ""),
                "name": contract_info.get("name", ""),
                "created_at": contract_info.get("createdAt", ""),
                "products": contract_info.get("products", []),
            },
            "account": {
                "name": account_info.get("name", ""),
                "id": account_info.get("id"),
                "created_at": account_info.get("createdAt", ""),
                "external_account_ids": account_info.get(
                    "externalAccountIDs", []
                ),
            },
            "simulated": True,
        }
    )

    now = datetime.now(timezone.utc)
    if contract_info.get("effectiveTo"):
        response["expires"] = contract_info.get("effectiveTo")
        expiration_datetime = response["expires"]
        delta = expiration_datetime - now
        if delta.total_seconds() <= 0:
            message = messages.E_ATTACH_FORBIDDEN_EXPIRED.format(
                contract_id=response["contract"]["id"],
                date=expiration_datetime.strftime(ATTACH_FAIL_DATE_FORMAT),
            )
            event.error(error_msg=message.msg, error_code=message.name)
            event.info(
                messages.STATUS_TOKEN_NOT_VALID + "\n" + message.msg + "\n"
            )
            ret = 1
    if contract_info.get("effectiveFrom"):
        response["effective"] = contract_info.get("effectiveFrom")
        effective_datetime = response["effective"]
        delta = now - effective_datetime
        if delta.total_seconds() <= 0:
            message = messages.E_ATTACH_FORBIDDEN_NOT_YET.format(
                contract_id=response["contract"]["id"],
                date=effective_datetime.strftime(ATTACH_FAIL_DATE_FORMAT),
            )
            event.error(error_msg=message.msg, error_code=message.name)
            event.info(
                messages.STATUS_TOKEN_NOT_VALID + "\n" + message.msg + "\n"
            )
            ret = 1

    resources = get_available_resources(cfg)
    inapplicable_resources = [
        resource["name"]
        for resource in sorted(resources, key=lambda x: x["name"])
        if not resource["available"]
    ]

    entitlements = contract_info.get("resourceEntitlements", [])
    for resource in resources:
        entitlement_name = resource.get("name", "")
        try:
            ent_cls = entitlement_factory(cfg=cfg, name=entitlement_name)
        except exceptions.EntitlementNotFoundError:
            continue
        ent = ent_cls(cfg=cfg)
        entitlement_information = _get_entitlement_information(
            entitlements, entitlement_name
        )
        response["services"].append(
            {
                "name": resource.get("presentedAs", ent.name),
                "description": ent.description,
                "entitled": entitlement_information["entitled"],
                "auto_enabled": entitlement_information["auto_enabled"],
                "available": "yes"
                if ent.name not in inapplicable_resources
                else "no",
            }
        )
    response["services"].sort(key=lambda x: x.get("name", ""))

    support = _get_entitlement_information(entitlements, "support")
    if support["entitled"]:
        supportLevel = support["affordances"].get("supportLevel")
        if supportLevel:
            response["contract"]["tech_support_level"] = supportLevel

    response.update(_get_config_status(cfg))
    response = _handle_beta_resources(cfg, show_all, response)

    if not show_all:
        available_services = [
            service
            for service in response.get("services", [])
            if service.get("available", "yes") == "yes"
        ]
        response["services"] = available_services

    return response, ret


def for_human_colorized(string: str) -> str:
    """Return colorized string if using a tty, else original string."""
    return (
        STATUS_HUMANIZE_COLORIZE.get(string, string)
        if sys.stdout.isatty()
        else string
    )


def colorize_commands(commands: List[List[str]]) -> str:
    content = ""
    for cmd in commands:
        if content:
            content += " && "
        content += " ".join(cmd)
    # subtract 4 from print width to account for leading and trailing braces
    # and spaces
    wrapped_content = " \\\n".join(
        textwrap.wrap(
            content, width=(PRINT_WRAP_WIDTH - 4), subsequent_indent="  "
        )
    )
    if "\n" in wrapped_content:
        prefix = "{\n  "
        suffix = "\n}"
    else:
        prefix = "{ "
        suffix = " }"
    return "{color}{prefix}{content}{suffix}{end}".format(
        color=TxtColor.DISABLEGREY,
        prefix=prefix,
        content=wrapped_content,
        suffix=suffix,
        end=TxtColor.ENDC,
    )


def get_section_column_content(
    column_data: List[Tuple[str, str]], header: Optional[str] = None
) -> List[str]:
    """Return a list of content lines to print to console for a section

    Content lines will be center-aligned based on max value length of first
    column.
    """
    content = []
    if header:
        content.append(header)
    template_length = max([len(pair[0]) for pair in column_data])
    if template_length > 0:
        template = "{{:>{}}}: {{}}".format(template_length)
        content.extend([template.format(*pair) for pair in column_data])
    else:
        # Then we have an empty "label" column and only descriptions
        content.extend([pair[1] for pair in column_data])
    return content


def format_expires(expires: Optional[datetime]) -> str:
    if expires is None:
        return messages.STATUS_CONTRACT_EXPIRES_UNKNOWN
    try:
        expires = expires.astimezone()
    except Exception:
        pass
    return expires.strftime("%c %Z")


def format_tabular(status: Dict[str, Any], show_all: bool = False) -> str:
    """Format status dict for tabular output."""
    if not status.get("attached"):
        if status.get("simulated"):
            if not status.get("services", None):
                return messages.STATUS_NO_SERVICES_AVAILABLE

            content = [
                STATUS_SIMULATED_TMPL.format(
                    name=messages.STATUS_SERVICE,
                    available=messages.STATUS_AVAILABLE,
                    entitled=messages.STATUS_ENTITLED,
                    auto_enabled=messages.STATUS_AUTO_ENABLED,
                    description=messages.STATUS_DESCRIPTION,
                )
            ]
            for service in status.get("services", []):
                content.append(STATUS_SIMULATED_TMPL.format(**service))

            return "\n".join(content)

        if not status.get("services", None):
            content = [messages.STATUS_NO_SERVICES_AVAILABLE]
        else:
            content = [
                STATUS_UNATTACHED_TMPL.format(
                    name=messages.STATUS_SERVICE,
                    available=messages.STATUS_AVAILABLE,
                    description=messages.STATUS_DESCRIPTION,
                )
            ]
            for service in status.get("services", []):
                descr_override = service.get("description_override")
                description = (
                    descr_override
                    if descr_override
                    else service.get("description", "")
                )
                available = (
                    messages.STANDALONE_YES
                    if service.get("available") == "yes"
                    else messages.STANDALONE_NO
                )
                content.append(
                    STATUS_UNATTACHED_TMPL.format(
                        name=service.get("name", ""),
                        available=available,
                        description=description,
                    )
                )

        notices = status.get("notices")
        if notices:
            content.append(messages.STATUS_NOTICES)
            content.extend(notices)

        if status.get("features"):
            content.append("\n" + messages.STATUS_FEATURES)
            for key, value in sorted(status.get("features", {}).items()):
                content.append("{}: {}".format(key, value))

        if not show_all:
            content.extend(["", messages.STATUS_ALL_HINT])

        content.extend(["", messages.E_UNATTACHED.msg])
        if (
            livepatch.on_supported_kernel()
            == livepatch.LivepatchSupport.UNSUPPORTED
        ):
            content.extend(
                ["", messages.LIVEPATCH_KERNEL_NOT_SUPPORTED_UNATTACHED]
            )
        return "\n".join(content)

    service_warnings = []
    has_variants = False
    if not status.get("services", None):
        content = [messages.STATUS_NO_SERVICES_AVAILABLE]
    else:
        content = [STATUS_HEADER]
        for service_status in status.get("services", []):
            entitled = service_status.get("entitled", "")
            descr_override = service_status.get("description_override")
            description = (
                descr_override
                if descr_override
                else service_status.get("description", "")
            )
            fmt_args = {
                "name": service_status.get("name", ""),
                "entitled": for_human_colorized(entitled),
                "status": for_human_colorized(
                    service_status.get("status", "")
                ),
                "description": description,
            }
            warning = service_status.get("warning", None)
            if warning is not None:
                warning_message = warning.get("message", None)
                if warning_message is not None:
                    service_warnings.append(warning_message)
            variants = service_status.get("variants")
            if variants and not show_all:
                has_variants = True
                fmt_args["name"] = "{}*".format(fmt_args["name"])

            content.append(STATUS_TMPL.format(**fmt_args))
            if variants and show_all:
                for idx, (_, variant) in enumerate(variants.items()):
                    marker = "├" if idx != len(variants) - 1 else "└"
                    content.append(
                        VARIANT_STATUS_TMPL.format(
                            marker=marker,
                            name=variant.get("name"),
                            entitled=for_human_colorized(
                                variant.get("entitled", "")
                            ),
                            status=for_human_colorized(
                                variant.get("status", "")
                            ),
                            description=variant.get("description", ""),
                        )
                    )

    if has_variants:
        content.append("")
        content.append(messages.STATUS_SERVICE_HAS_VARIANTS)

    if status.get("notices") or len(service_warnings) > 0:
        content.append("")
        content.append(messages.STATUS_NOTICES)
        notices = status.get("notices")
        if notices:
            content.extend(notices)
        if len(service_warnings) > 0:
            content.extend(service_warnings)

    if status.get("features"):
        content.append("\n" + messages.STATUS_FEATURES)
        for key, value in sorted(status.get("features", {}).items()):
            content.append("{}: {}".format(key, value))
    content.append("")

    if not show_all:
        if has_variants:
            content.append(messages.STATUS_ALL_HINT_WITH_VARIANTS)
        else:
            content.append(messages.STATUS_ALL_HINT)

    content.append(
        messages.STATUS_FOOTER_ENABLE_SERVICES_WITH.format(
            command="pro enable <service>"
        )
    )
    pairs = []

    account_name = status.get("account", {}).get("name", "unknown")
    if account_name:
        pairs.append((messages.STATUS_FOOTER_ACCOUNT, account_name))

    contract_name = status.get("contract", {}).get("name", "unknown")
    if contract_name:
        pairs.append((messages.STATUS_FOOTER_SUBSCRIPTION, contract_name))

    if status.get("origin", None) != "free":
        pairs.append(
            (
                messages.STATUS_FOOTER_VALID_UNTIL,
                format_expires(status.get("expires")),
            )
        )
        tech_support_level = status.get("contract", {}).get(
            "tech_support_level", "unknown"
        )
        pairs.append(
            (
                messages.STATUS_FOOTER_SUPPORT_LEVEL,
                for_human_colorized(tech_support_level),
            )
        )

    if pairs:
        content.append("")
        content.extend(get_section_column_content(column_data=pairs))

    return "\n".join(content)


def help(cfg, name):
    """Return help information from an uaclient service as a dict

    :param name: Name of the service for which to return help data.

    :raises: UbuntuProError when no help is available.
    """
    resources = get_available_resources(cfg)
    help_resource = None

    # We are using an OrderedDict here to guarantee
    # that if we need to print the result of this
    # dict, the order of insertion will always be respected
    response_dict = OrderedDict()
    response_dict["name"] = name

    for resource in resources:
        if resource["name"] == name or resource.get("presentedAs") == name:
            try:
                help_ent_cls = entitlement_factory(
                    cfg=cfg, name=resource["name"]
                )
            except exceptions.EntitlementNotFoundError:
                continue
            help_resource = resource
            help_ent = help_ent_cls(cfg)
            break

    if help_resource is None:
        raise exceptions.NoHelpContent(name=name)

    if _is_attached(cfg).is_attached:
        service_status = _attached_service_status(help_ent, {}, cfg)
        status_msg = service_status["status"]

        response_dict["entitled"] = service_status["entitled"]
        response_dict["status"] = status_msg

        if status_msg == "enabled" and help_ent_cls.is_beta:
            response_dict["beta"] = True

    else:
        if help_resource["available"]:
            available = UserFacingAvailability.AVAILABLE.value
        else:
            available = UserFacingAvailability.UNAVAILABLE.value

        response_dict["available"] = available

    response_dict["help"] = help_ent.help_info
    return response_dict
