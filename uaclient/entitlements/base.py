import abc
import logging
import os
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import yaml

from uaclient import config, contract, status, util
from uaclient.defaults import DEFAULT_HELP_FILE
from uaclient.status import (
    MESSAGE_DEPENDENT_SERVICE_STOPS_DISABLE,
    MESSAGE_INCOMPATIBLE_SERVICE_STOPS_ENABLE,
    MESSAGE_REQUIRED_SERVICE_STOPS_ENABLE,
    ApplicabilityStatus,
    CanEnableFailure,
    CanEnableFailureReason,
    ContractStatus,
    UserFacingStatus,
)
from uaclient.types import StaticAffordance
from uaclient.util import is_config_value_true

RE_KERNEL_UNAME = (
    r"(?P<major>[\d]+)[.-](?P<minor>[\d]+)[.-](?P<patch>[\d]+\-[\d]+)"
    r"-(?P<flavor>[A-Za-z0-9_-]+)"
)


class UAEntitlement(metaclass=abc.ABCMeta):

    # Optional URL for top-level product service information
    help_doc_url = None  # type: str

    # Whether to assume yes to any messaging prompts
    assume_yes = False

    # Whether that entitlement is in beta stage
    is_beta = False

    # Help info message for the entitlement
    _help_info = None  # type: str

    # List of services that are incompatible with this service
    _incompatible_services = ()  # type: Tuple[str, ...]

    # List of services that must be active before enabling this service
    _required_services = ()  # type: Tuple[str, ...]

    # List of services that depend on this service
    _dependent_services = ()  # type: Tuple[str, ...]

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The lowercase name of this entitlement"""
        pass

    @property
    def valid_names(self) -> List[str]:
        """The list of names this entitlement may be called."""
        valid_names = [self.name]
        if self.presentation_name != self.name:
            valid_names.append(self.presentation_name)
        return valid_names

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The human readable title of this entitlement"""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """A sentence describing this entitlement"""
        pass

    @property
    def presentation_name(self) -> str:
        """The user-facing name shown for this entitlement"""
        return (
            self.cfg.entitlements.get(self.name, {})
            .get("entitlement", {})
            .get("affordances", {})
            .get("presentedAs", self.name)
        )

    @property
    def help_info(self) -> str:
        """Help information for the entitlement"""
        if self._help_info is None:
            help_dict = {}

            if os.path.exists(DEFAULT_HELP_FILE):
                with open(DEFAULT_HELP_FILE, "r") as f:
                    help_dict = yaml.safe_load(f)

            self._help_info = help_dict.get(self.name, {}).get("help", "")

        return self._help_info

    # A tuple of 3-tuples with (failure_message, functor, expected_results)
    # If any static_affordance does not match expected_results fail with
    # <failure_message>. Overridden in livepatch and fips
    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        return ()

    @property
    def incompatible_services(self) -> Tuple[str, ...]:
        """
        Return a list of packages that aren't compatible with the entitlement.
        When we are enabling the entitlement we can directly ask the user
        if those entitlements can be disabled before proceding.
        Overridden in livepatch and fips
        """
        return self._incompatible_services

    @property
    def required_services(self) -> Tuple[str, ...]:
        """
        Return a list of packages that must be active before enabling this
        service. When we are enabling the entitlement we can directly ask
        the user if those entitlements can be enabled before proceding.
        Overridden in ros and ros-updates.
        """
        return self._required_services

    @property
    def dependent_services(self) -> Tuple[str, ...]:
        """
        Return a list of packages that depend on this service.
        We will use that list during disable operations, where
        a disable operation will also disable all of the services
        required by the original service
        Overriden in esm-apps and esm-infra
        """
        return self._dependent_services

    # Any custom messages to emit to the console or callables which are
    # handled at pre_enable, pre_disable, pre_install or post_enable stages
    @property
    def messaging(self,) -> Dict[str, List[Union[str, Tuple[Callable, Dict]]]]:
        return {}

    def __init__(
        self,
        cfg: Optional[config.UAConfig] = None,
        assume_yes: bool = False,
        allow_beta: bool = False,
        called_name: str = "",
    ) -> None:
        """Setup UAEntitlement instance

        @param config: Parsed configuration dictionary
        """
        if not cfg:
            cfg = config.UAConfig()
        self.cfg = cfg
        self.assume_yes = assume_yes
        self.allow_beta = allow_beta
        self._called_name = called_name
        self._valid_service = None

    @property
    def valid_service(self):
        """Check if the service is marked as valid (non-beta)"""
        if self._valid_service is None:
            self._valid_service = (
                not self.is_beta
                or self.allow_beta
                or is_config_value_true(self.cfg.cfg, "features.allow_beta")
            )

        return self._valid_service

    # using Union instead of Optional here to signal that it may expand to
    # support additional reason types in the future.
    def enable(
        self, silent: bool = False
    ) -> Tuple[bool, Union[None, CanEnableFailure]]:
        """Enable specific entitlement.

        @return: tuple of (success, optional reason)
            (True, None) on success.
            (False, reason) otherwise. reason is only non-None if it is a
                populated CanEnableFailure reason. This may expand to
                include other types of reasons in the future.
        """
        msg_ops = self.messaging.get("pre_enable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        can_enable, fail = self.can_enable()
        if not can_enable:
            if fail is None:
                # this shouldn't happen, but if it does we shouldn't continue
                return False, None
            elif fail.reason == CanEnableFailureReason.INCOMPATIBLE_SERVICE:
                # Try to disable those services before proceeding with enable
                handle_incompat_ret = self.handle_incompatible_services()
                if not handle_incompat_ret:
                    return False, fail
            elif (
                fail.reason
                == CanEnableFailureReason.INACTIVE_REQUIRED_SERVICES
            ):
                # Try to enable those services before proceeding with enable
                if not self._enable_required_services():
                    return False, fail
            else:
                # every other reason means we can't continue
                return False, fail

        ret = self._perform_enable(silent=silent)
        if not ret:
            return False, None

        msg_ops = self.messaging.get("post_enable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        return True, None

    @abc.abstractmethod
    def _perform_enable(self, silent: bool = False) -> bool:
        """
        Enable specific entitlement. This should be implemented by subclasses.
        This method does the actual enablement, and does not check can_enable
        or handle pre_enable or post_enable messaging.

        @return: True on success, False otherwise.
        """
        pass

    def can_disable(self, silent: bool = False) -> bool:
        """Report whether or not disabling is possible for the entitlement.

        @param silent: Boolean set True to silence printed messages/warnings.
        """
        application_status, _ = self.application_status()

        if application_status == status.ApplicationStatus.DISABLED:
            if not silent:
                print(
                    status.MESSAGE_ALREADY_DISABLED_TMPL.format(
                        title=self.title
                    )
                )
            return False
        return True

    def can_enable(self) -> Tuple[bool, Optional[CanEnableFailure]]:
        """
        Report whether or not enabling is possible for the entitlement.

        :return:
            (True, None) if can enable
            (False, CanEnableFailure) if can't enable
        """

        if self.is_access_expired():
            logging.debug(
                "Updating contract on service '%s' expiry", self.name
            )
            contract.request_updated_contract(self.cfg)

        if not self.contract_status() == ContractStatus.ENTITLED:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.NOT_ENTITLED,
                    message=status.MESSAGE_UNENTITLED_TMPL.format(
                        title=self.title
                    ),
                ),
            )

        application_status, _ = self.application_status()
        if application_status != status.ApplicationStatus.DISABLED:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.ALREADY_ENABLED,
                    message=status.MESSAGE_ALREADY_ENABLED_TMPL.format(
                        title=self.title
                    ),
                ),
            )

        if not self.valid_service:
            return (False, CanEnableFailure(CanEnableFailureReason.IS_BETA))

        applicability_status, details = self.applicability_status()
        if applicability_status == status.ApplicabilityStatus.INAPPLICABLE:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.INAPPLICABLE, message=details
                ),
            )

        if self.incompatible_services:
            if self.detect_incompatible_services():
                return (
                    False,
                    CanEnableFailure(
                        CanEnableFailureReason.INCOMPATIBLE_SERVICE
                    ),
                )

        if self.required_services:
            if not self.check_required_services_active():
                return (
                    False,
                    CanEnableFailure(
                        CanEnableFailureReason.INACTIVE_REQUIRED_SERVICES
                    ),
                )

        return (True, None)

    def check_required_services_active(self):
        """
        Check if all required services are active

        :return:
            True if all required services are active
            False is at least one of the required services is disabled
        """
        from uaclient.entitlements import entitlement_factory

        for required_service in self.required_services:
            ent_cls = entitlement_factory(required_service)
            if ent_cls:
                ent_status, _ = ent_cls(self.cfg).application_status()
                if ent_status != status.ApplicationStatus.ENABLED:
                    return False

        return True

    def detect_incompatible_services(self) -> bool:
        """
        Check for incompatible services.

        :return:
            True if there are incompatible services enabled
            False if there are no incompatible services enabled
        """
        from uaclient.entitlements import entitlement_factory

        for incompatible_service in self.incompatible_services:
            ent_cls = entitlement_factory(incompatible_service)
            if ent_cls:
                ent_status, _ = ent_cls(self.cfg).application_status()
                if ent_status == status.ApplicationStatus.ENABLED:
                    return True

        return False

    def handle_incompatible_services(self) -> bool:
        """
        Prompt user when incompatible services are found during enable.

        When enabling a service, we may find that there is an incompatible
        service already enable. In that situation, we can ask the user
        if the incompatible service should be disabled before proceeding.
        There are also different ways to configure that behavior:

        We can disable removing incompatible service during enable by
        adding the following lines into uaclient.conf:

        features:
          block_disable_on_enable: true
        """
        from uaclient.entitlements import entitlement_factory

        cfg_block_disable_on_enable = util.is_config_value_true(
            config=self.cfg.cfg,
            path_to_value="features.block_disable_on_enable",
        )
        for incompatible_service in self.incompatible_services:
            ent_cls = entitlement_factory(incompatible_service)

            if ent_cls:
                ent = ent_cls(self.cfg)
                enabled_status = status.ApplicationStatus.ENABLED

                is_service_enabled = (
                    ent.application_status()[0] == enabled_status
                )

                if is_service_enabled:
                    user_msg = status.MESSAGE_INCOMPATIBLE_SERVICE.format(
                        service_being_enabled=self.title,
                        incompatible_service=ent.title,
                    )

                    e_msg = MESSAGE_INCOMPATIBLE_SERVICE_STOPS_ENABLE.format(
                        service_being_enabled=self.title,
                        incompatible_service=ent.title,
                    )

                    if cfg_block_disable_on_enable:
                        logging.info(e_msg)
                        return False

                    if not util.prompt_for_confirmation(
                        msg=user_msg, assume_yes=self.assume_yes
                    ):
                        print(e_msg)
                        return False

                    disable_msg = "Disabling incompatible service: {}".format(
                        ent.title
                    )
                    logging.info(disable_msg)

                    ret = ent.disable()
                    if not ret:
                        return ret

        return True

    def _enable_required_services(self) -> bool:
        """
        Prompt user when required services are found during enable.

        When enabling a service, we may find that there are required services
        that must be enabled first. In that situation, we can ask the user
        if the required service should be enabled before proceeding.
        """
        from uaclient.entitlements import entitlement_factory

        for required_service in self.required_services:
            ent_cls = entitlement_factory(required_service)
            if not ent_cls:
                msg = "Required service {} not found.".format(required_service)
                logging.error(msg)
                return False

            ent = ent_cls(self.cfg, allow_beta=True)

            is_service_disabled = (
                ent.application_status()[0]
                == status.ApplicationStatus.DISABLED
            )

            if is_service_disabled:
                user_msg = status.MESSAGE_REQUIRED_SERVICE.format(
                    service_being_enabled=self.title,
                    required_service=ent.title,
                )

                e_msg = MESSAGE_REQUIRED_SERVICE_STOPS_ENABLE.format(
                    service_being_enabled=self.title,
                    required_service=ent.title,
                )

                if not util.prompt_for_confirmation(
                    msg=user_msg, assume_yes=self.assume_yes
                ):
                    print(e_msg)
                    return False

                print("Enabling required service: {}".format(ent.title))
                ret, _ = ent.enable(silent=True)
                if not ret:
                    return ret

        return True

    def applicability_status(self) -> Tuple[ApplicabilityStatus, str]:
        """Check all contract affordances to vet current platform

        Affordances are a list of support constraints for the entitlement.
        Examples include a list of supported series, architectures for kernel
        revisions.

        :return:
            tuple of (ApplicabilityStatus, detailed_message). APPLICABLE if
            platform passes all defined affordances, INAPPLICABLE if it doesn't
            meet all of the provided constraints.
        """
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if not entitlement_cfg:
            return (
                ApplicabilityStatus.APPLICABLE,
                "no entitlement affordances checked",
            )
        for error_message, functor, expected_result in self.static_affordances:
            if functor() != expected_result:
                return ApplicabilityStatus.INAPPLICABLE, error_message
        affordances = entitlement_cfg["entitlement"].get("affordances", {})
        platform = util.get_platform_info()
        affordance_arches = affordances.get("architectures", [])
        if affordance_arches and platform["arch"] not in affordance_arches:
            return (
                ApplicabilityStatus.INAPPLICABLE,
                status.MESSAGE_INAPPLICABLE_ARCH_TMPL.format(
                    title=self.title,
                    arch=platform["arch"],
                    supported_arches=", ".join(affordance_arches),
                ),
            )
        affordance_series = affordances.get("series", [])
        if affordance_series and platform["series"] not in affordance_series:
            return (
                ApplicabilityStatus.INAPPLICABLE,
                status.MESSAGE_INAPPLICABLE_SERIES_TMPL.format(
                    title=self.title, series=platform["version"]
                ),
            )
        kernel = platform["kernel"]
        affordance_kernels = affordances.get("kernelFlavors", [])
        affordance_min_kernel = affordances.get("minKernelVersion")
        match = re.match(RE_KERNEL_UNAME, kernel)
        if affordance_kernels:
            if not match or match.group("flavor") not in affordance_kernels:
                return (
                    ApplicabilityStatus.INAPPLICABLE,
                    status.MESSAGE_INAPPLICABLE_KERNEL_TMPL.format(
                        title=self.title,
                        kernel=kernel,
                        supported_kernels=", ".join(affordance_kernels),
                    ),
                )
        if affordance_min_kernel:
            invalid_msg = status.MESSAGE_INAPPLICABLE_KERNEL_VER_TMPL.format(
                title=self.title,
                kernel=kernel,
                min_kernel=affordance_min_kernel,
            )
            try:
                kernel_major, kernel_minor = affordance_min_kernel.split(".")
                min_kern_major = int(kernel_major)
                min_kern_minor = int(kernel_minor)
            except ValueError:
                logging.warning(
                    "Could not parse minKernelVersion: %s",
                    affordance_min_kernel,
                )
                return (ApplicabilityStatus.INAPPLICABLE, invalid_msg)

            if not match:
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg
            kernel_major = int(match.group("major"))
            kernel_minor = int(match.group("minor"))
            if kernel_major < min_kern_major:
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg
            elif (
                kernel_major == min_kern_major
                and kernel_minor < min_kern_minor
            ):
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg
        return ApplicabilityStatus.APPLICABLE, ""

    @abc.abstractmethod
    def _perform_disable(self, silent: bool = False) -> bool:
        """
        Disable specific entitlement. This should be implemented by subclasses.
        This method does the actual disable, and does not check can_disable
        or handle pre_disable or post_disable messaging.

        @param silent: Boolean set True to silence print/log of messages

        @return: True on success, False otherwise.
        """
        pass

    def _disable_dependent_services(self):
        """
        Disable dependent services

        When performing a disable operation, we might have
        other services that depend on the original services.
        If that is true, we will alert the user about this
        and prompt for confirmation to disable these services
        as well.
        """
        from uaclient.entitlements import entitlement_factory

        for dependent_service in self.dependent_services:
            ent_cls = entitlement_factory(dependent_service)
            ent = ent_cls(self.cfg)

            is_service_enabled = (
                ent.application_status()[0] == status.ApplicationStatus.ENABLED
            )

            if is_service_enabled:
                user_msg = status.MESSAGE_DEPENDENT_SERVICE.format(
                    dependent_service=ent.title,
                    service_being_disabled=self.title,
                )

                e_msg = MESSAGE_DEPENDENT_SERVICE_STOPS_DISABLE.format(
                    service_being_disabled=self.title,
                    dependent_service=ent.title,
                )

                if not util.prompt_for_confirmation(
                    msg=user_msg, assume_yes=self.assume_yes
                ):
                    print(e_msg)
                    return False

                print("Disabling dependent service: {}".format(ent.title))
                ret = ent.disable(silent=True)
                if not ret:
                    return ret

        return True

    def _check_for_reboot(self) -> bool:
        """Check if system needs to be rebooted."""
        return util.should_reboot()

    def _check_for_reboot_msg(self, operation: str) -> None:
        """Check if user should be alerted that a reboot must be performed.

        @param operation: The operation being executed.
        """
        if self._check_for_reboot():
            print(
                status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation=operation
                )
            )

    def disable(self, silent: bool = False) -> bool:
        """Disable specific entitlement

        @param silent: Boolean set True to silence print/log of messages

        @return: True on success, False otherwise.
        """
        msg_ops = self.messaging.get("pre_disable", [])
        if not util.handle_message_operations(msg_ops):
            return False
        if not self.can_disable(silent):
            return False
        if not self._disable_dependent_services():
            return False

        if not self._perform_disable(silent=silent):
            return False

        msg_ops = self.messaging.get("post_disable", [])
        if not util.handle_message_operations(msg_ops):
            return False
        self._check_for_reboot_msg(operation="disable operation")

        return True

    def contract_status(self) -> ContractStatus:
        """Return whether the user is entitled to the entitlement or not"""
        if not self.cfg.is_attached:
            return ContractStatus.UNENTITLED
        entitlement_cfg = self.cfg.entitlements.get(self.name, {})
        if entitlement_cfg and entitlement_cfg["entitlement"].get("entitled"):
            return ContractStatus.ENTITLED
        return ContractStatus.UNENTITLED

    def is_access_expired(self) -> bool:
        """Return entitlement access info as stale and needing refresh."""
        entitlement_contract = self.cfg.entitlements.get(self.name, {})
        # TODO(No expiry per resource in MVP yet)
        expire_str = entitlement_contract.get("expires")
        if not expire_str:
            return False
        expiry = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        if expiry >= datetime.utcnow():
            return False
        return True

    def _check_application_status_on_cache(self) -> status.ApplicationStatus:
        """Check on the state of application on the status cache."""
        status_cache = self.cfg.read_cache("status-cache")

        if status_cache is None:
            return status.ApplicationStatus.DISABLED

        services_status_list = status_cache.get("services", [])

        for service in services_status_list:
            if service.get("name") == self.name:
                service_status = service.get("status")

                if service_status == "enabled":
                    return status.ApplicationStatus.ENABLED
                else:
                    return status.ApplicationStatus.DISABLED

        return status.ApplicationStatus.DISABLED

    def process_contract_deltas(
        self,
        orig_access: Dict[str, Any],
        deltas: Dict[str, Any],
        allow_enable: bool = False,
    ) -> bool:
        """Process any contract access deltas for this entitlement.

        :param orig_access: Dictionary containing the original
            resourceEntitlement access details.
        :param deltas: Dictionary which contains only the changed access keys
        and values.
        :param allow_enable: Boolean set True if allowed to perform the enable
            operation. When False, a message will be logged to inform the user
            about the recommended enabled service.

        :return: True when delta operations are processed; False when noop.
        :raise: UserFacingError when auto-enable fails unexpectedly.
        """
        if not deltas:
            return True  # We processed all deltas that needed processing

        delta_entitlement = deltas.get("entitlement", {})
        delta_directives = delta_entitlement.get("directives", {})
        status_cache = self.cfg.read_cache("status-cache")

        transition_to_unentitled = bool(delta_entitlement == util.DROPPED_KEY)
        if not transition_to_unentitled:
            if delta_entitlement:
                util.apply_series_overrides(deltas)
                delta_entitlement = deltas["entitlement"]
            if orig_access and "entitled" in delta_entitlement:
                transition_to_unentitled = delta_entitlement["entitled"] in (
                    False,
                    util.DROPPED_KEY,
                )
        if transition_to_unentitled:
            if delta_directives and status_cache:
                application_status = self._check_application_status_on_cache()
            else:
                application_status, _ = self.application_status()

            if application_status != status.ApplicationStatus.DISABLED:
                if self.can_disable(silent=True):
                    self.disable()
                    logging.info(
                        "Due to contract refresh, '%s' is now disabled.",
                        self.name,
                    )
                else:
                    logging.warning(
                        "Unable to disable '%s' as recommended during contract"
                        " refresh. Service is still active. See"
                        " `ua status`",
                        self.name,
                    )
            # Clean up former entitled machine-access-<name> response cache
            # file because uaclient doesn't access machine-access-* routes or
            # responses on unentitled services.
            self.cfg.delete_cache_key("machine-access-{}".format(self.name))
            return True

        resourceToken = orig_access.get("resourceToken")
        if not resourceToken:
            resourceToken = deltas.get("resourceToken")
        delta_obligations = delta_entitlement.get("obligations", {})
        enable_by_default = bool(
            delta_obligations.get("enableByDefault") and resourceToken
        )

        if enable_by_default:
            self.allow_beta = True

        can_enable, _ = self.can_enable()
        if can_enable and enable_by_default:
            if allow_enable:
                msg = status.MESSAGE_ENABLE_BY_DEFAULT_TMPL.format(
                    name=self.name
                )
                logging.info(msg)
                self.enable()
            else:
                msg = status.MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
                    name=self.name
                )
                logging.info(msg)
            return True

        return False

    def user_facing_status(self) -> Tuple[UserFacingStatus, str]:
        """Return (user-facing status, details) for entitlement"""
        applicability, details = self.applicability_status()
        if applicability != ApplicabilityStatus.APPLICABLE:
            return UserFacingStatus.INAPPLICABLE, details
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if not entitlement_cfg:
            return (
                UserFacingStatus.UNAVAILABLE,
                "{} is not entitled".format(self.title),
            )
        elif entitlement_cfg["entitlement"].get("entitled", False) is False:
            return (
                UserFacingStatus.UNAVAILABLE,
                "{} is not entitled".format(self.title),
            )

        application_status, explanation = self.application_status()
        user_facing_status = {
            status.ApplicationStatus.ENABLED: UserFacingStatus.ACTIVE,
            status.ApplicationStatus.DISABLED: UserFacingStatus.INACTIVE,
        }[application_status]
        return user_facing_status, explanation

    @abc.abstractmethod
    def application_status(self) -> Tuple[status.ApplicationStatus, str]:
        """
        The current status of application of this entitlement

        :return:
            A tuple of (ApplicationStatus, human-friendly reason)
        """
        pass
