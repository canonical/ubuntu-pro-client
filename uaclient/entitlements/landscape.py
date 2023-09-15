import logging
import os
from typing import Any, Dict, Optional, Tuple

from uaclient import apt, event_logger, exceptions, messages, system, util
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))
event = event_logger.get_event_logger()

LANDSCAPE_CLIENT_PACKAGE_NAME = "landscape-client"
LANDSCAPE_CLIENT_CONFIG_PATH = "/etc/landscape/client.conf"
LANDSCAPE_CLIENT_CONFIG_PATH_DISABLE_BACKUP = (
    "/etc/landscape/client.conf.pro-disable-backup"
)


class LandscapeEntitlement(UAEntitlement):
    name = "landscape"
    title = messages.LANDSCAPE_TITLE
    description = messages.LANDSCAPE_DESCRIPTION
    help_doc_url = messages.urls.LANDSCAPE_HOME_PAGE
    help_text = messages.LANDSCAPE_HELP_TEXT

    def _perform_enable(self, silent: bool = False) -> bool:
        cmd = ["landscape-config"] + self.extra_args
        if self.assume_yes and "--silent" not in cmd:
            cmd += ["--silent"]

        LOG.debug("Executing: %r", cmd)
        event.info(
            util.redact_sensitive_logs(
                messages.EXECUTING_COMMAND.format(command=" ".join(cmd))
            )
        )
        try:
            system.subp(cmd, pipe_stdouterr=self.assume_yes)
        except exceptions.ProcessExecutionError as e:
            if self.assume_yes:
                err_msg = messages.LANDSCAPE_CONFIG_FAILED
                event.error(
                    err_msg.msg,
                    err_msg.name,
                    service=self.name,
                    additional_info={
                        "stdout": e.stdout.strip(),
                        "stderr": e.stderr.strip(),
                    },
                )
                event.info(e.stderr.strip())
                event.info(messages.ENABLE_FAILED.format(title=self.title))
            return False

        if self.assume_yes:
            # when silencing landscape-config, include a success message
            # otherwise, let landscape-config say what happened
            event.info(messages.ENABLED_TMPL.format(title=self.title))
        return True

    def _perform_disable(self, silent: bool = False) -> bool:
        cmd = ["landscape-config", "--disable"]
        event.info(messages.EXECUTING_COMMAND.format(command=" ".join(cmd)))
        try:
            system.subp(cmd)
        except exceptions.ProcessExecutionError as e:
            LOG.error(e)
            event.info(str(e).strip())
            event.warning(str(e), self.name)

        LOG.debug(
            "Backing up %s as %s",
            LANDSCAPE_CLIENT_CONFIG_PATH,
            LANDSCAPE_CLIENT_CONFIG_PATH_DISABLE_BACKUP,
        )
        event.info(
            messages.BACKING_UP_FILE.format(
                original=LANDSCAPE_CLIENT_CONFIG_PATH,
                backup=LANDSCAPE_CLIENT_CONFIG_PATH_DISABLE_BACKUP,
            )
        )
        try:
            os.rename(
                LANDSCAPE_CLIENT_CONFIG_PATH,
                LANDSCAPE_CLIENT_CONFIG_PATH_DISABLE_BACKUP,
            )
        except FileNotFoundError as e:
            LOG.error(e)
            event.info(str(e))
            event.warning(str(e), self.name)

        return True

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        if apt.is_installed(LANDSCAPE_CLIENT_PACKAGE_NAME):
            return (ApplicationStatus.ENABLED, None)
        else:
            return (
                ApplicationStatus.DISABLED,
                messages.LANDSCAPE_CLIENT_NOT_INSTALLED,
            )

    def enabled_warning_status(
        self,
    ) -> Tuple[bool, Optional[messages.NamedMessage]]:
        if not os.path.exists(LANDSCAPE_CLIENT_CONFIG_PATH):
            return (
                True,
                messages.LANDSCAPE_NOT_CONFIGURED,
            )

        # This check wrongly gives warning when non-root
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

        if not system.is_systemd_unit_active("landscape-client"):
            return (
                True,
                messages.LANDSCAPE_SERVICE_NOT_ACTIVE,
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
