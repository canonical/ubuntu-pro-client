import enum
from typing import Optional

from uaclient import messages


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
    An enum representing the user-visible config status of Pro system.

    This enum will be used in display code and will be written to status.json
    """

    INACTIVE = "inactive"  # No Pro config commands/daemons
    ACTIVE = "active"  # Pro command is running
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
    ACCESS_ONLY_NOT_SUPPORTED = object()


class CanEnableFailure:
    def __init__(
        self,
        reason: CanEnableFailureReason,
        message: Optional[messages.NamedMessage] = None,
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
        message: Optional[messages.NamedMessage] = None,
    ) -> None:
        self.reason = reason
        self.message = message
