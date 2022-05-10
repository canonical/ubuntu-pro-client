"""
Update messaging text for use in MOTD and APT custom Ubuntu Advantage messages.

Messaging files will be emitted to /var/lib/ubuntu-advantage/message-* which
will be sourced by apt-hook/hook.cc and various /etc/update-motd.d/ hooks to
present updated text about Ubuntu Advantage service and token state.
"""

import enum
import logging
import os
from os.path import exists
from typing import List, Tuple

from uaclient import config, defaults, entitlements, util
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.messages import (
    ANNOUNCE_ESM_TMPL,
    CONTRACT_EXPIRED_APT_NO_PKGS_TMPL,
    CONTRACT_EXPIRED_APT_PKGS_TMPL,
    CONTRACT_EXPIRED_GRACE_PERIOD_TMPL,
    CONTRACT_EXPIRED_MOTD_PKGS_TMPL,
    CONTRACT_EXPIRED_SOON_TMPL,
    DISABLED_APT_PKGS_TMPL,
    DISABLED_MOTD_NO_PKGS_TMPL,
    UBUNTU_NO_WARRANTY,
)


@enum.unique
class ContractExpiryStatus(enum.Enum):
    NONE = 0
    ACTIVE = 1
    ACTIVE_EXPIRED_SOON = 2
    EXPIRED_GRACE_PERIOD = 3
    EXPIRED = 4


# Type of message file used for external messaging (APT and MOTD)
@enum.unique
class ExternalMessage(enum.Enum):
    MOTD_APPS_NO_PKGS = "motd-no-packages-apps.tmpl"
    MOTD_INFRA_NO_PKGS = "motd-no-packages-infra.tmpl"
    MOTD_APPS_PKGS = "motd-packages-apps.tmpl"
    MOTD_INFRA_PKGS = "motd-packages-infra.tmpl"
    APT_PRE_INVOKE_APPS_NO_PKGS = "apt-pre-invoke-no-packages-apps.tmpl"
    APT_PRE_INVOKE_INFRA_NO_PKGS = "apt-pre-invoke-no-packages-infra.tmpl"
    APT_PRE_INVOKE_APPS_PKGS = "apt-pre-invoke-packages-apps.tmpl"
    APT_PRE_INVOKE_INFRA_PKGS = "apt-pre-invoke-packages-infra.tmpl"
    APT_PRE_INVOKE_SERVICE_STATUS = "apt-pre-invoke-esm-service-status"
    MOTD_ESM_SERVICE_STATUS = "motd-esm-service-status"
    ESM_ANNOUNCE = "motd-esm-announce"
    UBUNTU_NO_WARRANTY = "ubuntu-no-warranty"


UPDATE_NOTIFIER_MOTD_SCRIPT = (
    "/usr/lib/update-notifier/update-motd-updates-available"
)


def get_contract_expiry_status(
    cfg: config.UAConfig,
) -> Tuple[ContractExpiryStatus, int]:
    """Return a tuple [ContractExpiryStatus, num_days]"""
    if not cfg.is_attached:
        return ContractExpiryStatus.NONE, 0

    grace_period = defaults.CONTRACT_EXPIRY_GRACE_PERIOD_DAYS
    pending_expiry = defaults.CONTRACT_EXPIRY_PENDING_DAYS
    remaining_days = cfg.contract_remaining_days
    if 0 <= remaining_days <= pending_expiry:
        return ContractExpiryStatus.ACTIVE_EXPIRED_SOON, remaining_days
    elif -grace_period <= remaining_days < 0:
        return ContractExpiryStatus.EXPIRED_GRACE_PERIOD, remaining_days
    elif remaining_days < -grace_period:
        return ContractExpiryStatus.EXPIRED, remaining_days
    return ContractExpiryStatus.ACTIVE, remaining_days


def _write_template_or_remove(msg: str, tmpl_file: str):
    """Write a template to tmpl_file.

    When msg is empty, remove both tmpl_file and the generated msg.
    """
    if msg:
        util.write_file(tmpl_file, msg)
    else:
        util.remove_file(tmpl_file)
        if tmpl_file.endswith(".tmpl"):
            util.remove_file(tmpl_file.replace(".tmpl", ""))


def _remove_msg_templates(msg_dir: str, msg_template_names: List[str]):
    # Purge all template out output messages for this service
    for name in msg_template_names:
        _write_template_or_remove("", os.path.join(msg_dir, name))


def _write_esm_service_msg_templates(
    cfg: config.UAConfig,
    ent: entitlements.base.UAEntitlement,
    expiry_status: ContractExpiryStatus,
    remaining_days: int,
    pkgs_file: str,
    no_pkgs_file: str,
    motd_pkgs_file: str,
    motd_no_pkgs_file: str,
):
    """Write any related template content for an ESM service.

    If no content is applicable for the current service state, remove
    all service-related template files.

    :param cfg: UAConfig instance for this environment.
    :param ent: entitlements.base.UAEntitlement,
    :param expiry_status: Current ContractExpiryStatus enum for attached VM.
    :param remaining_days: Int remaining days on contrat, negative when
        expired.
    :param *_file: template file names to write.
    """
    pkgs_msg = no_pkgs_msg = motd_pkgs_msg = motd_no_pkgs_msg = ""
    tmpl_prefix = ent.name.upper().replace("-", "_")
    tmpl_pkg_count_var = "{{{}_PKG_COUNT}}".format(tmpl_prefix)
    tmpl_pkg_names_var = "{{{}_PACKAGES}}".format(tmpl_prefix)

    platform_info = util.get_platform_info()
    is_active_esm = util.is_active_esm(platform_info["series"])
    if is_active_esm and ent.name == "esm-infra":
        release = platform_info["release"]
        ua_esm_url = defaults.EOL_UA_URL_TMPL.format(
            hyphenatedrelease=release.replace(".", "-")
        )
        eol_release = "for Ubuntu {release} ".format(release=release)
    else:
        eol_release = ""
        ua_esm_url = defaults.BASE_ESM_URL
    if ent.application_status()[0] == ApplicationStatus.ENABLED:
        if expiry_status == ContractExpiryStatus.ACTIVE_EXPIRED_SOON:
            pkgs_msg = CONTRACT_EXPIRED_SOON_TMPL.format(
                title=ent.title,
                remaining_days=remaining_days,
                url=defaults.BASE_UA_URL,
            )
            # Same cautionary message when contract is about to expire
            motd_pkgs_msg = motd_no_pkgs_msg = no_pkgs_msg = pkgs_msg
        elif expiry_status == ContractExpiryStatus.EXPIRED_GRACE_PERIOD:
            grace_period_remaining = (
                defaults.CONTRACT_EXPIRY_GRACE_PERIOD_DAYS + remaining_days
            )
            pkgs_msg = CONTRACT_EXPIRED_GRACE_PERIOD_TMPL.format(
                title=ent.title,
                expired_date=cfg.contract_expiry_datetime.strftime("%d %b %Y"),
                remaining_days=grace_period_remaining,
                url=defaults.BASE_UA_URL,
            )
            # Same cautionary message when in grace period
            motd_pkgs_msg = motd_no_pkgs_msg = no_pkgs_msg = pkgs_msg
        elif expiry_status == ContractExpiryStatus.EXPIRED:
            pkgs_msg = CONTRACT_EXPIRED_APT_PKGS_TMPL.format(
                pkg_num=tmpl_pkg_count_var,
                pkg_names=tmpl_pkg_names_var,
                title=ent.title,
                name=ent.name,
                url=defaults.BASE_UA_URL,
            )
            no_pkgs_msg = CONTRACT_EXPIRED_APT_NO_PKGS_TMPL.format(
                title=ent.title, url=defaults.BASE_UA_URL
            )
            motd_no_pkgs_msg = no_pkgs_msg
            motd_pkgs_msg = CONTRACT_EXPIRED_MOTD_PKGS_TMPL.format(
                title=ent.title,
                pkg_num=tmpl_pkg_count_var,
                url=defaults.BASE_UA_URL,
            )
    elif expiry_status != ContractExpiryStatus.EXPIRED:  # Service not enabled
        pkgs_msg = DISABLED_APT_PKGS_TMPL.format(
            title=ent.title,
            pkg_num=tmpl_pkg_count_var,
            pkg_names=tmpl_pkg_names_var,
            eol_release=eol_release,
            url=ua_esm_url,
        )
        no_pkgs_msg = DISABLED_MOTD_NO_PKGS_TMPL.format(
            title=ent.title, url=ua_esm_url
        )

    msg_dir = os.path.join(cfg.data_dir, "messages")
    _write_template_or_remove(no_pkgs_msg, os.path.join(msg_dir, no_pkgs_file))
    _write_template_or_remove(pkgs_msg, os.path.join(msg_dir, pkgs_file))
    _write_template_or_remove(
        motd_no_pkgs_msg, os.path.join(msg_dir, motd_no_pkgs_file)
    )
    _write_template_or_remove(
        motd_pkgs_msg, os.path.join(msg_dir, motd_pkgs_file)
    )


def write_apt_and_motd_templates(cfg: config.UAConfig, series: str) -> None:
    """Write messaging templates about available esm packages.

    :param cfg: UAConfig instance for this environment.
    :param series: string of Ubuntu release series: 'xenial'.
    """
    apps_no_pkg_file = ExternalMessage.APT_PRE_INVOKE_APPS_NO_PKGS.value
    apps_pkg_file = ExternalMessage.APT_PRE_INVOKE_APPS_PKGS.value
    infra_no_pkg_file = ExternalMessage.APT_PRE_INVOKE_INFRA_NO_PKGS.value
    infra_pkg_file = ExternalMessage.APT_PRE_INVOKE_INFRA_PKGS.value
    motd_apps_no_pkg_file = ExternalMessage.MOTD_APPS_NO_PKGS.value
    motd_apps_pkg_file = ExternalMessage.MOTD_APPS_PKGS.value
    motd_infra_no_pkg_file = ExternalMessage.MOTD_INFRA_NO_PKGS.value
    motd_infra_pkg_file = ExternalMessage.MOTD_INFRA_PKGS.value
    no_warranty_file = ExternalMessage.UBUNTU_NO_WARRANTY.value
    msg_dir = os.path.join(cfg.data_dir, "messages")

    apps_cls = entitlements.entitlement_factory(cfg=cfg, name="esm-apps")
    apps_inst = apps_cls(cfg)
    config_allow_beta = util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.allow_beta"
    )
    apps_valid = bool(config_allow_beta or not apps_cls.is_beta)
    infra_cls = entitlements.entitlement_factory(cfg=cfg, name="esm-infra")
    infra_inst = infra_cls(cfg)

    expiry_status, remaining_days = get_contract_expiry_status(cfg)

    enabled_status = ApplicationStatus.ENABLED
    msg_esm_apps = False
    msg_esm_infra = False
    if util.is_active_esm(series):
        no_warranty_msg = ""
        if expiry_status in (
            ContractExpiryStatus.EXPIRED,
            ContractExpiryStatus.NONE,
        ):
            no_warranty_msg = UBUNTU_NO_WARRANTY
        if infra_inst.application_status()[0] != enabled_status:
            msg_esm_infra = True
            no_warranty_msg = UBUNTU_NO_WARRANTY
        elif remaining_days <= defaults.CONTRACT_EXPIRY_PENDING_DAYS:
            msg_esm_infra = True
        _write_template_or_remove(
            no_warranty_msg, os.path.join(msg_dir, no_warranty_file)
        )
    if not msg_esm_infra:
        # write_apt_and_motd_templates is only called if util.is_lts(series)
        msg_esm_apps = apps_valid

    if msg_esm_infra:
        _write_esm_service_msg_templates(
            cfg,
            infra_inst,
            expiry_status,
            remaining_days,
            infra_pkg_file,
            infra_no_pkg_file,
            motd_infra_pkg_file,
            motd_infra_no_pkg_file,
        )
    else:
        _remove_msg_templates(
            msg_dir=os.path.join(cfg.data_dir, "messages"),
            msg_template_names=[
                infra_pkg_file,
                infra_no_pkg_file,
                motd_infra_pkg_file,
                motd_infra_no_pkg_file,
            ],
        )

    if msg_esm_apps:
        _write_esm_service_msg_templates(
            cfg,
            apps_inst,
            expiry_status,
            remaining_days,
            apps_pkg_file,
            apps_no_pkg_file,
            motd_apps_pkg_file,
            motd_apps_no_pkg_file,
        )
    else:
        _remove_msg_templates(
            msg_dir=os.path.join(cfg.data_dir, "messages"),
            msg_template_names=[
                apps_pkg_file,
                apps_no_pkg_file,
                motd_apps_pkg_file,
                motd_apps_no_pkg_file,
            ],
        )


def write_esm_announcement_message(cfg: config.UAConfig, series: str) -> None:
    """Write human-readable messages if ESM is offered on this LTS release.

    Do not write ESM announcements if esm-apps is enabled or beta.

    :param cfg: UAConfig instance for this environment.
    :param series: string of Ubuntu release series: 'xenial'.
    """
    apps_cls = entitlements.entitlement_factory(cfg=cfg, name="esm-apps")
    apps_inst = apps_cls(cfg)
    enabled_status = ApplicationStatus.ENABLED
    apps_not_enabled = apps_inst.application_status()[0] != enabled_status
    config_allow_beta = util.is_config_value_true(
        config=cfg.cfg, path_to_value="features.allow_beta"
    )
    apps_not_beta = bool(config_allow_beta or not apps_cls.is_beta)

    msg_dir = os.path.join(cfg.data_dir, "messages")
    esm_news_file = os.path.join(msg_dir, ExternalMessage.ESM_ANNOUNCE.value)
    platform_info = util.get_platform_info()
    is_active_esm = util.is_active_esm(platform_info["series"])
    if is_active_esm:
        ua_esm_url = defaults.EOL_UA_URL_TMPL.format(
            hyphenatedrelease=platform_info["release"].replace(".", "-")
        )
    else:
        ua_esm_url = defaults.BASE_ESM_URL
    if apps_not_beta and apps_not_enabled:
        util.write_file(
            esm_news_file, "\n" + ANNOUNCE_ESM_TMPL.format(url=ua_esm_url)
        )
    else:
        util.remove_file(esm_news_file)


def update_apt_and_motd_messages(cfg: config.UAConfig) -> bool:
    """Emit templates and human-readable status messages in msg_dir.

    These structured messages will be sourced by both /etc/update.motd.d
    and APT UA-configured hooks. APT hook content will orginate from
    apt-hook/hook.cc

    Call esm-apt-hook process-templates to render final human-readable
    messages.

    :param cfg: UAConfig instance for this environment.
    """
    logging.debug("Updating UA messages for APT and MOTD.")
    msg_dir = os.path.join(cfg.data_dir, "messages")
    if not os.path.exists(msg_dir):
        os.makedirs(msg_dir)

    series = util.get_platform_info()["series"]
    if not util.is_lts(series):
        # ESM is only on LTS releases. Remove all messages and templates.
        for msg_enum in ExternalMessage:
            msg_path = os.path.join(msg_dir, msg_enum.value)
            util.remove_file(msg_path)
            if msg_path.endswith(".tmpl"):
                util.remove_file(msg_path.replace(".tmpl", ""))
        return True

    # Announce ESM availabilty on active ESM LTS releases
    write_esm_announcement_message(cfg, series)
    write_apt_and_motd_templates(cfg, series)
    # Now that we've setup/cleanedup templates render them with apt-hook
    util.subp(["/usr/lib/ubuntu-advantage/apt-esm-hook", "process-templates"])
    return True


def refresh_motd():
    # If update-notifier is present, we might as well update
    # the package updates count related to MOTD
    if exists(UPDATE_NOTIFIER_MOTD_SCRIPT):
        # If this command fails, we shouldn't break the entire command,
        # since this command should already be triggered by
        # update-notifier apt hooks
        try:
            util.subp([UPDATE_NOTIFIER_MOTD_SCRIPT, "--force"])
        except Exception as exc:
            logging.exception(exc)

    util.subp(["sudo", "systemctl", "restart", "motd-news.service"])
