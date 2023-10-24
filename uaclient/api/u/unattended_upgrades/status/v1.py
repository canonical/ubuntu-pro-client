import datetime
import os
from typing import Dict, List, Optional, Tuple, Union

from uaclient import apt, exceptions, messages, system
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.exceptions import UnattendedUpgradesError
from uaclient.apt import get_apt_config_keys, get_apt_config_values
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    DatetimeDataValue,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)

UNATTENDED_UPGRADES_CONFIG_KEYS = [
    "APT::Periodic::Enable",
    "APT::Periodic::Update-Package-Lists",
    "APT::Periodic::Unattended-Upgrade",
    "Unattended-Upgrade::Allowed-Origins",
]

UNATTENDED_UPGRADES_STAMP_PATH = "/var/lib/apt/periodic/upgrade-stamp"


class UnattendedUpgradesDisabledReason(DataObject):
    fields = [
        Field("msg", StringDataValue),
        Field("code", StringDataValue),
    ]

    def __init__(self, msg: str, code: str):
        self.msg = msg
        self.code = code


class UnattendedUpgradesStatusResult(DataObject, AdditionalInfo):
    fields = [
        Field("systemd_apt_timer_enabled", BoolDataValue),
        Field("apt_periodic_job_enabled", BoolDataValue),
        Field("package_lists_refresh_frequency_days", IntDataValue),
        Field("unattended_upgrades_frequency_days", IntDataValue),
        Field(
            "unattended_upgrades_allowed_origins",
            data_list(StringDataValue),
        ),
        Field("unattended_upgrades_running", BoolDataValue),
        Field(
            "unattended_upgrades_disabled_reason",
            UnattendedUpgradesDisabledReason,
            required=False,
        ),
        Field(
            "unattended_upgrades_last_run", DatetimeDataValue, required=False
        ),
    ]

    def __init__(
        self,
        *,
        systemd_apt_timer_enabled: bool,
        apt_periodic_job_enabled: bool,
        package_lists_refresh_frequency_days: int,
        unattended_upgrades_frequency_days: int,
        unattended_upgrades_allowed_origins: List[str],
        unattended_upgrades_running: bool,
        unattended_upgrades_disabled_reason: Optional[
            UnattendedUpgradesDisabledReason
        ],
        unattended_upgrades_last_run: Optional[datetime.datetime]
    ):
        self.systemd_apt_timer_enabled = systemd_apt_timer_enabled
        self.apt_periodic_job_enabled = apt_periodic_job_enabled
        self.package_lists_refresh_frequency_days = (
            package_lists_refresh_frequency_days
        )
        self.unattended_upgrades_frequency_days = (
            unattended_upgrades_frequency_days
        )
        self.unattended_upgrades_allowed_origins = (
            unattended_upgrades_allowed_origins
        )
        self.unattended_upgrades_running = unattended_upgrades_running
        self.unattended_upgrades_disabled_reason = (
            unattended_upgrades_disabled_reason
        )
        self.unattended_upgrades_last_run = unattended_upgrades_last_run


def _get_apt_daily_job_status() -> bool:
    try:
        apt_daily_job_enabled = system.is_systemd_unit_active(
            "apt-daily.timer"
        )
        apt_daily_upgrade_job_enabled = system.is_systemd_unit_active(
            "apt-daily-upgrade.timer"
        )
        systemd_apt_timer_enabled = (
            apt_daily_job_enabled and apt_daily_upgrade_job_enabled
        )
    except exceptions.ProcessExecutionError as e:
        raise UnattendedUpgradesError(error_msg=str(e))

    return systemd_apt_timer_enabled


def _is_unattended_upgrades_running(
    systemd_apt_timer_enabled: bool,
    unattended_upgrades_cfg: Dict[str, Union[str, List[str]]],
) -> Tuple[bool, Optional[messages.NamedMessage]]:
    if not systemd_apt_timer_enabled:
        return (False, messages.UNATTENDED_UPGRADES_SYSTEMD_JOB_DISABLED)

    for key, value in unattended_upgrades_cfg.items():
        if not value:
            return (
                False,
                messages.UNATTENDED_UPGRADES_CFG_LIST_VALUE_EMPTY.format(
                    cfg_name=key
                ),
            )
        if isinstance(value, str) and value == "0":
            return (
                False,
                messages.UNATTENDED_UPGRADES_CFG_VALUE_TURNED_OFF.format(
                    cfg_name=key
                ),
            )

    return (True, None)


def _get_unattended_upgrades_last_run() -> Optional[datetime.datetime]:
    try:
        creation_epoch = os.path.getctime(UNATTENDED_UPGRADES_STAMP_PATH)
    except FileNotFoundError:
        return None

    return datetime.datetime.fromtimestamp(creation_epoch)


def status() -> UnattendedUpgradesStatusResult:
    return _status(UAConfig())


def _status(cfg: UAConfig) -> UnattendedUpgradesStatusResult:
    if not apt.is_installed("unattended-upgrades"):
        return UnattendedUpgradesStatusResult(
            systemd_apt_timer_enabled=False,
            apt_periodic_job_enabled=False,
            package_lists_refresh_frequency_days=0,
            unattended_upgrades_frequency_days=0,
            unattended_upgrades_allowed_origins=[],
            unattended_upgrades_disabled_reason=UnattendedUpgradesDisabledReason(  # noqa
                msg=messages.UNATTENDED_UPGRADES_UNINSTALLED.msg,
                code=messages.UNATTENDED_UPGRADES_UNINSTALLED.name,
            ),
            unattended_upgrades_running=False,
            unattended_upgrades_last_run=None,
        )

    systemd_apt_timer_enabled = _get_apt_daily_job_status()
    unattended_upgrades_last_run = _get_unattended_upgrades_last_run()

    unattended_upgrades_cfg = get_apt_config_values(
        set(
            UNATTENDED_UPGRADES_CONFIG_KEYS
            + get_apt_config_keys("Unattended-Upgrade")
        )
    )

    # If that key is not present on the APT Config, we assume it
    # that the config is "enabled", as by default this configuration
    # will not be present in APT
    unattended_upgrades_cfg["APT::Periodic::Enable"] = (
        unattended_upgrades_cfg["APT::Periodic::Enable"] or "1"
    )

    (
        unattended_upgrades_running,
        disabled_reason,
    ) = _is_unattended_upgrades_running(
        systemd_apt_timer_enabled, unattended_upgrades_cfg
    )

    if disabled_reason:
        unattended_upgrades_disabled_reason = UnattendedUpgradesDisabledReason(
            msg=disabled_reason.msg,
            code=disabled_reason.name,
        )
    else:
        unattended_upgrades_disabled_reason = None

    unattended_upgrades_result = UnattendedUpgradesStatusResult(
        systemd_apt_timer_enabled=systemd_apt_timer_enabled,
        apt_periodic_job_enabled=str(
            unattended_upgrades_cfg.get("APT::Periodic::Enable", "")
        )
        == "1",
        package_lists_refresh_frequency_days=int(
            unattended_upgrades_cfg.get(  # type: ignore
                "APT::Periodic::Update-Package-Lists", 0
            )
        ),
        unattended_upgrades_frequency_days=int(
            unattended_upgrades_cfg.get(  # type: ignore
                "APT::Periodic::Unattended-Upgrade", 0
            )
        ),
        unattended_upgrades_allowed_origins=list(
            unattended_upgrades_cfg.get("Unattended-Upgrade::Allowed-Origins")
            or []
        ),
        unattended_upgrades_disabled_reason=(
            unattended_upgrades_disabled_reason
        ),
        unattended_upgrades_running=unattended_upgrades_running,
        unattended_upgrades_last_run=unattended_upgrades_last_run,
    )
    unattended_upgrades_result.meta = {"raw_config": unattended_upgrades_cfg}

    return unattended_upgrades_result


endpoint = APIEndpoint(
    version="v1",
    name="UnattendedUpgradesStatus",
    fn=_status,
    options_cls=None,
)
