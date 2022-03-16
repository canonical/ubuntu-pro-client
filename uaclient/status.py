import enum
import os
import sys
import textwrap
from typing import Any, Dict, List, Optional, Tuple

from uaclient.defaults import (
    BASE_UA_URL,
    CONFIG_FIELD_ENVVAR_ALLOWLIST,
    PRINT_WRAP_WIDTH,
)
from uaclient.messages import UNATTACHED, NamedMessage, TxtColor


@enum.unique
class ApplicationStatus(enum.Enum):
    """
    An enum to represent the current application status of an entitlement
    """

    ENABLED = object()
    DISABLED = object()


@enum.unique
class ContractStatus(enum.Enum):
    """
    An enum to represent whether a user is entitled to an entitlement

    (The value of each member is the string that will be used in status
    output.)
    """

    ENTITLED = "yes"
    UNENTITLED = "no"


@enum.unique
class ApplicabilityStatus(enum.Enum):
    """
    An enum to represent whether an entitlement could apply to this machine
    """

    APPLICABLE = object()
    INAPPLICABLE = object()


@enum.unique
class UserFacingAvailability(enum.Enum):
    """
    An enum representing whether a service could be available for a machine.

    'Availability' means whether a service is available to machines with this
    architecture, series and kernel. Whether a contract is entitled to use
    the specific service is determined by the contract level.

    This enum should only be used in display code, it should not be used in
    business logic.
    """

    AVAILABLE = "yes"
    UNAVAILABLE = "no"


@enum.unique
class UserFacingConfigStatus(enum.Enum):
    """
    An enum representing the user-visible config status of UA system.

    This enum will be used in display code and will be written to status.json
    """

    INACTIVE = "inactive"  # No UA config commands/daemons
    ACTIVE = "active"  # UA command is running
    REBOOTREQUIRED = "reboot-required"  # System Reboot required


@enum.unique
class UserFacingStatus(enum.Enum):
    """
    An enum representing the states we will display in status output.

    This enum should only be used in display code, it should not be used in
    business logic.
    """

    ACTIVE = "enabled"
    INACTIVE = "disabled"
    INAPPLICABLE = "n/a"
    UNAVAILABLE = "—"


@enum.unique
class CanEnableFailureReason(enum.Enum):
    """
    An enum representing the reasons an entitlement can't be enabled.
    """

    NOT_ENTITLED = object()
    ALREADY_ENABLED = object()
    INAPPLICABLE = object()
    IS_BETA = object()
    INCOMPATIBLE_SERVICE = object()
    INACTIVE_REQUIRED_SERVICES = object()


class CanEnableFailure:
    def __init__(
        self,
        reason: CanEnableFailureReason,
        message: Optional[NamedMessage] = None,
    ) -> None:
        self.reason = reason
        self.message = message


@enum.unique
class CanDisableFailureReason(enum.Enum):
    """
    An enum representing the reasons an entitlement can't be disabled.
    """

    ALREADY_DISABLED = object()
    ACTIVE_DEPENDENT_SERVICES = object()
    NOT_FOUND_DEPENDENT_SERVICE = object()


class CanDisableFailure:
    def __init__(
        self,
        reason: CanDisableFailureReason,
        message: Optional[NamedMessage] = None,
    ) -> None:
        self.reason = reason
        self.message = message


ESSENTIAL = "essential"
STANDARD = "standard"
ADVANCED = "advanced"

# Colorized status output for terminal
STATUS_COLOR = {
    UserFacingStatus.ACTIVE.value: (
        TxtColor.OKGREEN + UserFacingStatus.ACTIVE.value + TxtColor.ENDC
    ),
    UserFacingStatus.INACTIVE.value: (
        TxtColor.FAIL + UserFacingStatus.INACTIVE.value + TxtColor.ENDC
    ),
    UserFacingStatus.INAPPLICABLE.value: (
        TxtColor.DISABLEGREY
        + UserFacingStatus.INAPPLICABLE.value
        + TxtColor.ENDC
    ),  # noqa: E501
    UserFacingStatus.UNAVAILABLE.value: (
        TxtColor.DISABLEGREY
        + UserFacingStatus.UNAVAILABLE.value
        + TxtColor.ENDC
    ),
    ContractStatus.ENTITLED.value: (
        TxtColor.OKGREEN + ContractStatus.ENTITLED.value + TxtColor.ENDC
    ),
    ContractStatus.UNENTITLED.value: (
        TxtColor.DISABLEGREY + ContractStatus.UNENTITLED.value + TxtColor.ENDC
    ),  # noqa: E501
    ESSENTIAL: TxtColor.OKGREEN + ESSENTIAL + TxtColor.ENDC,
    STANDARD: TxtColor.OKGREEN + STANDARD + TxtColor.ENDC,
    ADVANCED: TxtColor.OKGREEN + ADVANCED + TxtColor.ENDC,
}

PROMPT_YES_NO = """Are you sure? (y/N) """
NOTICE_FIPS_MANUAL_DISABLE_URL = """\
FIPS kernel is running in a disabled state.
  To manually remove fips kernel: https://discourse.ubuntu.com/t/20738
"""
NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD = """\
Warning: FIPS kernel is not optimized for your specific cloud.
To fix it, run the following commands:

    1. sudo ua disable fips
    2. sudo apt-get remove ubuntu-fips
    3. sudo ua enable fips --assume-yes
    4. sudo reboot
"""
PROMPT_FIPS_PRE_ENABLE = (
    """\
This will install the FIPS packages. The Livepatch service will be unavailable.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)
PROMPT_FIPS_UPDATES_PRE_ENABLE = (
    """\
This will install the FIPS packages including security updates.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)
PROMPT_FIPS_CONTAINER_PRE_ENABLE = (
    """\
Warning: Enabling {title} in a container.
         This will install the FIPS packages but not the kernel.
         This container must run on a host with {title} enabled to be
         compliant.
Warning: This action can take some time and cannot be undone.
"""
    + PROMPT_YES_NO
)

PROMPT_FIPS_PRE_DISABLE = (
    """\
This will disable the FIPS entitlement but the FIPS packages will remain installed.
"""  # noqa
    + PROMPT_YES_NO
)

PROMPT_ENTER_TOKEN = """\
Enter your token (from {}) to attach this system:""".format(
    BASE_UA_URL
)
PROMPT_EXPIRED_ENTER_TOKEN = """\
Enter your new token to renew UA subscription on this system:"""
PROMPT_UA_SUBSCRIPTION_URL = """\
Open a browser to: {}/subscribe""".format(
    BASE_UA_URL
)

STATUS_UNATTACHED_TMPL = "{name: <17}{available: <11}{description}"

STATUS_SIMULATED_TMPL = """\
{name: <17}{available: <11}{entitled: <11}{auto_enabled: <14}{description}"""

STATUS_HEADER = "SERVICE          ENTITLED  STATUS    DESCRIPTION"
# The widths listed below for entitled and status are actually 9 characters
# less than reality because we colorize the values in entitled and status
# columns. Colorizing has an opening and closing set of unprintable characters
# that factor into formats len() calculations
STATUS_TMPL = "{name: <17}{entitled: <19}{status: <19}{description}"


def colorize(string: str) -> str:
    """Return colorized string if using a tty, else original string."""
    return STATUS_COLOR.get(string, string) if sys.stdout.isatty() else string


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
    content = [""]
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


def format_tabular(status: Dict[str, Any]) -> str:
    """Format status dict for tabular output."""
    if not status.get("attached"):
        if status.get("simulated"):
            content = [
                STATUS_SIMULATED_TMPL.format(
                    name="SERVICE",
                    available="AVAILABLE",
                    entitled="ENTITLED",
                    auto_enabled="AUTO_ENABLED",
                    description="DESCRIPTION",
                )
            ]
            for service in status["services"]:
                content.append(STATUS_SIMULATED_TMPL.format(**service))
            return "\n".join(content)

        content = [
            STATUS_UNATTACHED_TMPL.format(
                name="SERVICE",
                available="AVAILABLE",
                description="DESCRIPTION",
            )
        ]
        for service in status["services"]:
            content.append(STATUS_UNATTACHED_TMPL.format(**service))
        content.extend(["", UNATTACHED.msg])
        return "\n".join(content)

    content = [STATUS_HEADER]
    for service_status in status["services"]:
        entitled = service_status["entitled"]
        descr_override = service_status.get("description_override")
        description = (
            descr_override if descr_override else service_status["description"]
        )
        fmt_args = {
            "name": service_status["name"],
            "entitled": colorize(entitled),
            "status": colorize(service_status["status"]),
            "description": description,
        }
        content.append(STATUS_TMPL.format(**fmt_args))
    tech_support_level = status["contract"]["tech_support_level"]

    if status.get("notices"):
        content.extend(
            get_section_column_content(
                status.get("notices") or [], header="NOTICES"
            )
        )
    content.append("\nEnable services with: ua enable <service>")
    pairs = []

    account_name = status["account"]["name"]
    if account_name:
        pairs.append(("Account", account_name))

    contract_name = status["contract"]["name"]
    if contract_name:
        pairs.append(("Subscription", contract_name))

    if status["origin"] != "free":
        pairs.append(("Valid until", str(status["expires"])))
        pairs.append(("Technical support level", colorize(tech_support_level)))

    if pairs:
        content.extend(get_section_column_content(column_data=pairs))

    return "\n".join(content)


def format_machine_readable_output(status: Dict[str, Any]) -> Dict[str, Any]:
    status["environment_vars"] = [
        {"name": name, "value": value}
        for name, value in sorted(os.environ.items())
        if name.lower() in CONFIG_FIELD_ENVVAR_ALLOWLIST
        or name.startswith("UA_FEATURES")
        or name == "UA_CONFIG_FILE"
    ]

    if not status.get("simulated"):
        available_services = [
            service
            for service in status.get("services", [])
            if service.get("available", "yes") == "yes"
        ]
        status["services"] = available_services

    # We don't need the origin info in the json output
    status.pop("origin", "")

    return status
