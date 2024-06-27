import logging
from typing import Any, Dict, Optional, Tuple

from uaclient import api, event_logger, exceptions, messages, system, util
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))
event = event_logger.get_event_logger()


class LandscapeEntitlement(UAEntitlement):
    name = "landscape"
    title = messages.LANDSCAPE_TITLE
    description = messages.LANDSCAPE_DESCRIPTION
    help_doc_url = messages.urls.LANDSCAPE_HOME_PAGE
    help_text = messages.LANDSCAPE_HELP_TEXT

    def enable_steps(self) -> int:
        return 1

    def disable_steps(self) -> int:
        return 1

    def _perform_enable(self, progress: api.ProgressWrapper) -> bool:
        cmd = ["landscape-config"] + self.extra_args
        if not progress.is_interactive() and "--silent" not in cmd:
            cmd += ["--silent"]

        LOG.debug("Executing: %r", cmd)
        progress.progress(
            util.redact_sensitive_logs(
                messages.EXECUTING_COMMAND.format(command=" ".join(cmd))
            )
        )
        try:
            system.subp(cmd, pipe_stdouterr=not progress.is_interactive())
        except exceptions.ProcessExecutionError as e:
            LOG.exception(e)
            if not progress.is_interactive():
                progress.emit("info", e.stderr.strip())
                raise exceptions.LandscapeConfigFailed(
                    stdout=e.stdout.strip(), stderr=e.stderr.strip()
                )
            return False
        return True

    def _perform_disable(self, progress: api.ProgressWrapper) -> bool:
        cmd = ["landscape-config", "--disable"]
        progress.progress(
            messages.EXECUTING_COMMAND.format(command=" ".join(cmd))
        )
        try:
            system.subp(cmd)
        except exceptions.ProcessExecutionError as e:
            LOG.error(e)
            progress.emit("info", str(e).strip())

        progress.emit("info", messages.LANDSCAPE_CONFIG_REMAINS)

        return True

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        if (
            self.are_required_packages_installed()
            and system.is_systemd_unit_active("landscape-client")
        ):
            return (ApplicationStatus.ENABLED, None)
        else:
            return (
                ApplicationStatus.DISABLED,
                messages.LANDSCAPE_SERVICE_NOT_ACTIVE,
            )

    def enabled_warning_status(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        # This check wrongly gives warning when non-root
        # This will become obsolete soon: #2864
        if util.we_are_currently_root():
            try:
                system.subp(
                    ["landscape-config", "--is-registered", "--silent"]
                )
            except exceptions.ProcessExecutionError:
                return (
                    True,
                    messages.LANDSCAPE_NOT_REGISTERED,
                )

        return False, None

    def process_contract_deltas(
        self,
        orig_access: Dict[str, Any],
        deltas: Dict[str, Any],
        allow_enable: bool = False,
    ) -> bool:
        # overriding allow_enable to always be False for this entitlement
        # effectively prevents enableByDefault from ever happening
        return super().process_contract_deltas(
            orig_access, deltas, allow_enable=False
        )
