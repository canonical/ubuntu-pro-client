import logging
from typing import Any, Dict, Optional, Tuple

from uaclient import (
    event_logger,
    exceptions,
    http,
    livepatch,
    messages,
    snap,
    system,
)
from uaclient.entitlements.base import IncompatibleService, UAEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.types import StaticAffordance

LIVEPATCH_RETRIES = [0.5, 1.0]

ERROR_MSG_MAP = {
    "Unknown Auth-Token": "Invalid Auth-Token provided to livepatch.",
    "unsupported kernel": "Your running kernel is not supported by Livepatch.",
}

event = event_logger.get_event_logger()


class LivepatchEntitlement(UAEntitlement):

    help_doc_url = "https://ubuntu.com/security/livepatch"
    name = "livepatch"
    title = "Livepatch"
    description = "Canonical Livepatch service"
    affordance_check_kernel_min_version = False
    affordance_check_kernel_flavor = False
    # we do want to check series because livepatch errors on non-lts releases
    affordance_check_series = True
    # we still need to check arch because the livepatch-client is not built
    # for all arches
    affordance_check_arch = True

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        from uaclient.entitlements.fips import FIPSEntitlement
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            IncompatibleService(
                FIPSEntitlement, messages.LIVEPATCH_INVALIDATES_FIPS
            ),
            IncompatibleService(
                RealtimeKernelEntitlement,
                messages.REALTIME_LIVEPATCH_INCOMPATIBLE,
            ),
        )

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        # Use a lambda so we can mock system.is_container in tests
        from uaclient.entitlements.fips import FIPSEntitlement

        fips_ent = FIPSEntitlement(self.cfg)

        is_fips_enabled = bool(
            fips_ent.application_status()[0] == ApplicationStatus.ENABLED
        )

        return (
            (
                messages.SERVICE_ERROR_INSTALL_ON_CONTAINER.format(
                    title=self.title
                ),
                lambda: system.is_container(),
                False,
            ),
            (
                messages.LIVEPATCH_ERROR_WHEN_FIPS_ENABLED,
                lambda: is_fips_enabled,
                False,
            ),
        )

    def _perform_enable(self, silent: bool = False) -> Tuple[bool, bool]:
        """Enable specific entitlement.

        @return: Tuple:
            True on success, False otherwise.
            True if an apt update is required before post_enable.
        """
        if not system.which(snap.SNAP_CMD):
            event.info("Installing snapd")
            snap.install_snapd()

        elif not snap.is_snapd_installed():
            raise exceptions.SnapdNotProperlyInstalledError(
                snap_cmd=snap.SNAP_CMD, service=self.title
            )

        snap.run_snapd_wait_cmd()

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
        if not livepatch.is_livepatch_installed():
            event.info("Installing canonical-livepatch snap")
            try:
                snap.install_snap("canonical-livepatch")
            except exceptions.ProcessExecutionError as e:
                raise exceptions.ErrorInstallingLivepatch(error_msg=str(e))

        livepatch.configure_livepatch_proxy(http_proxy, https_proxy)

        return (
            self.setup_livepatch_config(
                process_directives=True, process_token=True
            ),
            False,
        )

    def setup_livepatch_config(
        self, process_directives: bool = True, process_token: bool = True
    ) -> bool:
        """Process configuration setup for livepatch directives.

        :param process_directives: Boolean set True when directives should be
            processsed.
        :param process_token: Boolean set True when token should be
            processsed.
        """
        entitlement_cfg = self.cfg.machine_token_file.entitlements.get(
            self.name
        )
        if process_directives:
            try:
                process_config_directives(entitlement_cfg)
            except exceptions.ProcessExecutionError as e:
                msg = "Unable to configure Livepatch: " + str(e)
                event.info(msg)
                logging.error(msg)
                return False
        if process_token:
            livepatch_token = entitlement_cfg.get("resourceToken")
            if not livepatch_token:
                logging.debug(
                    "No specific resourceToken present. Using machine token as"
                    " %s credentials",
                    self.title,
                )
                livepatch_token = self.cfg.machine_token["machineToken"]
            application_status, _details = self.application_status()
            if application_status != ApplicationStatus.DISABLED:
                logging.info(
                    "Disabling %s prior to re-attach with new token",
                    self.title,
                )
                try:
                    system.subp([livepatch.LIVEPATCH_CMD, "disable"])
                except exceptions.ProcessExecutionError as e:
                    logging.error(str(e))
                    return False
            try:
                system.subp(
                    [livepatch.LIVEPATCH_CMD, "enable", livepatch_token],
                    capture=True,
                )
            except exceptions.ProcessExecutionError as e:
                msg = "Unable to enable Livepatch: "
                for error_message, print_message in ERROR_MSG_MAP.items():
                    if error_message in str(e):
                        msg += print_message
                        break
                if msg == "Unable to enable Livepatch: ":
                    msg += str(e)
                event.info(msg)
                return False
            event.info("Canonical livepatch enabled.")
        return True

    def _perform_disable(self, silent=False):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not livepatch.is_livepatch_installed():
            return True
        system.subp([livepatch.LIVEPATCH_CMD, "disable"], capture=True)
        return True

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        status = (ApplicationStatus.ENABLED, None)

        if not livepatch.is_livepatch_installed():
            return (ApplicationStatus.DISABLED, messages.LIVEPATCH_NOT_ENABLED)

        if livepatch.status() is None:
            # TODO(May want to parse INACTIVE/failure assessment)
            return (
                ApplicationStatus.DISABLED,
                messages.LIVEPATCH_APPLICATION_STATUS_CLIENT_FAILURE,
            )
        return status

    def enabled_warning_status(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        support = livepatch.on_supported_kernel()
        if support == livepatch.LivepatchSupport.UNSUPPORTED:
            kernel_info = system.get_kernel_info()
            return (
                True,
                messages.LIVEPATCH_KERNEL_NOT_SUPPORTED.format(
                    version=kernel_info.uname_release,
                    arch=kernel_info.uname_machine_arch,
                ),
            )
        if support == livepatch.LivepatchSupport.KERNEL_EOL:
            kernel_info = system.get_kernel_info()
            return (
                True,
                messages.LIVEPATCH_KERNEL_EOL.format(
                    version=kernel_info.uname_release,
                    arch=kernel_info.uname_machine_arch,
                ),
            )
        if support == livepatch.LivepatchSupport.KERNEL_UPGRADE_REQUIRED:
            return (
                True,
                messages.LIVEPATCH_KERNEL_UPGRADE_REQUIRED,
            )
        # if on_supported_kernel returns UNKNOWN we default to no warning
        # because there would be no way for a user to resolve the warning
        return False, None

    def status_description_override(self):
        if (
            livepatch.on_supported_kernel()
            == livepatch.LivepatchSupport.UNSUPPORTED
            and not system.is_container()
        ):
            return messages.LIVEPATCH_KERNEL_NOT_SUPPORTED_DESCRIPTION
        return None

    def process_contract_deltas(
        self,
        orig_access: Dict[str, Any],
        deltas: Dict[str, Any],
        allow_enable: bool = False,
    ) -> Tuple[bool, bool]:
        """Process any contract access deltas for this entitlement.

        :param orig_access: Dictionary containing the original
            resourceEntitlement access details.
        :param deltas: Dictionary which contains only the changed access keys
        and values.
        :param allow_enable: Boolean set True if allowed to perform the enable
            operation. When False, a message will be logged to inform the user
            about the recommended enabled service.

        :return: Tuple with:
            True when delta operations are processed; False when noop.
            True when an apt update is required, False otherwise.
        """
        processed, apt_update = super().process_contract_deltas(
            orig_access, deltas, allow_enable
        )
        if processed:
            return True, apt_update  # Already processed parent class deltas

        delta_entitlement = deltas.get("entitlement", {})
        process_enable_default = delta_entitlement.get("obligations", {}).get(
            "enabledByDefault", False
        )

        if process_enable_default:
            enable_success, _, apt_update = self.enable()
            return enable_success, apt_update

        application_status, _ = self.application_status()
        if application_status == ApplicationStatus.DISABLED:
            # only operate on changed directives when ACTIVE
            return False, False
        delta_directives = delta_entitlement.get("directives", {})
        supported_deltas = set(["caCerts", "remoteServer"])
        process_directives = bool(
            supported_deltas.intersection(delta_directives)
        )
        process_token = bool(deltas.get("resourceToken", False))
        if any([process_directives, process_token]):
            logging.info("Updating '%s' on changed directives.", self.name)
            return (
                self.setup_livepatch_config(
                    process_directives=process_directives,
                    process_token=process_token,
                ),
                True,
            )
        return True, True


def process_config_directives(cfg):
    """Process livepatch configuration directives.

    We process caCerts before remoteServer because changing remote-server
    in the canonical-livepatch CLI performs a PUT against the new server name.
    If new caCerts were required for the new remoteServer, this
    canonical-livepatch client PUT could fail on unmatched old caCerts.

    @raises: ProcessExecutionError if unable to configure livepatch.
    """
    if not cfg:
        return
    directives = cfg.get("entitlement", {}).get("directives", {})
    ca_certs = directives.get("caCerts")
    if ca_certs:
        system.subp(
            [
                livepatch.LIVEPATCH_CMD,
                "config",
                "ca-certs={}".format(ca_certs),
            ],
            capture=True,
        )
    remote_server = directives.get("remoteServer", "")
    if remote_server.endswith("/"):
        remote_server = remote_server[:-1]
    if remote_server:
        system.subp(
            [
                livepatch.LIVEPATCH_CMD,
                "config",
                "remote-server={}".format(remote_server),
            ],
            capture=True,
        )
