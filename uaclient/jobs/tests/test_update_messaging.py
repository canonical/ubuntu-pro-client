import datetime
import os

import mock
import pytest

from uaclient import system
from uaclient.defaults import BASE_UA_URL, CONTRACT_EXPIRY_GRACE_PERIOD_DAYS
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.jobs.update_messaging import (
    AWS_PRO_URL,
    AZURE_PRO_URL,
    AZURE_XENIAL_URL,
    GCP_PRO_URL,
    XENIAL_ESM_URL,
    ContractExpiryStatus,
    ExternalMessage,
    _write_esm_service_msg_templates,
    get_contextual_esm_info_url,
    get_contract_expiry_status,
    update_apt_and_motd_messages,
    write_apt_and_motd_templates,
    write_esm_announcement_message,
)
from uaclient.messages import (
    ANNOUNCE_ESM_APPS_TMPL,
    CONTRACT_EXPIRED_APT_GRACE_PERIOD_TMPL,
    CONTRACT_EXPIRED_APT_NO_PKGS_TMPL,
    CONTRACT_EXPIRED_APT_PKGS_TMPL,
    CONTRACT_EXPIRED_APT_SOON_TMPL,
    CONTRACT_EXPIRED_MOTD_GRACE_PERIOD_TMPL,
    CONTRACT_EXPIRED_MOTD_NO_PKGS_TMPL,
    CONTRACT_EXPIRED_MOTD_PKGS_TMPL,
    CONTRACT_EXPIRED_MOTD_SOON_TMPL,
    DISABLED_APT_NO_PKGS_TMPL,
    DISABLED_APT_PKGS_TMPL,
)

M_PATH = "uaclient.jobs.update_messaging."


class TestGetContractExpiryStatus:
    @pytest.mark.parametrize(
        "contract_remaining_days,expected_status",
        (
            (21, ContractExpiryStatus.ACTIVE),
            (20, ContractExpiryStatus.ACTIVE_EXPIRED_SOON),
            (-1, ContractExpiryStatus.EXPIRED_GRACE_PERIOD),
            (-20, ContractExpiryStatus.EXPIRED),
        ),
    )
    def test_contract_expiry_status_based_on_remaining_days(
        self, contract_remaining_days, expected_status, FakeConfig
    ):
        """Return a tuple of ContractExpiryStatus and remaining_days"""
        now = datetime.datetime.utcnow()
        expire_date = now + datetime.timedelta(days=contract_remaining_days)
        cfg = FakeConfig.for_attached_machine()
        m_token = cfg.machine_token
        m_token["machineTokenInfo"]["contractInfo"][
            "effectiveTo"
        ] = expire_date

        assert (
            expected_status,
            contract_remaining_days,
        ) == get_contract_expiry_status(cfg)


class TestGetContextualESMInfoURL:
    @pytest.mark.parametrize(
        "cloud, series, expected",
        (
            (None, "xenial", (XENIAL_ESM_URL, " for 16.04")),
            (None, "bionic", (BASE_UA_URL, "")),
            (None, "focal", (BASE_UA_URL, "")),
            (None, "jammy", (BASE_UA_URL, "")),
            ("aws", "xenial", (XENIAL_ESM_URL, " for 16.04")),
            ("aws", "bionic", (AWS_PRO_URL, " on AWS")),
            ("aws", "focal", (AWS_PRO_URL, " on AWS")),
            ("aws", "jammy", (AWS_PRO_URL, " on AWS")),
            ("azure", "xenial", (AZURE_XENIAL_URL, " for 16.04 on Azure")),
            ("azure", "bionic", (AZURE_PRO_URL, " on Azure")),
            ("azure", "focal", (AZURE_PRO_URL, " on Azure")),
            ("azure", "jammy", (AZURE_PRO_URL, " on Azure")),
            ("gce", "xenial", (XENIAL_ESM_URL, " for 16.04")),
            ("gce", "bionic", (GCP_PRO_URL, " on GCP")),
            ("gce", "focal", (GCP_PRO_URL, " on GCP")),
            ("gce", "jammy", (GCP_PRO_URL, " on GCP")),
            ("somethingelse", "xenial", (XENIAL_ESM_URL, " for 16.04")),
            ("somethingelse", "bionic", (BASE_UA_URL, "")),
            ("somethingelse", "focal", (BASE_UA_URL, "")),
            ("somethingelse", "jammy", (BASE_UA_URL, "")),
        ),
    )
    @mock.patch("uaclient.jobs.update_messaging.system.get_platform_info")
    @mock.patch("uaclient.jobs.update_messaging.identity.get_cloud_type")
    def test_get_contextual_esm_info_url(
        self, m_get_cloud_type, m_get_platform_info, cloud, series, expected
    ):
        m_get_cloud_type.return_value = (cloud, None)
        m_get_platform_info.return_value = {"series": series}
        assert get_contextual_esm_info_url.__wrapped__() == expected


class TestWriteAPTAndMOTDTemplates:
    @pytest.mark.parametrize(
        "series,is_active_esm,contract_days,infra_enabled,"
        "esm_apps_beta,cfg_allow_beta,show_infra,show_apps",
        (
            # Enabled infra, active contract, beta apps: show none
            ("xenial", True, 21, True, True, None, False, False),
            # Not enabled infra, beta apps: show infra msg
            ("xenial", True, -21, False, True, None, True, False),
            # Any *expired contract, infra enabled, beta apps: show infra msg
            ("xenial", True, 20, True, True, None, True, False),
            ("xenial", True, 0, True, True, None, True, False),
            ("xenial", True, -1, True, True, None, True, False),
            ("xenial", True, -21, True, True, None, True, False),
            # Infra enabled, any *expired contract, allow_beta: show infra msg
            ("xenial", True, 20, True, True, True, True, False),
            # Infra enabled, active contract, allow_beta: show apps msg
            ("xenial", True, 21, True, True, True, False, True),
            # Infra enabled, active contract, apps not beta: show apps msg
            ("xenial", True, 21, True, False, None, False, True),
        ),
    )
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "_remove_msg_templates")
    @mock.patch(M_PATH + "_write_esm_service_msg_templates")
    @mock.patch(M_PATH + "system.is_active_esm")
    @mock.patch(M_PATH + "get_contract_expiry_status")
    def test_write_apps_or_infra_services_mutually_exclusive(
        self,
        get_contract_expiry_status,
        util_is_active_esm,
        write_esm_service_templates,
        remove_msg_templates,
        m_entitlement_factory,
        series,
        is_active_esm,
        contract_days,
        infra_enabled,
        esm_apps_beta,
        cfg_allow_beta,
        show_infra,
        show_apps,
        FakeConfig,
    ):
        """Write Infra or Apps when Apps not-beta service.

        Messaging is mutually exclusive, if Infra templates are emitted, don't
        write Apps.
        """
        get_contract_expiry_status.return_value = (
            ContractExpiryStatus.ACTIVE,
            contract_days,
        )
        if infra_enabled:
            infra_status = ApplicationStatus.ENABLED
        else:
            infra_status = ApplicationStatus.DISABLED
        util_is_active_esm.return_value = is_active_esm
        infra_cls = mock.MagicMock()
        infra_obj = infra_cls.return_value
        infra_obj.application_status.return_value = (infra_status, "")
        infra_obj.name = "esm-infra"
        apps_cls = mock.MagicMock()
        apps_cls.is_beta = esm_apps_beta
        apps_obj = apps_cls.return_value
        apps_obj.name = "esm-apps"

        def factory_side_effect(cfg, name):
            if name == "esm-infra":
                return infra_cls
            if name == "esm-apps":
                return apps_cls

        m_entitlement_factory.side_effect = factory_side_effect

        cfg = FakeConfig.for_attached_machine()
        os.makedirs(os.path.join(cfg.data_dir, "messages"))
        if cfg_allow_beta:
            cfg.override_features({"allow_beta": cfg_allow_beta})
        write_calls = []
        remove_calls = []
        if show_infra:
            write_calls.append(
                mock.call(
                    cfg,
                    mock.ANY,
                    ContractExpiryStatus.ACTIVE,
                    contract_days,
                    ExternalMessage.APT_PRE_INVOKE_INFRA_PKGS.value,
                    ExternalMessage.APT_PRE_INVOKE_INFRA_NO_PKGS.value,
                    ExternalMessage.MOTD_INFRA_PKGS.value,
                    ExternalMessage.MOTD_INFRA_NO_PKGS.value,
                )
            )
        else:
            remove_calls.append(
                mock.call(
                    msg_dir=os.path.join(cfg.data_dir, "messages"),
                    msg_template_names=[
                        ExternalMessage.APT_PRE_INVOKE_INFRA_PKGS.value,
                        ExternalMessage.APT_PRE_INVOKE_INFRA_NO_PKGS.value,
                        ExternalMessage.MOTD_INFRA_PKGS.value,
                        ExternalMessage.MOTD_INFRA_NO_PKGS.value,
                    ],
                )
            )
        if show_apps:
            write_calls.append(
                mock.call(
                    cfg,
                    mock.ANY,
                    ContractExpiryStatus.ACTIVE,
                    contract_days,
                    ExternalMessage.APT_PRE_INVOKE_APPS_PKGS.value,
                    ExternalMessage.APT_PRE_INVOKE_APPS_NO_PKGS.value,
                    ExternalMessage.MOTD_APPS_PKGS.value,
                    ExternalMessage.MOTD_APPS_NO_PKGS.value,
                )
            )
        else:
            remove_calls.append(
                mock.call(
                    msg_dir=os.path.join(cfg.data_dir, "messages"),
                    msg_template_names=[
                        ExternalMessage.APT_PRE_INVOKE_APPS_PKGS.value,
                        ExternalMessage.APT_PRE_INVOKE_APPS_NO_PKGS.value,
                        ExternalMessage.MOTD_APPS_PKGS.value,
                        ExternalMessage.MOTD_APPS_NO_PKGS.value,
                    ],
                )
            )
        write_apt_and_motd_templates(cfg, series)
        assert [mock.call(cfg)] == get_contract_expiry_status.call_args_list
        assert remove_calls == remove_msg_templates.call_args_list
        assert write_calls == write_esm_service_templates.call_args_list


class Test_WriteESMServiceAPTMsgTemplates:
    @pytest.mark.parametrize(
        "service_name,contract_expiry,expect_messages,platform_info,"
        "url,context",
        (
            (
                "esm-apps",
                ContractExpiryStatus.ACTIVE,
                True,
                {"series": "xenial", "release": "16.04"},
                XENIAL_ESM_URL,
                " for 16.04",
            ),
            (
                "esm-infra",
                ContractExpiryStatus.ACTIVE,
                True,
                {"series": "xenial", "release": "16.04"},
                XENIAL_ESM_URL,
                " for 16.04",
            ),
            (
                "esm-apps",
                ContractExpiryStatus.ACTIVE,
                True,
                {"series": "xenial", "release": "16.04"},
                XENIAL_ESM_URL,
                " for 16.04",
            ),
            (
                "esm-apps",
                ContractExpiryStatus.EXPIRED,
                False,
                {"series": "xenial", "release": "16.04"},
                XENIAL_ESM_URL,
                " for 16.04",
            ),
        ),
    )
    @mock.patch(M_PATH + "system.get_platform_info")
    @mock.patch(M_PATH + "system.is_active_esm", return_value=True)
    @mock.patch(
        M_PATH + "entitlements.repo.RepoEntitlement.application_status"
    )
    def test_apt_templates_written_for_disabled_services(
        self,
        app_status,
        util_is_active_esm,
        get_platform_info,
        service_name,
        contract_expiry,
        expect_messages,
        platform_info,
        url,
        context,
        FakeConfig,
        tmpdir,
    ):
        """Disabled service messages are omitted if contract expired.

        This represents customer chosen disabling of service on an attached
        machine. So, they've chosen to disable expired services.
        """
        get_contextual_esm_info_url.cache_clear()
        if service_name == "esm-infra":
            pkg_names_var = "{ESM_INFRA_PACKAGES}"
        else:
            pkg_names_var = "{ESM_APPS_PACKAGES}"
        get_platform_info.return_value = platform_info
        m_entitlement_cls = mock.MagicMock()
        m_ent_obj = m_entitlement_cls.return_value
        disabled_status = ApplicationStatus.DISABLED, ""
        m_ent_obj.application_status.return_value = disabled_status
        type(m_ent_obj).name = mock.PropertyMock(return_value=service_name)
        pkgs_file = tmpdir.join("pkgs-msg")
        no_pkgs_file = tmpdir.join("no-pkgs-msg")
        motd_pkgs_file = tmpdir.join("motd-pkgs-msg")
        motd_no_pkgs_file = tmpdir.join("motd-no-pkgs-msg")
        _write_esm_service_msg_templates(
            FakeConfig.for_attached_machine(),
            m_ent_obj,
            contract_expiry,
            21,
            pkgs_file.strpath,
            no_pkgs_file.strpath,
            motd_pkgs_file.strpath,
            motd_no_pkgs_file.strpath,
        )
        if expect_messages:
            assert (
                DISABLED_APT_PKGS_TMPL.format(
                    service=m_ent_obj.name,
                    pkg_names=pkg_names_var,
                    context=context,
                    url=url,
                )
                == pkgs_file.read()
            )
            assert (
                DISABLED_APT_NO_PKGS_TMPL.format(context=context, url=url)
                == no_pkgs_file.read()
            )
        else:
            assert False is os.path.exists(pkgs_file.strpath)
            assert False is os.path.exists(no_pkgs_file.strpath)

    @pytest.mark.parametrize(
        "contract_status, remaining_days, is_active_esm, platform_info",
        (
            (
                ContractExpiryStatus.ACTIVE,
                21,
                True,
                {"series": "xenial", "release": "16.04"},
            ),
            (
                ContractExpiryStatus.ACTIVE_EXPIRED_SOON,
                10,
                True,
                {"series": "xenial", "release": "16.04"},
            ),
            (
                ContractExpiryStatus.EXPIRED_GRACE_PERIOD,
                -5,
                True,
                {"series": "xenial", "release": "16.04"},
            ),
            (
                ContractExpiryStatus.EXPIRED,
                -20,
                True,
                {"series": "xenial", "release": "16.04"},
            ),
            (
                ContractExpiryStatus.EXPIRED,
                -20,
                False,
                {"series": "xenial", "release": "16.04"},
            ),
        ),
    )
    @mock.patch(M_PATH + "system.get_platform_info")
    @mock.patch(M_PATH + "system.is_active_esm")
    @mock.patch(
        M_PATH + "entitlements.repo.RepoEntitlement.application_status"
    )
    def test_apt_templates_written_for_enabled_services_by_contract_status(
        self,
        app_status,
        util_is_active_esm,
        get_platform_info,
        contract_status,
        remaining_days,
        is_active_esm,
        platform_info,
        FakeConfig,
        tmpdir,
    ):
        get_platform_info.return_value = platform_info
        util_is_active_esm.return_value = is_active_esm
        m_entitlement_cls = mock.MagicMock()
        m_ent_obj = m_entitlement_cls.return_value
        disabled_status = ApplicationStatus.ENABLED, ""
        m_ent_obj.application_status.return_value = disabled_status
        type(m_ent_obj).name = mock.PropertyMock(return_value="esm-apps")
        type(m_ent_obj).title = mock.PropertyMock(
            return_value="Ubuntu Pro: ESM Apps"
        )
        pkgs_tmpl = tmpdir.join("pkgs-msg.tmpl")
        no_pkgs_tmpl = tmpdir.join("no-pkgs-msg.tmpl")
        motd_pkgs_tmpl = tmpdir.join("motd-pkgs-msg.tmpl")
        motd_no_pkgs_tmpl = tmpdir.join("motd-no-pkgs-msg.tmpl")
        pkgs_tmpl.write("oldcache")
        no_pkgs_tmpl.write("oldcache")
        motd_pkgs_tmpl.write("oldcache")
        motd_no_pkgs_tmpl.write("oldcache")
        no_pkgs_msg_file = no_pkgs_tmpl.strpath.replace(".tmpl", "")
        pkgs_msg_file = pkgs_tmpl.strpath.replace(".tmpl", "")
        system.write_file(no_pkgs_msg_file, "oldcache")
        system.write_file(pkgs_msg_file, "oldcache")

        now = datetime.datetime.utcnow()
        expire_date = now + datetime.timedelta(days=remaining_days)
        cfg = FakeConfig.for_attached_machine()
        m_token = cfg.machine_token
        m_token["machineTokenInfo"]["contractInfo"][
            "effectiveTo"
        ] = expire_date

        _write_esm_service_msg_templates(
            cfg,
            m_ent_obj,
            contract_status,
            remaining_days,
            pkgs_tmpl.strpath,
            no_pkgs_tmpl.strpath,
            motd_pkgs_tmpl.strpath,
            motd_no_pkgs_tmpl.strpath,
        )
        if contract_status == ContractExpiryStatus.ACTIVE:
            # Old messages removed on ACTIVE status
            assert False is os.path.exists(pkgs_tmpl.strpath)
            assert False is os.path.exists(no_pkgs_tmpl.strpath)
            assert False is os.path.exists(motd_pkgs_tmpl.strpath)
            assert False is os.path.exists(motd_no_pkgs_tmpl.strpath)
            assert False is os.path.exists(pkgs_msg_file)
            assert False is os.path.exists(no_pkgs_msg_file)
        elif contract_status == ContractExpiryStatus.ACTIVE_EXPIRED_SOON:
            pkgs_msg = CONTRACT_EXPIRED_APT_SOON_TMPL.format(
                remaining_days=remaining_days,
            )
            assert pkgs_msg == pkgs_tmpl.read()
            assert pkgs_msg == no_pkgs_tmpl.read()
            motd_pkgs_msg = CONTRACT_EXPIRED_MOTD_SOON_TMPL.format(
                remaining_days=remaining_days,
            )
            assert motd_pkgs_msg == motd_pkgs_tmpl.read()
            assert motd_pkgs_msg == motd_no_pkgs_tmpl.read()
        elif contract_status == ContractExpiryStatus.EXPIRED_GRACE_PERIOD:
            exp_dt = cfg.machine_token_file.contract_expiry_datetime
            exp_dt = exp_dt.strftime("%d %b %Y")
            pkgs_msg = CONTRACT_EXPIRED_APT_GRACE_PERIOD_TMPL.format(
                expired_date=exp_dt,
                remaining_days=remaining_days
                + CONTRACT_EXPIRY_GRACE_PERIOD_DAYS,
            )
            assert pkgs_msg == pkgs_tmpl.read()
            assert pkgs_msg == no_pkgs_tmpl.read()
            motd_pkgs_msg = CONTRACT_EXPIRED_MOTD_GRACE_PERIOD_TMPL.format(
                expired_date=exp_dt,
                remaining_days=remaining_days
                + CONTRACT_EXPIRY_GRACE_PERIOD_DAYS,
            )
            assert motd_pkgs_msg == motd_pkgs_tmpl.read()
            assert motd_pkgs_msg == motd_no_pkgs_tmpl.read()
        elif contract_status == ContractExpiryStatus.EXPIRED:
            pkgs_msg = CONTRACT_EXPIRED_APT_PKGS_TMPL.format(
                service="esm-apps",
                pkg_names="{ESM_APPS_PACKAGES}",
            )
            no_pkgs_msg = CONTRACT_EXPIRED_APT_NO_PKGS_TMPL
            assert pkgs_msg == pkgs_tmpl.read()
            assert no_pkgs_msg == no_pkgs_tmpl.read()
            motd_pkgs_msg = CONTRACT_EXPIRED_MOTD_PKGS_TMPL.format(
                pkg_num="{ESM_APPS_PKG_COUNT}",
                service="esm-apps",
            )
            motd_no_pkgs_msg = CONTRACT_EXPIRED_MOTD_NO_PKGS_TMPL
            assert motd_pkgs_msg == motd_pkgs_tmpl.read()
            assert motd_no_pkgs_msg == motd_no_pkgs_tmpl.read()


class TestWriteESMAnnouncementMessage:
    @pytest.mark.parametrize(
        "series,release,is_active_esm,is_beta,cfg_allow_beta,"
        "apps_enabled,expected",
        (
            # ESMApps.is_beta == True no Announcement
            ("xenial", "16.04", True, True, None, False, None),
            # Once release begins ESM and ESMApps.is_beta is false announce
            (
                "xenial",
                "16.04",
                True,
                False,
                None,
                False,
                "\n" + ANNOUNCE_ESM_APPS_TMPL.format(url=XENIAL_ESM_URL),
            ),
            # allow_beta uaclient.config overrides is_beta and days_until_esm
            (
                "xenial",
                "16.04",
                True,
                True,
                True,
                False,
                "\n" + ANNOUNCE_ESM_APPS_TMPL.format(url=XENIAL_ESM_URL),
            ),
            # when esm-apps already enabled don't show
            ("xenial", "16.04", True, False, True, True, None),
            (
                "bionic",
                "18.04",
                False,
                False,
                None,
                False,
                "\n" + ANNOUNCE_ESM_APPS_TMPL.format(url=BASE_UA_URL),
            ),
            (
                "focal",
                "20.04",
                False,
                False,
                None,
                False,
                "\n" + ANNOUNCE_ESM_APPS_TMPL.format(url=BASE_UA_URL),
            ),
        ),
    )
    @mock.patch(
        M_PATH + "entitlements.repo.RepoEntitlement.application_status"
    )
    @mock.patch(M_PATH + "entitlements.entitlement_factory")
    @mock.patch(M_PATH + "system.is_active_esm")
    @mock.patch(M_PATH + "system.get_platform_info")
    def test_message_based_on_beta_status_and_count_until_active_esm(
        self,
        get_platform_info,
        util_is_active_esm,
        m_entitlement_factory,
        esm_application_status,
        series,
        release,
        is_active_esm,
        is_beta,
        cfg_allow_beta,
        apps_enabled,
        expected,
        FakeConfig,
    ):
        get_contextual_esm_info_url.cache_clear()
        get_platform_info.return_value = {"series": series, "release": release}
        system.is_active_esm.return_value = is_active_esm

        cfg = FakeConfig.for_attached_machine()
        msg_dir = os.path.join(cfg.data_dir, "messages")
        os.makedirs(msg_dir)
        esm_news_path = os.path.join(msg_dir, "motd-esm-announce")

        if cfg_allow_beta:
            cfg.override_features({"allow_beta": cfg_allow_beta})

        m_entitlement_cls = mock.MagicMock()
        m_entitlement_cls.is_beta = is_beta
        m_ent_obj = m_entitlement_cls.return_value
        if apps_enabled:
            status_return = ApplicationStatus.ENABLED, ""
        else:
            status_return = ApplicationStatus.DISABLED, ""
        m_ent_obj.application_status.return_value = status_return

        m_entitlement_factory.return_value = m_entitlement_cls

        write_esm_announcement_message(cfg, series)
        if expected is None:
            assert False is os.path.exists(esm_news_path)
        else:
            assert expected == system.load_file(esm_news_path)


class TestUpdateAPTandMOTDMessages:
    @pytest.mark.parametrize(
        "series,is_lts,esm_active,cfg_allow_beta",
        (
            ("xenial", True, True, True),
            ("bionic", True, False, True),
            ("bionic", True, False, None),
            ("groovy", False, False, None),
        ),
    )
    @mock.patch(M_PATH + "system.is_lts")
    @mock.patch(M_PATH + "system.is_active_esm")
    @mock.patch(M_PATH + "write_apt_and_motd_templates")
    @mock.patch(M_PATH + "write_esm_announcement_message")
    @mock.patch(M_PATH + "system.subp")
    @mock.patch(M_PATH + "system.get_platform_info")
    def test_motd_and_apt_templates_written_separately(
        self,
        get_platform_info,
        subp,
        write_esm_announcement_message,
        write_apt_and_motd_templates,
        is_active_esm,
        util_is_lts,
        series,
        is_lts,
        esm_active,
        cfg_allow_beta,
        FakeConfig,
    ):
        """Update message templates for LTS releases with esm active.

        Assert cleanup of cached template and rendered message files when
        non-LTS release.

        Allow config allow_beta overrides.
        """
        get_platform_info.return_value = {"series": series}
        util_is_lts.return_value = is_lts
        is_active_esm.return_value = esm_active
        cfg = FakeConfig.for_attached_machine()
        if cfg_allow_beta:
            cfg.override_features({"allow_beta": cfg_allow_beta})
        msg_dir = os.path.join(cfg.data_dir, "messages")
        if not is_lts:
            # setup old msg files to assert they are removed
            os.makedirs(msg_dir)
            for msg_enum in ExternalMessage:
                msg_path = os.path.join(msg_dir, msg_enum.value)
                system.write_file(msg_path, "old")
                system.write_file(msg_path.replace(".tmpl", ""), "old")

        update_apt_and_motd_messages(cfg)
        os.path.exists(os.path.join(cfg.data_dir, "messages"))

        if is_lts:
            write_apt_calls = [mock.call(cfg, series)]
            esm_announce_calls = []
            subp_calls = [
                mock.call(
                    [
                        "/usr/lib/ubuntu-advantage/apt-esm-hook",
                    ]
                )
            ]
        else:
            write_apt_calls = esm_announce_calls = []
            subp_calls = []
            # Cached msg templates removed on non-LTS
            for msg_enum in ExternalMessage:
                msg_path = os.path.join(msg_dir, msg_enum.value)
                assert False is os.path.exists(msg_path)
                assert False is os.path.exists(msg_path.replace(".tmpl", ""))
        assert (
            esm_announce_calls == write_esm_announcement_message.call_args_list
        )
        assert write_apt_calls == write_apt_and_motd_templates.call_args_list
        assert subp_calls == subp.call_args_list

    @pytest.mark.parametrize(
        "expiry_status,call_count",
        (
            (ContractExpiryStatus.ACTIVE, 0),
            (ContractExpiryStatus.ACTIVE_EXPIRED_SOON, 1),
            (ContractExpiryStatus.EXPIRED_GRACE_PERIOD, 1),
        ),
    )
    @mock.patch(M_PATH + "update_contract_expiry")
    @mock.patch(M_PATH + "get_contract_expiry_status")
    @mock.patch(M_PATH + "system.is_lts")
    @mock.patch(M_PATH + "system.is_active_esm")
    @mock.patch(M_PATH + "write_apt_and_motd_templates")
    @mock.patch(M_PATH + "write_esm_announcement_message")
    @mock.patch(M_PATH + "system.subp")
    @mock.patch(M_PATH + "system.get_platform_info")
    def test_contract_expiry_motd_and_apt_messages(
        self,
        _get_platform_info,
        _subp,
        _write_esm_announcement_message,
        _write_apt_and_motd_templates,
        _is_active_esm,
        _util_is_lts,
        get_contract_expiry_status,
        update_contract_expiry,
        expiry_status,
        call_count,
        FakeConfig,
    ):
        get_contract_expiry_status.return_value = expiry_status, 0
        cfg = FakeConfig.for_attached_machine()
        update_apt_and_motd_messages(cfg)
        assert update_contract_expiry.call_count == call_count

    @pytest.mark.parametrize(
        "expiry,is_updated",
        (("2040-05-08T19:02:26Z", False), ("2042-05-08T19:02:26Z", True)),
    )
    @mock.patch("uaclient.files.MachineTokenFile.write")
    @mock.patch(M_PATH + "contract.UAContractClient.get_updated_contract_info")
    def test_update_contract_expiry(
        self,
        get_updated_contract_info,
        machine_token_write,
        expiry,
        is_updated,
    ):
        get_updated_contract_info.return_value = {
            "machineTokenInfo": {"contractInfo": {"effectiveTo": expiry}}
        }
        if is_updated:
            1 == machine_token_write.call_count
        else:
            0 == machine_token_write.call_count
