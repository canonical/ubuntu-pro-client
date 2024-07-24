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
        Field("msg", StringDataValue, doc="Human readable reason"),
        Field("code", StringDataValue, doc="Reason code"),
    ]

    def __init__(self, msg: str, code: str):
        self.msg = msg
        self.code = code


class UnattendedUpgradesStatusResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "systemd_apt_timer_enabled",
            BoolDataValue,
            doc="Indicate if the ``apt-daily.timer`` jobs are enabled",
        ),
        Field(
            "apt_periodic_job_enabled",
            BoolDataValue,
            doc=(
                "Indicate if the ``APT::Periodic::Enabled`` configuration is"
                " turned off"
            ),
        ),
        Field(
            "package_lists_refresh_frequency_days",
            IntDataValue,
            doc=(
                "The value of the ``APT::Periodic::Update-Package-Lists``"
                " configuration"
            ),
        ),
        Field(
            "unattended_upgrades_frequency_days",
            IntDataValue,
            doc=(
                "The value of the ``APT::Periodic::Unattended-Upgrade``"
                " configuration"
            ),
        ),
        Field(
            "unattended_upgrades_allowed_origins",
            data_list(StringDataValue),
            doc=(
                "The value of the ``Unattended-Upgrade::Allowed-Origins``"
                " configuration"
            ),
        ),
        Field(
            "unattended_upgrades_running",
            BoolDataValue,
            doc=(
                "Indicate if the ``unattended-upgrade`` service is correctly"
                " configured and running"
            ),
        ),
        Field(
            "unattended_upgrades_disabled_reason",
            UnattendedUpgradesDisabledReason,
            required=False,
            doc=(
                "Object that explains why ``unattended-upgrades`` is not"
                " running -- if the application is running, the object will be"
                " null"
            ),
        ),
        Field(
            "unattended_upgrades_last_run",
            DatetimeDataValue,
            required=False,
            doc="The last time ``unattended-upgrades`` ran",
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
    """
    This endpoint returns the status around ``unattended-upgrades``. The focus
    of the endpoint is to verify if the application is running and how it is
    configured on the machine.

    .. important::

        For this endpoint, we deliver a unique key under ``meta`` called
        ``raw_config``. This field contains all related ``unattended-upgrades``
        configurations, unparsed. This means that this field will maintain both
        original name and values for those configurations.
    """
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

_doc = {
    "introduced_in": "27.14",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.unattended_upgrades.status.v1 import status

result = status()
""",
    "result_class": UnattendedUpgradesStatusResult,
    "exceptions": [
        (
            UnattendedUpgradesError,
            "Raised if we cannot run a necessary command to show the status of ``unattended-upgrades``",  # noqa: E501
        )
    ],
    "example_cli": "pro api u.unattended_upgrades.status.v1",
    "example_json": """
{
    "apt_periodic_job_enabled": true,
    "package_lists_refresh_frequency_days": 1,
    "systemd_apt_timer_enabled": true,
    "unattended_upgrades_allowed_origins": [
        "${distro_id}:${distro_codename}",
        "${distro_id}:${distro_codename}-security",
        "${distro_id}ESMApps:${distro_codename}-apps-security",
        "${distro_id}ESM:${distro_codename}-infra-security"
    ],
    "unattended_upgrades_disabled_reason": null,
    "unattended_upgrades_frequency_days": 1,
    "unattended_upgrades_last_run": null,
    "unattended_upgrades_running": true
}
""",
    "extra": """
- Possible attributes in JSON ``meta`` field:

  .. code-block:: json

     {
         "meta": {
             "environment_vars": [],
             "raw_config": {
                 "APT::Periodic::Enable": "1",
                 "APT::Periodic::Unattended-Upgrade": "1",
                 "APT::Periodic::Update-Package-Lists": "1",
                 "Unattended-Upgrade::Allowed-Origins": [
                     "${distro_id}:${distro_codename}",
                     "${distro_id}:${distro_codename}-security",
                     "${distro_id}ESMApps:${distro_codename}-apps-security",
                     "${distro_id}ESM:${distro_codename}-infra-security"
                 ]
             }
         }
     }
""",
    "extra_indent": 2,
}
