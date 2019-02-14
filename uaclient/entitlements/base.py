import abc
from datetime import datetime
import os
import six

from uaclient import config
from uaclient import contract
from uaclient import status
from uaclient import util


@six.add_metaclass(abc.ABCMeta)
class UAEntitlement(object):

    # The lowercase name of this entitlement
    name = None
    # The human readable title of this entitlement
    title = None
    # A sentence describing this entitlement
    description = None

    # A tuple of 3-tuples with (failure_message, functor, expected_results)
    # If any static_affordance does not match expected_results fail with
    # <failure_message>.
    static_affordances = ()   # Overridden in livepatch and fips

    def __init__(self, cfg=None):
        """Setup UAEntitlement instance

        @param config: Parsed configuration dictionary
        """
        if not cfg:
            cfg = config.UAConfig()
        self.cfg = cfg

    @abc.abstractmethod
    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        pass

    def can_disable(self, silent=False, force=False):
        """Report whether or not disabling is possible for the entitlement.

        @param silent: Boolean set True to silence printed messages/warnings.
        @param force: Boolean set True to allow disable even if entitlement
            doesn't appear 'enabled'.
        """
        message = ''
        retval = True
        if os.getuid() != 0:   # Ignore 'force' here. We always need sudo check
            message = status.MESSAGE_NONROOT_USER
            retval = False
        elif not any([self.cfg.is_attached, force]):
            message = status.MESSAGE_UNATTACHED
            retval = False
        elif not any([self.contract_status() == status.ENTITLED, force]):
            message = status.MESSAGE_UNENTITLED_TMPL.format(title=self.title)
            retval = False
        elif not force:
            op_status, _status_details = self.operational_status()
            if op_status == status.INACTIVE:
                message = status.MESSAGE_ALREADY_DISABLED_TMPL.format(
                          title=self.title)
                retval = False
        if message and not silent:
            print(message)
        return retval

    def can_enable(self):
        """Report whether or not enabling is possible for the entitlement."""
        if os.getuid() != 0:
            print(status.MESSAGE_NONROOT_USER)
            return False
        if not self.cfg.is_attached:
            print(status.MESSAGE_UNATTACHED)
            return False
        if self.is_access_expired():
            machine_secret = self.cfg.machine_token['machineSecret']
            contract_client = contract.UAContractClient(self.cfg)
            contract_client.request_resource_machine_access(
                machine_secret, self.name)
        if not self.contract_status() == status.ENTITLED:
            print(status.MESSAGE_UNENTITLED_TMPL.format(title=self.title))
            return False
        op_status, op_status_details = self.operational_status()
        if op_status == status.ACTIVE:
            print(status.MESSAGE_ALREADY_ENABLED_TMPL.format(title=self.title))
            return False
        if op_status == status.INAPPLICABLE:
            print(op_status_details)
            return False
        return True

    def check_affordances(self):
        """Check all contract affordances to vet current platform

        Affordances are a list of support constraints for the entitlement.
        Examples include a list of supported series, architectures for kernel
        revisions.

        @return: Tuple (boolean, detailed_message). True if platform passes
            all defined affordances, False if it doesn't meet any of the
            provided constraints.
        """
        entitlements = self.cfg.entitlements
        entitlement_cfg = entitlements.get(self.name)
        if entitlement_cfg:
            affordances = entitlement_cfg['entitlement'].get('affordances', {})
            series = util.get_platform_info('series')
            affordance_series = affordances.get('series')
            if affordance_series and series not in affordance_series:
                return False, status.MESSAGE_INAPPLICABLE_SERIES_TMPL.format(
                                  title=self.title, series=series)
        for error_message, functor, expected_result in self.static_affordances:
            if functor() != expected_result:
                return False, error_message
        return True, ''

    @abc.abstractmethod
    def disable(self, silent=False, force=False):
        """Disable specific entitlement

        @param silent: Boolean set True to silence print/log of messages
        @param force: Boolean set True to perform disable logic even if
            entitlement doesn't appear fully configured.

        @return: True on success, False otherwise.
        """
        pass

    def contract_status(self):
        """Return whether contract entitlement is ENTITLED or NONE."""
        if not self.cfg.is_attached:
            return status.NONE
        entitlement_cfg = self.cfg.entitlements.get(self.name, {})
        if entitlement_cfg and entitlement_cfg['entitlement'].get('entitled'):
            return status.ENTITLED
        return status.NONE

    def is_access_expired(self):
        """Return entitlement access info as stale and needing refresh."""
        entitlement_contract = self.cfg.entitlements.get(self.name, {})
        expire_str = entitlement_contract.get('expires')
        if not expire_str:
            return False
        expiry = datetime.strptime(expire_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        if expiry >= datetime.utcnow():
            return False
        return True

    @abc.abstractmethod
    def operational_status(self):
        """Return whether entitlement is ACTIVE, INACTIVE or UNAVAILABLE"""
        pass
