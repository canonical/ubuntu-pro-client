import abc
from datetime import datetime
import logging
import re

try:
    from typing import Any, Callable, Dict, Optional, Tuple  # noqa: F401
    StaticAffordance = Tuple[str, Callable[[], Any], bool]
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

from uaclient import config
from uaclient import contract
from uaclient import status
from uaclient import util
from uaclient.status import (
    ApplicabilityStatus, ContractStatus, UserFacingStatus)

RE_KERNEL_UNAME = (
    r'(?P<major>[\d]+)[.-](?P<minor>[\d]+)[.-](?P<patch>[\d]+\-[\d]+)'
    r'-(?P<flavor>[A-Za-z0-9_-]+)')


class UAEntitlement(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The lowercase name of this entitlement"""
        pass

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

    # A tuple of 3-tuples with (failure_message, functor, expected_results)
    # If any static_affordance does not match expected_results fail with
    # <failure_message>. Overridden in livepatch and fips
    static_affordances = ()  # type: Tuple[StaticAffordance, ...]

    def __init__(self, cfg: 'Optional[config.UAConfig]' = None) -> None:
        """Setup UAEntitlement instance

        @param config: Parsed configuration dictionary
        """
        if not cfg:
            cfg = config.UAConfig()
        self.cfg = cfg

    @abc.abstractmethod
    def enable(self, *, silent_if_inapplicable: bool = False) -> bool:
        """Enable specific entitlement.

        :param silent_if_inapplicable:
            Don't emit any messages until after it has been determined that
            this entitlement is applicable to the current machine.

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
                print(status.MESSAGE_ALREADY_DISABLED_TMPL.format(
                    title=self.title))
            return False
        return True

    def can_enable(self, silent: bool = False) -> bool:
        """
        Report whether or not enabling is possible for the entitlement.

        :param silent: if True, suppress output
        """
        if self.is_access_expired():
            token = self.cfg.machine_token['machineToken']
            contract_client = contract.UAContractClient(self.cfg)
            contract_client.request_resource_machine_access(
                token, self.name)
        if not self.contract_status() == ContractStatus.ENTITLED:
            if not silent:
                print(status.MESSAGE_UNENTITLED_TMPL.format(title=self.title))
            return False
        application_status, _ = self.application_status()
        if application_status != status.ApplicationStatus.DISABLED:
            if not silent:
                print(status.MESSAGE_ALREADY_ENABLED_TMPL.format(
                    title=self.title))
            return False
        applicability_status, details = self.applicability_status()
        if applicability_status == status.ApplicabilityStatus.INAPPLICABLE:
            if not silent:
                print(details)
            return False
        return True

    def applicability_status(self) -> 'Tuple[ApplicabilityStatus, str]':
        """Check all contract affordances to vet current platform

        Affordances are a list of support constraints for the entitlement.
        Examples include a list of supported series, architectures for kernel
        revisions.

        :return:
            tuple of (ApplicabilityStatus, detailed_message).  APPLICABLE if
            platform passes all defined affordances, INAPPLICABLE if it doesn't
            meet all of the provided constraints.
        """
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if not entitlement_cfg:
            return (ApplicabilityStatus.APPLICABLE,
                    'no entitlement affordances checked')
        affordances = entitlement_cfg['entitlement'].get('affordances', {})
        platform = util.get_platform_info()
        affordance_arches = affordances.get('architectures', [])
        if affordance_arches and platform['arch'] not in affordance_arches:
            return (ApplicabilityStatus.INAPPLICABLE,
                    status.MESSAGE_INAPPLICABLE_ARCH_TMPL.format(
                        title=self.title, arch=platform['arch'],
                        supported_arches=', '.join(affordance_arches)))
        affordance_series = affordances.get('series', [])
        if affordance_series and platform['series'] not in affordance_series:
            return (ApplicabilityStatus.INAPPLICABLE,
                    status.MESSAGE_INAPPLICABLE_SERIES_TMPL.format(
                        title=self.title, series=platform['version']))
        kernel = platform['kernel']
        affordance_kernels = affordances.get('kernelFlavors', [])
        affordance_min_kernel = affordances.get('minKernelVersion')
        match = re.match(RE_KERNEL_UNAME, kernel)
        if affordance_kernels:
            if not match or match.group('flavor') not in affordance_kernels:
                return (ApplicabilityStatus.INAPPLICABLE,
                        status.MESSAGE_INAPPLICABLE_KERNEL_TMPL.format(
                            title=self.title, kernel=kernel,
                            supported_kernels=', '.join(affordance_kernels)))
        if affordance_min_kernel:
            invalid_msg = status.MESSAGE_INAPPLICABLE_KERNEL_VER_TMPL.format(
                title=self.title, kernel=kernel,
                min_kernel=affordance_min_kernel)
            try:
                kernel_major, kernel_minor = affordance_min_kernel.split('.')
                min_kern_major = int(kernel_major)
                min_kern_minor = int(kernel_minor)
            except ValueError:
                logging.warning(
                    'Could not parse minKernelVersion: %s',
                    affordance_min_kernel)
                return (ApplicabilityStatus.INAPPLICABLE, invalid_msg)

            if not match:
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg
            if any([int(match.group('major')) < min_kern_major,
                    int(match.group('minor')) < min_kern_minor]):
                return ApplicabilityStatus.INAPPLICABLE, invalid_msg
        for error_message, functor, expected_result in self.static_affordances:
            if functor() != expected_result:
                return ApplicabilityStatus.INAPPLICABLE, error_message
        return ApplicabilityStatus.APPLICABLE, ''

    @abc.abstractmethod
    def disable(self, silent: bool = False) -> bool:
        """Disable specific entitlement

        @param silent: Boolean set True to silence print/log of messages

        @return: True on success, False otherwise.
        """
        pass

    def contract_status(self) -> ContractStatus:
        """Return whether the user is entitled to the entitlement or not"""
        if not self.cfg.is_attached:
            return ContractStatus.UNENTITLED
        entitlement_cfg = self.cfg.entitlements.get(self.name, {})
        if entitlement_cfg and entitlement_cfg['entitlement'].get('entitled'):
            return ContractStatus.ENTITLED
        return ContractStatus.UNENTITLED

    def is_access_expired(self) -> bool:
        """Return entitlement access info as stale and needing refresh."""
        entitlement_contract = self.cfg.entitlements.get(self.name, {})
        # TODO(No expiry per resource in MVP yet)
        expire_str = entitlement_contract.get('expires')
        if not expire_str:
            return False
        expiry = datetime.strptime(expire_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        if expiry >= datetime.utcnow():
            return False
        return True

    def process_contract_deltas(
            self, orig_access: 'Dict[str, Any]',
            deltas: 'Dict[str, Any]', allow_enable: bool = False) -> bool:
        """Process any contract access deltas for this entitlement.

        :param orig_access: Dictionary containing the original
            resourceEntitlement access details.
        :param deltas: Dictionary which contains only the changed access keys
        and values.
        :param allow_enable: Boolean set True if allowed to perform the enable
            operation. When False, a message will be logged to inform the user
            about the recommended enabled service.

        :return: True when delta operations are processed; False when noop.
        """
        if not deltas:
            return True  # We processed all deltas that needed processing

        delta_entitlement = deltas.get('entitlement', {})
        transition_to_unentitled = bool(delta_entitlement == util.DROPPED_KEY)
        if not transition_to_unentitled:
            if delta_entitlement:
                util.apply_series_overrides(deltas)
                delta_entitlement = deltas['entitlement']
            if orig_access and 'entitled' in delta_entitlement:
                transition_to_unentitled = (
                    delta_entitlement['entitled'] in (False, util.DROPPED_KEY))
        if transition_to_unentitled:
            application_status, _ = self.application_status()
            if application_status != status.ApplicationStatus.DISABLED:
                if self.can_disable(silent=True):
                    self.disable()
                    logging.info(
                        "Due to contract refresh, '%s' is now disabled.",
                        self.name)
                else:
                    logging.warning(
                        "Unable to disable '%s' as recommended during contract"
                        " refresh. Service is still active. See `ua status`" %
                        self.name)
            # Clean up former entitled machine-access-<name> response cache
            # file because uaclient doesn't access machine-access-* routes or
            # responses on unentitled services.
            self.cfg.delete_cache_key('machine-access-%s' % self.name)
            return True

        resourceToken = orig_access.get('resourceToken')
        if not resourceToken:
            resourceToken = deltas.get('resourceToken')
        delta_obligations = delta_entitlement.get('obligations', {})
        can_enable = self.can_enable(silent=True)
        enableByDefault = bool(
            delta_obligations.get('enableByDefault') and resourceToken)
        if can_enable and enableByDefault:
            if allow_enable:
                msg = status.MESSAGE_ENABLE_BY_DEFAULT_TMPL.format(
                    name=self.name)
                logging.info(msg)
                self.enable()
            else:
                msg = status.MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
                    name=self.name)
                logging.info(msg)
            return True

        return False

    def user_facing_status(self) -> 'Tuple[UserFacingStatus, str]':
        """Return (user-facing status, details) for entitlement"""
        applicability, details = self.applicability_status()
        if applicability != ApplicabilityStatus.APPLICABLE:
            return UserFacingStatus.INAPPLICABLE, details
        entitlement_cfg = self.cfg.entitlements.get(self.name)
        if not entitlement_cfg:
            return (UserFacingStatus.INAPPLICABLE,
                    '%s is not entitled' % self.title)
        elif entitlement_cfg['entitlement'].get('entitled', False) is False:
            return (UserFacingStatus.INAPPLICABLE,
                    '%s is not entitled' % self.title)

        application_status, explanation = self.application_status()
        user_facing_status = {
            status.ApplicationStatus.ENABLED: UserFacingStatus.ACTIVE,
            status.ApplicationStatus.DISABLED: UserFacingStatus.INACTIVE,
            status.ApplicationStatus.PENDING: UserFacingStatus.PENDING,
        }[application_status]
        return user_facing_status, explanation

    @abc.abstractmethod
    def application_status(self) -> 'Tuple[status.ApplicationStatus, str]':
        """
        The current status of application of this entitlement

        :return:
            A tuple of (ApplicationStatus, human-friendly reason)
        """
        pass
