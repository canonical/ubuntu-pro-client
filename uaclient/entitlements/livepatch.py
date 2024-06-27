import logging
from typing import Any, Dict, Optional, Tuple

from uaclient import (
    api,
    event_logger,
    exceptions,
    http,
    livepatch,
    messages,
    snap,
    system,
    util,
)
from uaclient.entitlements.base import EntitlementWithMessage, UAEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.types import StaticAffordance

LIVEPATCH_RETRIES = [0.5, 1.0]

ERROR_MSG_MAP = {
    "Unknown Auth-Token": "Invalid Auth-Token provided to livepatch.",
    "unsupported kernel": "Your running kernel is not supported by Livepatch.",
}

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class LivepatchEntitlement(UAEntitlement):
    help_doc_url = messages.urls.LIVEPATCH_HOME_PAGE
    name = "livepatch"
    title = messages.LIVEPATCH_TITLE
    description = messages.LIVEPATCH_DESCRIPTION
    help_text = messages.LIVEPATCH_HELP_TEXT
    affordance_check_kernel_min_version = False
    affordance_check_kernel_flavor = False
    # we do want to check series because livepatch errors on non-lts releases
    affordance_check_series = True
    # we still need to check arch because the livepatch-client is not built
    # for all arches
    affordance_check_arch = True

    @property
    def incompatible_services(self) -> Tuple[EntitlementWithMessage, ...]:
        from uaclient.entitlements.fips import FIPSEntitlement
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            EntitlementWithMessage(
                FIPSEntitlement, messages.LIVEPATCH_INVALIDATES_FIPS
            ),
            EntitlementWithMessage(
                RealtimeKernelEntitlement,
                messages.REALTIME_LIVEPATCH_INCOMPATIBLE,
            ),
        )

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        # Use a lambda so we can mock system.is_container in tests
        from uaclient.entitlements.fips import FIPSEntitlement

        fips_ent = FIPSEntitlement(cfg=self.cfg)

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

    def enable_steps(self) -> int:
        return 2

    def disable_steps(self) -> int:
        return 1

    def _perform_enable(self, progress: api.ProgressWrapper) -> bool:
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        progress.progress(messages.INSTALLING_LIVEPATCH)

        if not snap.is_snapd_installed():
            progress.emit(
                "info", messages.INSTALLING_PACKAGES.format(packages="snapd")
            )
            snap.install_snapd()

        if not snap.is_snapd_installed_as_a_snap():
            progress.emit(
                "info",
                messages.INSTALLING_PACKAGES.format(packages="snapd snap"),
            )
            try:
                snap.install_snap("snapd")
            except exceptions.ProcessExecutionError as e:
                LOG.warning("Failed to install snapd as a snap", exc_info=e)
                progress.emit(
                    "info",
                    messages.EXECUTING_COMMAND_FAILED.format(
                        command="snap install snapd"
                    ),
                )

        snap.run_snapd_wait_cmd(progress)

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
        if not livepatch.is_livepatch_installed():
            progress.emit(
                "info",
                messages.INSTALLING_PACKAGES.format(
                    packages="canonical-livepatch snap"
                ),
            )
            try:
                snap.install_snap("canonical-livepatch")
            except exceptions.ProcessExecutionError as e:
                raise exceptions.ErrorInstallingLivepatch(error_msg=str(e))

        livepatch.configure_livepatch_proxy(http_proxy, https_proxy)

        return self.setup_livepatch_config(
            progress, process_directives=True, process_token=True
        )

    def setup_livepatch_config(
        self,
        progress: api.ProgressWrapper,
        process_directives: bool = True,
        process_token: bool = True,
    ) -> bool:
        """Processs configuration setup for livepatch directives.

        :param process_directives: Boolean set True when directives should be
            processsed.
        :param process_token: Boolean set True when token should be
            processsed.
        """
        progress.progress(messages.SETTING_UP_LIVEPATCH)

        entitlement_cfg = self.machine_token_file.entitlements().get(self.name)
        if process_directives:
            try:
                process_config_directives(entitlement_cfg)
            except exceptions.ProcessExecutionError as e:
                LOG.error(str(e), exc_info=e)
                progress.emit(
                    "info",
                    messages.LIVEPATCH_UNABLE_TO_CONFIGURE.format(
                        error_msg=str(e)
                    ),
                )
                return False
        if process_token:
            livepatch_token = entitlement_cfg.get("resourceToken")
            if not livepatch_token:
                LOG.debug(
                    "No specific resourceToken present. Using machine token as"
                    " %s credentials",
                    self.title,
                )
                livepatch_token = self.machine_token_file.machine_token[
                    "machineToken"
                ]
            application_status, _details = self.application_status()
            if application_status != ApplicationStatus.DISABLED:
                LOG.info("Disabling livepatch before re-enabling")
                progress.emit("info", messages.LIVEPATCH_DISABLE_REATTACH)
                try:
                    system.subp([livepatch.LIVEPATCH_CMD, "disable"])
                except exceptions.ProcessExecutionError as e:
                    LOG.error(str(e), exc_info=e)
                    return False
            try:
                system.subp(
                    [livepatch.LIVEPATCH_CMD, "enable", livepatch_token],
                    capture=True,
                )
            except exceptions.ProcessExecutionError as e:
                msg = messages.LIVEPATCH_UNABLE_TO_ENABLE
                for error_message, print_message in ERROR_MSG_MAP.items():
                    if error_message in str(e):
                        msg += print_message
                        break
                if msg == messages.LIVEPATCH_UNABLE_TO_ENABLE:
                    msg += str(e)
                progress.emit("info", msg)
                return False
        return True

    def _perform_disable(self, progress: api.ProgressWrapper):
        """Disable specific entitlement

        @return: True on success, False otherwise.
        """
        if not livepatch.is_livepatch_installed():
            return True
        cmd = [livepatch.LIVEPATCH_CMD, "disable"]
        progress.progress(
            messages.EXECUTING_COMMAND.format(command=" ".join(cmd))
        )
        system.subp(cmd, capture=True)
        return True

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        status = (ApplicationStatus.ENABLED, None)

        if not livepatch.is_livepatch_installed():
            return (ApplicationStatus.DISABLED, messages.LIVEPATCH_NOT_ENABLED)

        try:
            livepatch_status = livepatch.status()
        except exceptions.ProcessExecutionError as e:
            return (
                ApplicationStatus.WARNING,
                messages.LIVEPATCH_CLIENT_FAILURE_WARNING.format(
                    livepatch_error=e.stderr,
                ),
            )

        if livepatch_status is None:
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
        """
        if super().process_contract_deltas(orig_access, deltas, allow_enable):
            return True  # Already processed parent class deltas

        delta_entitlement = deltas.get("entitlement", {})
        process_enable_default = delta_entitlement.get("obligations", {}).get(
            "enableByDefault", False
        )

        if process_enable_default:
            enable_success, _ = self.enable(api.ProgressWrapper())
            return enable_success

        application_status, _ = self.application_status()
        if application_status == ApplicationStatus.DISABLED:
            return False  # only operate on changed directives when ACTIVE
        delta_directives = delta_entitlement.get("directives", {})
        supported_deltas = set(["caCerts", "remoteServer"])
        process_directives = bool(
            supported_deltas.intersection(delta_directives)
        )
        process_token = bool(deltas.get("resourceToken", False))
        if any([process_directives, process_token]):
            LOG.info(
                "New livepatch directives or token. running "
                "setup_livepatch_config"
            )
            event.info(
                messages.SERVICE_UPDATING_CHANGED_DIRECTIVES.format(
                    service=self.name
                )
            )
            return self.setup_livepatch_config(
                progress=api.ProgressWrapper(),
                process_directives=process_directives,
                process_token=process_token,
            )
        return True


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
