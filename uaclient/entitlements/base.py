import abc
import copy
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from uaclient import (
    apt,
    config,
    contract,
    event_logger,
    exceptions,
    http,
    messages,
    snap,
    system,
    util,
)
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
    CanDisableFailure,
    CanDisableFailureReason,
    CanEnableFailure,
    CanEnableFailureReason,
    ContractStatus,
    UserFacingStatus,
)
from uaclient.types import MessagingOperationsDict, StaticAffordance
from uaclient.util import is_config_value_true

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class IncompatibleService:
    def __init__(
        self,
        entitlement: Type["UAEntitlement"],
        named_msg: messages.NamedMessage,
    ):
        self.entitlement = entitlement
        self.named_msg = named_msg


class UAEntitlement(metaclass=abc.ABCMeta):
    # Optional URL for top-level product service information
    help_doc_url = None  # type: str

    # Whether to assume yes to any messaging prompts
    assume_yes = False

    # Whether that entitlement is in beta stage
    is_beta = False

    # Whether the entitlement supports the --access-only flag
    supports_access_only = False

    # Whether the entitlement supports the --purge flag
    supports_purge = False

    # Help text for the entitlement
    help_text = ""

    # List of services that are incompatible with this service
    _incompatible_services = ()  # type: Tuple[IncompatibleService, ...]

    # List of services that must be active before enabling this service
    _required_services = ()  # type: Tuple[Type[UAEntitlement], ...]

    # List of services that depend on this service
    _dependent_services = ()  # type: Tuple[Type[UAEntitlement], ...]

    affordance_check_arch = True
    affordance_check_series = True
    affordance_check_kernel_min_version = True
    affordance_check_kernel_flavor = True

    # Determine if the service is a variant of an existing service
    is_variant = False

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The lowercase name of this entitlement"""
        pass

    @property
    def variant_name(self) -> str:
        """The lowercase name of this entitlement, in case it is a variant"""
        return ""

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
        if self.is_variant:
            return self.variant_name
        elif self.cfg.machine_token_file.is_present:
            return (
                self.entitlement_cfg.get("entitlement", {})
                .get("affordances", {})
                .get("presentedAs", self.name)
            )
        else:
            return self.name

    def verify_platform_checks(
        self, platform_check: Dict[str, Any]
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        """Verify specific platform checks for a service.

        This should only be used if the service requires custom platform checks
        to check if it is available or not in the machine.
        """
        return True, None

    @property
    def help_info(self) -> str:
        """Help information for the entitlement"""
        help_text = self.help_text

        if self.variants:
            variant_items = [
                "  * {}: {}".format(variant_name, variant_cls.description)
                for variant_name, variant_cls in self.variants.items()
            ]

            variant_text = "\n".join(
                ["\n\n" + messages.CLI_HELP_VARIANTS_HEADER + "\n"]
                + variant_items
            )
            help_text += variant_text

        return help_text

    # A tuple of 3-tuples with (failure_message, functor, expected_results)
    # If any static_affordance does not match expected_results fail with
    # <failure_message>. Overridden in livepatch and fips
    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        return ()

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        """
        Return a list of packages that aren't compatible with the entitlement.
        When we are enabling the entitlement we can directly ask the user
        if those entitlements can be disabled before proceding.
        Overridden in livepatch and fips
        """
        return self._incompatible_services

    @property
    def required_services(self) -> Tuple[Type["UAEntitlement"], ...]:
        """
        Return a list of packages that must be active before enabling this
        service. When we are enabling the entitlement we can directly ask
        the user if those entitlements can be enabled before proceding.
        Overridden in ros and ros-updates.
        """
        return self._required_services

    @property
    def dependent_services(self) -> Tuple[Type["UAEntitlement"], ...]:
        """
        Return a list of packages that depend on this service.
        We will use that list during disable operations, where
        a disable operation will also disable all of the services
        required by the original service
        Overriden in esm-apps and esm-infra
        """
        return self._dependent_services

    def _get_variants(self) -> Dict[str, Type["UAEntitlement"]]:
        return {}

    def _get_contract_variants(self) -> Set[str]:
        """
        Fetch all available variants defined in the Contract Server response
        """
        valid_variants = set()
        entitlement_cfg = self._base_entitlement_cfg()

        overrides = entitlement_cfg.get("entitlement", {}).get("overrides", [])
        for override in overrides:
            variant = override.get("selector", {}).get("variant")
            if variant:
                valid_variants.add(variant)

        return valid_variants

    def _get_valid_variants(self) -> Dict[str, Type["UAEntitlement"]]:
        service_variants = self._get_variants()
        contract_variants = self._get_contract_variants()

        if "generic" in service_variants:
            valid_variants = {"generic": service_variants["generic"]}
        else:
            valid_variants = {}

        for variant in sorted(contract_variants):
            if variant in service_variants:
                valid_variants[variant] = service_variants[variant]

        return valid_variants if len(valid_variants) > 1 else {}

    @property
    def variants(self) -> Dict[str, Type["UAEntitlement"]]:
        """
        Return a list of services that are considered a variant
        of the main service.
        """
        if self.is_variant:
            return {}
        return self._get_valid_variants()

    @property
    def other_variants(self) -> Dict[str, Type["UAEntitlement"]]:
        """
        On a variant, return the other variants of the main service.
        On a non-variant, returns empty.
        """
        if not self.is_variant:
            return {}
        return {
            name: cls
            for name, cls in self._get_valid_variants().items()
            if name != self.variant_name
        }

    @property
    def enabled_variant(self) -> Optional["UAEntitlement"]:
        """
        On an enabled service class, return the variant that is enabled.
        Return None if no variants exist or none are enabled (e.g. access-only)
        """
        for variant_cls in self.variants.values():
            if variant_cls.variant_name == "generic":
                continue
            variant = variant_cls(
                cfg=self.cfg,
                assume_yes=self.assume_yes,
                allow_beta=self.allow_beta,
                called_name=self._called_name,
                access_only=self.access_only,
            )
            status, _ = variant.application_status()
            if status == ApplicationStatus.ENABLED:
                return variant
        return None

    # Any custom messages to emit to the console or callables which are
    # handled at pre_enable, pre_disable, pre_install or post_enable stages
    @property
    def messaging(self) -> MessagingOperationsDict:
        return {}

    def __init__(
        self,
        cfg: Optional[config.UAConfig] = None,
        assume_yes: bool = False,
        allow_beta: bool = False,
        called_name: str = "",
        access_only: bool = False,
        purge: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> None:
        """Setup UAEntitlement instance

        @param config: Parsed configuration dictionary
        """
        if not cfg:
            cfg = config.UAConfig()
        self.cfg = cfg
        self.assume_yes = assume_yes
        self.allow_beta = allow_beta
        self.access_only = access_only
        self.purge = purge
        if extra_args is not None:
            self.extra_args = extra_args
        else:
            self.extra_args = []
        self._called_name = called_name
        self._valid_service = None  # type: Optional[bool]
        self._is_sources_list_updated = False

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

    def _base_entitlement_cfg(self):
        return copy.deepcopy(
            self.cfg.machine_token_file.entitlements.get(self.name, {})
        )

    @property
    def entitlement_cfg(self):
        entitlement_cfg = self._base_entitlement_cfg()

        if not self.is_variant or not entitlement_cfg:
            return entitlement_cfg

        contract.apply_contract_overrides(
            orig_access=entitlement_cfg, variant=self.variant_name
        )

        return entitlement_cfg

    def can_enable(self) -> Tuple[bool, Optional[CanEnableFailure]]:
        """
        Report whether or not enabling is possible for the entitlement.

        :return:
            (True, None) if can enable
            (False, CanEnableFailure) if can't enable
        """

        if self.is_access_expired():
            LOG.debug("Updating contract on service '%s' expiry", self.name)
            contract.refresh(self.cfg)

        if not self.contract_status() == ContractStatus.ENTITLED:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.NOT_ENTITLED,
                    message=messages.UNENTITLED.format(title=self.title),
                ),
            )

        application_status, _ = self.application_status()
        if application_status != ApplicationStatus.DISABLED:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.ALREADY_ENABLED,
                    message=messages.ALREADY_ENABLED.format(title=self.title),
                ),
            )

        if not self.valid_service:
            return (False, CanEnableFailure(CanEnableFailureReason.IS_BETA))

        applicability_status, details = self.applicability_status()
        if applicability_status == ApplicabilityStatus.INAPPLICABLE:
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

        if not self.supports_access_only and self.access_only:
            return (
                False,
                CanEnableFailure(
                    CanEnableFailureReason.ACCESS_ONLY_NOT_SUPPORTED,
                    messages.ENABLE_ACCESS_ONLY_NOT_SUPPORTED.format(
                        title=self.title
                    ),
                ),
            )

        return (True, None)

    # using Union instead of Optional here to signal that it may expand to
    # support additional reason types in the future.
    def enable(
        self,
        silent: bool = False,
    ) -> Tuple[bool, Union[None, CanEnableFailure]]:
        """Enable specific entitlement.

        @return: tuple of (success, optional reason)
            (True, None) on success.
            (False, reason) otherwise. reason is only non-None if it is a
                populated CanEnableFailure reason. This may expand to
                include other types of reasons in the future.
        """

        msg_ops = self.messaging.get("pre_can_enable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        can_enable, fail = self.can_enable()
        if not can_enable:
            if fail is None:
                # this shouldn't happen, but if it does we shouldn't continue
                return False, None
            elif fail.reason == CanEnableFailureReason.INCOMPATIBLE_SERVICE:
                # Try to disable those services before proceeding with enable
                incompat_ret, error = self.handle_incompatible_services()
                if not incompat_ret:
                    fail.message = error
                    return False, fail
            elif (
                fail.reason
                == CanEnableFailureReason.INACTIVE_REQUIRED_SERVICES
            ):
                # Try to enable those services before proceeding with enable
                req_ret, error = self._enable_required_services()
                if not req_ret:
                    fail.message = error
                    return False, fail
            else:
                # every other reason means we can't continue
                return False, fail

        msg_ops = self.messaging.get("pre_enable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        # TODO: Move all logic from RepoEntitlement that
        # handles the additionalPackages and APT directives
        # to the base class. The additionalSnaps handling
        # is a step on that direction
        if not self.access_only:
            if not self.handle_required_snaps():
                return False, None
            if not self.handle_required_packages():
                return False, None

        ret = self._perform_enable(silent=silent)
        if not ret:
            return False, None

        msg_ops = self.messaging.get("post_enable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        return True, None

    def handle_required_snaps(self) -> bool:
        """ "install snaps necessary to enable a service."""
        required_snaps = (
            self.entitlement_cfg.get("entitlement", {})
            .get("directives", {})
            .get("requiredSnaps")
        )

        # If we don't have the directive, there is nothing
        # to process here
        if required_snaps is None:
            return True

        if not snap.is_snapd_installed():
            event.info(messages.INSTALLING_PACKAGES.format(packages="snapd"))
            snap.install_snapd()

        if not snap.is_snapd_installed_as_a_snap():
            event.info(
                messages.INSTALLING_PACKAGES.format(packages="snapd snap")
            )
            try:
                snap.install_snap("snapd")
            except exceptions.ProcessExecutionError as e:
                LOG.warning("Failed to install snapd as a snap", exc_info=e)
                event.info(
                    messages.EXECUTING_COMMAND_FAILED.format(
                        command="snap install snapd"
                    )
                )

        snap.run_snapd_wait_cmd()

        try:
            snap.refresh_snap("snapd")
        except exceptions.ProcessExecutionError as e:
            LOG.warning("Failed to refresh snapd snap", exc_info=e)
            event.info(
                messages.EXECUTING_COMMAND_FAILED.format(
                    command="snap refresh snapd"
                )
            )

        http_proxy = http.validate_proxy(
            "http", self.cfg.http_proxy, http.PROXY_VALIDATION_SNAP_HTTP_URL
        )
        https_proxy = http.validate_proxy(
            "https", self.cfg.https_proxy, http.PROXY_VALIDATION_SNAP_HTTPS_URL
        )
        snap.configure_snap_proxy(
            http_proxy=http_proxy,
            https_proxy=https_proxy,
            retry_sleeps=snap.SNAP_INSTALL_RETRIES,
        )

        if required_snaps:
            event.info(messages.INSTALLING_REQUIRED_SNAPS)

        for snap_pkg in sorted(required_snaps, key=lambda x: x.get("name")):
            # The name field should always be delivered by the contract side
            snap_name = snap_pkg["name"]
            try:
                snap.get_snap_info(snap_name)
            except exceptions.SnapNotInstalledError:
                classic_confinement_support = snap_pkg.get(
                    "classicConfinementSupport", False
                )
                channel = snap_pkg.get("channel")

                event.info(
                    messages.INSTALLING_REQUIRED_SNAP_PACKAGE.format(
                        snap=snap_name
                    )
                )
                snap.install_snap(
                    snap_name,
                    channel=channel,
                    classic_confinement_support=classic_confinement_support,
                )

        return True

    def are_required_packages_installed(self) -> bool:
        """install packages necessary to enable a service."""
        required_packages = (
            self.entitlement_cfg.get("entitlement", {})
            .get("directives", {})
            .get("requiredPackages")
        )

        # If we don't have the directive, there is nothing
        # to process here
        if not required_packages:
            return True

        package_names = [package["name"] for package in required_packages]
        installed_packages = apt.get_installed_packages_names()

        return all(
            [required in installed_packages for required in package_names]
        )

    def handle_required_packages(self) -> bool:
        """install packages necessary to enable a service."""
        required_packages = (
            self.entitlement_cfg.get("entitlement", {})
            .get("directives", {})
            .get("requiredPackages")
        )

        # If we don't have the directive, there is nothing
        # to process here
        if not required_packages:
            return True

        self._update_sources_list()

        package_names = [package["name"] for package in required_packages]
        LOG.debug("Installing packages %r", package_names)
        event.info(
            messages.INSTALLING_PACKAGES.format(
                packages=" ".join(package_names)
            )
        )
        apt.run_apt_install_command(package_names)

        return True

    def handle_removing_required_packages(self) -> bool:
        """install packages necessary to enable a service."""
        required_packages = (
            self.entitlement_cfg.get("entitlement", {})
            .get("directives", {})
            .get("requiredPackages")
        )

        # If we don't have the directive, there is nothing
        # to process here
        if not required_packages:
            return True

        package_names = [
            package["name"]
            for package in required_packages
            if package.get("removeOnDisable", False)
        ]
        # If none of the packages have removeOnDisable, then there is nothing
        # to process here
        if len(package_names) == 0:
            return True

        LOG.debug("Uninstalling packages %r", package_names)
        package_names_str = " ".join(package_names)
        event.info(
            messages.UNINSTALLING_PACKAGES.format(packages=package_names_str)
        )
        apt.remove_packages(
            package_names,
            messages.UNINSTALLING_PACKAGES_FAILED.format(
                packages=package_names_str
            ),
        )

        return True

    @abc.abstractmethod
    def _perform_enable(self, silent: bool = False) -> bool:
        """
        Enable specific entitlement. This should be implemented by subclasses.
        This method does the actual enablement, and does not check can_enable
        or handle pre_enable or post_enable messaging.

        @return: True on success, False otherwise.
        """
        pass

    def detect_dependent_services(self) -> bool:
        """
        Check for depedent services.

        :return:
            True if there are dependent services enabled
            False if there are no dependent services enabled
        """
        for dependent_service_cls in self.dependent_services:
            ent_status, _ = dependent_service_cls(
                self.cfg
            ).application_status()
            if ent_status == ApplicationStatus.ENABLED:
                return True

        return False

    def check_required_services_active(self):
        """
        Check if all required services are active

        :return:
            True if all required services are active
            False is at least one of the required services is disabled
        """
        for required_service_cls in self.required_services:
            ent_status, _ = required_service_cls(self.cfg).application_status()
            if ent_status != ApplicationStatus.ENABLED:
                return False

        return True

    def blocking_incompatible_services(self) -> List[IncompatibleService]:
        """
        :return: List of incompatible services that are enabled
        """
        ret = []
        for service in self.incompatible_services:
            ent_status, _ = service.entitlement(self.cfg).application_status()
            if ent_status in (
                ApplicationStatus.ENABLED,
                ApplicationStatus.WARNING,
            ):
                ret.append(service)

        return ret

    def detect_incompatible_services(self) -> bool:
        """
        Check for incompatible services.

        :return:
            True if there are incompatible services enabled
            False if there are no incompatible services enabled
        """
        return len(self.blocking_incompatible_services()) > 0

    def handle_incompatible_services(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
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
        cfg_block_disable_on_enable = util.is_config_value_true(
            config=self.cfg.cfg,
            path_to_value="features.block_disable_on_enable",
        )
        for service in self.blocking_incompatible_services():
            ent = service.entitlement(self.cfg, assume_yes=True)

            user_msg = messages.INCOMPATIBLE_SERVICE.format(
                service_being_enabled=self.title,
                incompatible_service=ent.title,
            )

            e_msg = messages.INCOMPATIBLE_SERVICE_STOPS_ENABLE.format(
                service_being_enabled=self.title,
                incompatible_service=ent.title,
            )

            if cfg_block_disable_on_enable:
                return False, e_msg

            if not util.prompt_for_confirmation(
                msg=user_msg, assume_yes=self.assume_yes
            ):
                return False, e_msg

            event.info(
                messages.DISABLING_INCOMPATIBLE_SERVICE.format(
                    service=ent.title
                )
            )

            ret = ent.disable(silent=True)
            if not ret:
                return ret, None

        return True, None

    def _enable_required_services(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        """
        Prompt user when required services are found during enable.

        When enabling a service, we may find that there are required services
        that must be enabled first. In that situation, we can ask the user
        if the required service should be enabled before proceeding.
        """
        for required_service_cls in self.required_services:
            ent = required_service_cls(self.cfg, allow_beta=True)

            is_service_disabled = (
                ent.application_status()[0] == ApplicationStatus.DISABLED
            )

            if is_service_disabled:
                user_msg = messages.REQUIRED_SERVICE.format(
                    service_being_enabled=self.title,
                    required_service=ent.title,
                )

                e_msg = messages.REQUIRED_SERVICE_STOPS_ENABLE.format(
                    service_being_enabled=self.title,
                    required_service=ent.title,
                )

                if not util.prompt_for_confirmation(
                    msg=user_msg, assume_yes=self.assume_yes
                ):
                    return False, e_msg

                event.info(
                    messages.ENABLING_REQUIRED_SERVICE.format(
                        service=ent.title
                    )
                )
                ret, fail = ent.enable(silent=True)
                if not ret:
                    error_msg = ""
                    if fail and fail.message and fail.message.msg:
                        error_msg = "\n" + fail.message.msg

                    msg = messages.ERROR_ENABLING_REQUIRED_SERVICE.format(
                        error=error_msg, service=ent.title
                    )
                    return ret, msg

        return True, None

    def can_disable(
        self, ignore_dependent_services: bool = False
    ) -> Tuple[bool, Optional[CanDisableFailure]]:
        """Report whether or not disabling is possible for the entitlement.

        :return:
            (True, None) if can disable
            (False, CanDisableFailure) if can't disable
        """
        application_status, _ = self.application_status()

        if application_status == ApplicationStatus.DISABLED:
            return (
                False,
                CanDisableFailure(
                    CanDisableFailureReason.ALREADY_DISABLED,
                    message=messages.ALREADY_DISABLED.format(title=self.title),
                ),
            )

        applicability_status, _ = self.applicability_status()
        # applicability_status() returns APPLICABLE if not self.entitlement_cfg
        # but we want to be more strict and prevent disabling if
        # not self.entitlement_cfg, so we check it explicitly here.
        # This prevents e.g. landscape from being disabled on jammy when it
        # doesn't exist for jammy yet but was manually configured separately
        # from pro.
        if (
            not self.entitlement_cfg
            or applicability_status == ApplicabilityStatus.INAPPLICABLE
        ):
            return (
                False,
                CanDisableFailure(
                    CanDisableFailureReason.NOT_APPLICABLE,
                    message=messages.CANNOT_DISABLE_NOT_APPLICABLE.format(
                        title=self.title
                    ),
                ),
            )

        if self.dependent_services and not ignore_dependent_services:
            if self.detect_dependent_services():
                return (
                    False,
                    CanDisableFailure(
                        CanDisableFailureReason.ACTIVE_DEPENDENT_SERVICES
                    ),
                )

        if not self.supports_purge and self.purge:
            return (
                False,
                CanDisableFailure(
                    CanDisableFailureReason.PURGE_NOT_SUPPORTED,
                    messages.DISABLE_PURGE_NOT_SUPPORTED.format(
                        title=self.title
                    ),
                ),
            )

        return True, None

    def disable(
        self, silent: bool = False
    ) -> Tuple[bool, Optional[CanDisableFailure]]:
        """Disable specific entitlement

        @param silent: Boolean set True to silence print/log of messages

        @return: tuple of (success, optional reason)
            (True, None) on success.
            (False, reason) otherwise. reason is only non-None if it is a
                populated CanDisableFailure reason. This may expand to
                include other types of reasons in the future.
        """
        msg_ops = self.messaging.get("pre_disable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        can_disable, fail = self.can_disable()
        if not can_disable:
            if fail is None:
                # this shouldn't happen, but if it does we shouldn't continue
                return False, None
            elif (
                fail.reason
                == CanDisableFailureReason.ACTIVE_DEPENDENT_SERVICES
            ):
                ret, msg = self._disable_dependent_services(silent=silent)
                if not ret:
                    fail.message = msg
                    return False, fail
            else:
                # every other reason means we can't continue
                return False, fail

        if not self._perform_disable(silent=silent):
            return False, None

        if not self.handle_removing_required_packages():
            return False, None

        msg_ops = self.messaging.get("post_disable", [])
        if not util.handle_message_operations(msg_ops):
            return False, None

        self._check_for_reboot_msg(
            operation="disable operation", silent=silent
        )
        return True, None

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

    def _disable_dependent_services(
        self, silent: bool
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        """
        Disable dependent services

        When performing a disable operation, we might have
        other services that depend on the original services.
        If that is true, we will alert the user about this
        and prompt for confirmation to disable these services
        as well.

        @param silent: Boolean set True to silence print/log of messages
        """
        for dependent_service_cls in self.dependent_services:
            ent = dependent_service_cls(cfg=self.cfg, assume_yes=True)

            is_service_enabled = (
                ent.application_status()[0] == ApplicationStatus.ENABLED
            )

            if is_service_enabled:
                user_msg = messages.DEPENDENT_SERVICE.format(
                    dependent_service=ent.title,
                    service_being_disabled=self.title,
                )

                e_msg = messages.DEPENDENT_SERVICE_STOPS_DISABLE.format(
                    service_being_disabled=self.title,
                    dependent_service=ent.title,
                )

                if not util.prompt_for_confirmation(
                    msg=user_msg, assume_yes=self.assume_yes
                ):
                    return False, e_msg

                if not silent:
                    event.info(
                        messages.DISABLING_DEPENDENT_SERVICE.format(
                            required_service=ent.title
                        )
                    )

                ret, fail = ent.disable(silent=True)
                if not ret:
                    error_msg = ""
                    if fail and fail.message and fail.message.msg:
                        error_msg = "\n" + fail.message.msg

                    msg = messages.FAILED_DISABLING_DEPENDENT_SERVICE.format(
                        error=error_msg, required_service=ent.title
                    )
                    return False, msg

        return True, None

    def _check_for_reboot(self) -> bool:
        """Check if system needs to be rebooted."""
        return system.should_reboot()

    def _check_for_reboot_msg(
        self, operation: str, silent: bool = False
    ) -> None:
        """Check if user should be alerted that a reboot must be performed.

        @param operation: The operation being executed.
        @param silent: Boolean set True to silence print/log of messages
        """
        if self._check_for_reboot() and not silent:
            event.info(
                messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation=operation
                )
            )

    def applicability_status(
        self,
    ) -> Tuple[ApplicabilityStatus, Optional[messages.NamedMessage]]:
        """Check all contract affordances to vet current platform

        Affordances are a list of support constraints for the entitlement.
        Examples include a list of supported series, architectures for kernel
        revisions.

        :return:
            tuple of (ApplicabilityStatus, NamedMessage). APPLICABLE if
            platform passes all defined affordances, INAPPLICABLE if it doesn't
            meet all of the provided constraints.
        """
        entitlement_cfg = self.entitlement_cfg
        if not entitlement_cfg:
            return (
                ApplicabilityStatus.APPLICABLE,
                messages.NO_ENTITLEMENT_AFFORDANCES_CHECKED,
            )
        for error_message, functor, expected_result in self.static_affordances:
            if functor() != expected_result:
                return ApplicabilityStatus.INAPPLICABLE, error_message
        affordances = entitlement_cfg["entitlement"].get("affordances", {})
        affordance_arches = affordances.get("architectures", None)
        if (
            self.affordance_check_arch
            and affordance_arches is not None
            and system.get_dpkg_arch() not in affordance_arches
        ):
            deduplicated_arches = util.deduplicate_arches(affordance_arches)
            return (
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_ARCH.format(
                    title=self.title,
                    arch=system.get_dpkg_arch(),
                    supported_arches=", ".join(deduplicated_arches),
                ),
            )
        affordance_series = affordances.get("series", None)
        if (
            self.affordance_check_series
            and affordance_series is not None
            and system.get_release_info().series not in affordance_series
        ):
            return (
                ApplicabilityStatus.INAPPLICABLE,
                messages.INAPPLICABLE_SERIES.format(
                    title=self.title,
                    series=system.get_release_info().pretty_version,
                ),
            )
        kernel_info = system.get_kernel_info()
        affordance_kernels = affordances.get("kernelFlavors", None)
        affordance_min_kernel = affordances.get("minKernelVersion", None)
        if (
            self.affordance_check_kernel_flavor
            and affordance_kernels is not None
        ):
            if kernel_info.flavor not in affordance_kernels:
                return (
                    ApplicabilityStatus.INAPPLICABLE,
                    messages.INAPPLICABLE_KERNEL.format(
                        title=self.title,
                        kernel=kernel_info.uname_release,
                        supported_kernels=", ".join(affordance_kernels),
                    ),
                )
        if (
            self.affordance_check_kernel_min_version
            and affordance_min_kernel
            and kernel_info.major is not None
            and kernel_info.minor is not None
        ):
            invalid_msg = messages.INAPPLICABLE_KERNEL_VER.format(
                title=self.title,
                kernel=kernel_info.uname_release,
                min_kernel=affordance_min_kernel,
            )
            try:
                kernel_major, kernel_minor = affordance_min_kernel.split(".")
                min_kern_major = int(kernel_major)
                min_kern_minor = int(kernel_minor)
            except ValueError:
                LOG.warning(
                    "Could not parse minKernelVersion: %s",
                    affordance_min_kernel,
                )
                return (ApplicabilityStatus.INAPPLICABLE, invalid_msg)

            if kernel_info.major < min_kern_major:
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg
            elif (
                kernel_info.major == min_kern_major
                and kernel_info.minor < min_kern_minor
            ):
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg

        affordances_platform_check = affordances.get("platformChecks", {})
        ret, reason = self.verify_platform_checks(affordances_platform_check)

        if not ret:
            return (ApplicabilityStatus.INAPPLICABLE, reason)
        return ApplicabilityStatus.APPLICABLE, None

    def contract_status(self) -> ContractStatus:
        """Return whether the user is entitled to the entitlement or not"""
        if not _is_attached(self.cfg).is_attached:
            return ContractStatus.UNENTITLED
        entitlement_cfg = self.entitlement_cfg
        if entitlement_cfg and entitlement_cfg["entitlement"].get("entitled"):
            return ContractStatus.ENTITLED
        return ContractStatus.UNENTITLED

    def user_facing_status(
        self,
    ) -> Tuple[UserFacingStatus, Optional[messages.NamedMessage]]:
        """Return (user-facing status, details) for entitlement"""
        applicability, details = self.applicability_status()
        if applicability != ApplicabilityStatus.APPLICABLE:
            return UserFacingStatus.INAPPLICABLE, details
        entitlement_cfg = self.entitlement_cfg
        if not entitlement_cfg:
            return (
                UserFacingStatus.UNAVAILABLE,
                messages.SERVICE_NOT_ENTITLED.format(title=self.title),
            )
        elif entitlement_cfg["entitlement"].get("entitled", False) is False:
            return (
                UserFacingStatus.UNAVAILABLE,
                messages.SERVICE_NOT_ENTITLED.format(title=self.title),
            )

        application_status, explanation = self.application_status()

        if application_status == ApplicationStatus.DISABLED:
            return UserFacingStatus.INACTIVE, explanation
        elif application_status == ApplicationStatus.WARNING:
            return UserFacingStatus.WARNING, explanation

        warning, warn_msg = self.enabled_warning_status()

        if warning:
            return UserFacingStatus.WARNING, warn_msg

        return UserFacingStatus.ACTIVE, explanation

    @abc.abstractmethod
    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        """
        The current status of application of this entitlement

        :return:
            A tuple of (ApplicationStatus, human-friendly reason)
        """
        pass

    def enabled_warning_status(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        """
        If the entitlment is enabled, are there any warnings?
        The message is displayed as a Warning Notice in status output

        :return:
            A tuple of (warning bool, human-friendly reason)
        """
        return False, None

    def status_description_override(
        self,
    ) -> Optional[str]:
        return None

    def is_access_expired(self) -> bool:
        """Return entitlement access info as stale and needing refresh."""
        # TODO(No expiry per resource in MVP yet)
        expire_str = self.entitlement_cfg.get("expires")
        if not expire_str:
            return False
        expiry = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        if expiry >= datetime.utcnow():
            return False
        return True

    def _check_application_status_on_cache(self) -> ApplicationStatus:
        """Check on the state of application on the status cache."""
        status_cache = self.cfg.read_cache("status-cache")

        if status_cache is None:
            return ApplicationStatus.DISABLED

        services_status_list = status_cache.get("services", [])

        for service in services_status_list:
            if service.get("name") == self.name:
                service_status = service.get("status")

                if service_status == "enabled":
                    return ApplicationStatus.ENABLED
                else:
                    return ApplicationStatus.DISABLED

        return ApplicationStatus.DISABLED

    def _should_enable_by_default(
        self, obligations: Dict[str, Any], resourceToken: Optional[str]
    ) -> bool:
        return bool(obligations.get("enableByDefault") and resourceToken)

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
        :raise: UbuntuProError when auto-enable fails unexpectedly.
        """
        if not deltas:
            return True  # We processed all deltas that needed processing

        delta_entitlement = deltas.get("entitlement", {})
        delta_directives = delta_entitlement.get("directives", {})
        status_cache = self.cfg.read_cache("status-cache")

        transition_to_unentitled = bool(delta_entitlement == util.DROPPED_KEY)
        if not transition_to_unentitled:
            if delta_entitlement:
                contract.apply_contract_overrides(deltas)
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

            if application_status != ApplicationStatus.DISABLED:
                if self.can_disable():
                    LOG.info(
                        "Disabling %s after refresh transition to unentitled"
                    )
                    self.disable()
                    msg = (
                        "Due to contract refresh, " "'{}' is now disabled."
                    ).format(self.name)
                    event.info(
                        messages.DISABLE_DURING_CONTRACT_REFRESH.format(
                            service=self.name
                        )
                    )
                else:
                    LOG.warning(
                        "Cannot disable %s after refresh transition to "
                        "unentitled"
                    )
                    event.info(
                        messages.UNABLE_TO_DISABLE_DURING_CONTRACT_REFRESH.format(  # noqa: E501
                            service=self.name
                        )
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
        enable_by_default = self._should_enable_by_default(
            delta_obligations, resourceToken
        )

        if enable_by_default:
            self.allow_beta = True

        can_enable, _ = self.can_enable()
        if can_enable and enable_by_default:
            if allow_enable:
                msg = messages.ENABLE_BY_DEFAULT_TMPL.format(name=self.name)

                event.info(msg, file_type=sys.stderr)
                self.enable()
            else:
                msg = messages.ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
                    name=self.name
                )
                event.info(msg, file_type=sys.stderr)
            return True

        return False

    def _update_sources_list(self):
        if self._is_sources_list_updated:
            return
        event.info(messages.APT_UPDATING_LIST.format(name="standard Ubuntu"))
        apt.update_sources_list(apt.get_system_sources_file())
        self._is_sources_list_updated = True
