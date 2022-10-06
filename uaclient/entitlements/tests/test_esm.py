import contextlib
import os.path

import mock
import pytest

from uaclient import apt, exceptions
from uaclient.entitlements.esm import ESMAppsEntitlement, ESMInfraEntitlement

M_PATH = "uaclient.entitlements.esm.ESMInfraEntitlement."
M_REPOPATH = "uaclient.entitlements.repo."
M_GETPLATFORM = M_REPOPATH + "system.get_platform_info"


@pytest.fixture(params=[ESMAppsEntitlement, ESMInfraEntitlement])
def entitlement(request, entitlement_factory):
    return entitlement_factory(request.param, suites=["xenial"])


class TestESMRepoPinPriority:
    @pytest.mark.parametrize(
        "series, is_lts, repo_pin_priority",
        (
            ("xenial", True, "never"),
            ("bionic", True, "never"),
            ("impish", False, None),
        ),
    )
    @mock.patch("uaclient.system.is_lts")
    @mock.patch("uaclient.entitlements.esm.system.get_platform_info")
    def test_esm_infra_repo_pin_priority_never_on_lts(
        self,
        m_get_platform_info,
        m_is_lts,
        series,
        is_lts,
        repo_pin_priority,
    ):
        """Repository pinning priority for ESMInfra is 'never' when LTS

        A pin priority of 'never' means we advertize those service packages
        without allowing them to be installed until someone attaches
        the machine to Ubuntu Advantage. This is only done for ESM Infra
        when the release is LTS. We won't want/need to
        advertize ESM Infra packages on releases that are not EOL, but
        this is dealt with in the enable/disable flows, and in postinst.
        """
        m_is_lts.return_value = is_lts
        m_get_platform_info.return_value = {"series": series}
        inst = ESMInfraEntitlement({})
        assert repo_pin_priority == inst.repo_pin_priority
        assert [mock.call(series)] == m_is_lts.call_args_list

    @pytest.mark.parametrize(
        "series, is_beta, repo_pin_priority",
        (
            # When esm non-beta pin it
            ("xenial", False, "never"),
            ("bionic", False, "never"),
            ("focal", False, "never"),
            # when ESM beta don't pin
            ("xenial", True, None),
            ("bionic", True, None),
            ("focal", True, None),
        ),
    )
    @mock.patch("uaclient.system.is_lts")
    @mock.patch("uaclient.entitlements.esm.system.get_platform_info")
    @mock.patch("uaclient.entitlements.UAConfig")
    def test_esm_apps_repo_pin_priority_never_on_lts(
        self,
        m_cfg,
        m_get_platform_info,
        m_is_lts,
        series,
        is_beta,
        repo_pin_priority,
        FakeConfig,
    ):
        """Repository pinning priority for ESMApps is 'never' when on LTS.

        A pin priority of 'never' means we advertize those service packages
        without allowing them to be installed until someone attaches
        the machine to Ubuntu Advantage. This is only done for ESM Apps
        when the release is an Ubuntu LTS release. We won't want/need to
        advertize ESM Apps packages on non-LTS releases or if ESM Apps is beta.
        """
        m_is_lts.return_value = True
        m_get_platform_info.return_value = {"series": series}
        cfg = FakeConfig.for_attached_machine()
        m_cfg.return_value = cfg

        inst = ESMAppsEntitlement(cfg)
        with mock.patch.object(ESMAppsEntitlement, "is_beta", is_beta):
            assert repo_pin_priority == inst.repo_pin_priority

        is_lts_calls = []
        if not is_beta:
            is_lts_calls = [mock.call(series)]

        assert is_lts_calls == m_is_lts.call_args_list


class TestESMDisableAptAuthOnly:
    @pytest.mark.parametrize(
        "series, is_active_esm, disable_apt_auth_only",
        (
            ("xenial", True, True),
            ("bionic", False, False),
            ("focal", False, False),
        ),
    )
    @mock.patch("uaclient.system.is_active_esm")
    @mock.patch("uaclient.entitlements.esm.system.get_platform_info")
    def test_esm_infra_disable_apt_auth_only_is_true_when_active_esm(
        self,
        m_get_platform_info,
        m_is_active_esm,
        series,
        is_active_esm,
        disable_apt_auth_only,
    ):
        m_is_active_esm.return_value = is_active_esm
        m_get_platform_info.return_value = {"series": series}
        inst = ESMInfraEntitlement({})
        assert disable_apt_auth_only is inst.disable_apt_auth_only
        assert [mock.call(series)] == m_is_active_esm.call_args_list

    @pytest.mark.parametrize(
        "series, is_lts, is_beta, cfg_allow_beta, disable_apt_auth_only",
        (
            ("xenial", True, True, None, False),  # is_beta disables
            ("xenial", True, False, False, True),  # not beta service succeeds
            ("xenial", True, True, True, True),  # cfg allow_true overrides
            ("bionic", True, True, None, False),
            ("focal", True, True, None, False),
            ("groovy", False, False, True, False),  # not is_lts fails
        ),
    )
    @mock.patch("uaclient.system.is_lts")
    @mock.patch("uaclient.entitlements.esm.system.get_platform_info")
    @mock.patch("uaclient.entitlements.UAConfig")
    def test_esm_apps_disable_apt_auth_only_is_true_on_lts(
        self,
        m_cfg,
        m_get_platform_info,
        m_is_lts,
        series,
        is_lts,
        is_beta,
        cfg_allow_beta,
        disable_apt_auth_only,
        FakeConfig,
    ):
        m_is_lts.return_value = is_lts
        m_get_platform_info.return_value = {"series": series}
        cfg = FakeConfig.for_attached_machine()
        if cfg_allow_beta:
            cfg.override_features({"allow_beta": cfg_allow_beta})
        m_cfg.return_value = cfg

        inst = ESMAppsEntitlement(cfg)
        with mock.patch.object(ESMAppsEntitlement, "is_beta", is_beta):
            assert disable_apt_auth_only is inst.disable_apt_auth_only

        is_lts_calls = []
        if cfg_allow_beta or not is_beta:
            is_lts_calls = [mock.call(series)]

        assert is_lts_calls == m_is_lts.call_args_list


@mock.patch("uaclient.system.is_lts", return_value=True)
@mock.patch("uaclient.util.validate_proxy", side_effect=lambda x, y, z: y)
@mock.patch("uaclient.entitlements.esm.update_apt_and_motd_messages")
@mock.patch("uaclient.apt.setup_apt_proxy")
class TestESMInfraEntitlementEnable:
    @pytest.mark.parametrize(
        "esm_cls", [ESMAppsEntitlement, ESMInfraEntitlement]
    )
    def test_enable_configures_apt_sources_and_auth_files(
        self,
        m_setup_apt_proxy,
        m_update_apt_and_motd_msgs,
        m_validate_proxy,
        _m_is_lts,
        esm_cls,
        entitlement_factory,
    ):
        """When entitled, configure apt repo auth token, pinning and url."""
        entitlement = entitlement_factory(
            esm_cls,
            cfg_extension={
                "ua_config": {  # intentionally using apt_*
                    "apt_http_proxy": "apt_http_proxy_value",
                    "apt_https_proxy": "apt_https_proxy_value",
                }
            },
            suites=["xenial"],
        )
        patched_packages = ["a", "b"]
        original_exists = os.path.exists

        def fake_exists(path):
            prefs_path = "/etc/apt/preferences.d/ubuntu-{}".format(
                entitlement.name
            )
            if path == prefs_path:
                return True
            if path in (apt.APT_METHOD_HTTPS_FILE, apt.CA_CERTIFICATES_FILE):
                return True
            return original_exists(path)

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch("uaclient.apt.add_auth_apt_repo")
            )
            stack.enter_context(mock.patch("uaclient.system.is_active_esm"))
            m_add_pinning = stack.enter_context(
                mock.patch("uaclient.apt.add_ppa_pinning")
            )
            m_subp = stack.enter_context(
                mock.patch("uaclient.system.subp", return_value=("", ""))
            )
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, "can_enable")
            )
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
            )
            stack.enter_context(
                mock.patch(
                    M_REPOPATH + "os.path.exists", side_effect=fake_exists
                )
            )
            m_remove_file = stack.enter_context(
                mock.patch("uaclient.system.remove_file")
            )
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), "packages", m_packages)
            )

            m_can_enable.return_value = (True, None)

            assert (True, None) == entitlement.enable()

        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-{}.list".format(
                    entitlement.name
                ),
                "http://{}".format(entitlement.name.upper()),
                "{}-token".format(entitlement.name),
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]
        install_cmd = mock.call(
            ["apt-get", "install", "--assume-yes"] + patched_packages,
            capture=True,
            retry_sleeps=apt.APT_RETRIES,
            env={},
        )

        subp_calls = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={},
            ),
            install_cmd,
        ]

        assert [mock.call()] == m_can_enable.call_args_list
        assert [
            mock.call(
                http_proxy="apt_http_proxy_value",
                https_proxy="apt_https_proxy_value",
                proxy_scope=apt.AptProxyScope.GLOBAL,
            )
        ] == m_setup_apt_proxy.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert 0 == m_add_pinning.call_count
        assert subp_calls == m_subp.call_args_list
        remove_file_calls = [
            mock.call(
                "/etc/apt/preferences.d/ubuntu-{}".format(entitlement.name)
            )
        ]
        assert remove_file_calls == m_remove_file.call_args_list
        assert [
            mock.call(entitlement.cfg)
        ] == m_update_apt_and_motd_msgs.call_args_list

    def test_enable_cleans_up_apt_sources_and_auth_files_on_error(
        self,
        _m_setup_apt_proxy,
        _m_update_apt_and_motd_msg,
        m_validate_proxy,
        _m_is_lts,
        entitlement,
        caplog_text,
    ):
        """When setup_apt_config fails, cleanup any apt artifacts."""
        original_exists = os.path.exists

        def fake_exists(path):
            prefs_path = "/etc/apt/preferences.d/ubuntu-{}".format(
                entitlement.name
            )
            if path == prefs_path:
                return True
            if path in (apt.APT_METHOD_HTTPS_FILE, apt.CA_CERTIFICATES_FILE):
                return True
            return original_exists(path)

        def fake_subp(cmd, capture=None, retry_sleeps=None, env={}):
            if cmd == ["apt-get", "update"]:
                raise exceptions.ProcessExecutionError(
                    "Failure", stderr="Could not get lock /var/lib/dpkg/lock"
                )
            return "", ""

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch("uaclient.apt.add_auth_apt_repo")
            )
            m_add_pinning = stack.enter_context(
                mock.patch("uaclient.apt.add_ppa_pinning")
            )
            stack.enter_context(mock.patch("uaclient.system.is_active_esm"))
            m_subp = stack.enter_context(
                mock.patch("uaclient.system.subp", side_effect=fake_subp)
            )
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, "can_enable")
            )
            m_remove_apt_config = stack.enter_context(
                mock.patch.object(entitlement, "remove_apt_config")
            )
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
            )
            stack.enter_context(
                mock.patch(
                    M_REPOPATH + "os.path.exists", side_effect=fake_exists
                )
            )
            m_remove_file = stack.enter_context(
                mock.patch("uaclient.system.remove_file")
            )

            m_can_enable.return_value = (True, None)

            with pytest.raises(exceptions.UserFacingError) as excinfo:
                entitlement.enable()

        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-{}.list".format(
                    entitlement.name
                ),
                "http://{}".format(entitlement.name.upper()),
                "{}-token".format(entitlement.name),
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]
        subp_calls = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={},
            )
        ]

        error_msg = "APT update failed. Another process is running APT."
        assert error_msg == excinfo.value.msg
        assert [mock.call()] == m_can_enable.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert 0 == m_add_pinning.call_count
        assert subp_calls == m_subp.call_args_list
        # Enable esm-infra/apps xenial removes apt preferences pin 'never' file
        remove_file_calls = [
            mock.call(
                "/etc/apt/preferences.d/ubuntu-{}".format(entitlement.name)
            )
        ]
        assert remove_file_calls == m_remove_file.call_args_list
        assert [
            mock.call(run_apt_update=False)
        ] == m_remove_apt_config.call_args_list


@mock.patch("uaclient.entitlements.esm.update_apt_and_motd_messages")
class TestESMEntitlementDisable:
    @pytest.mark.parametrize("silent", [False, True])
    @mock.patch("uaclient.system.get_platform_info")
    @mock.patch(M_PATH + "can_disable", return_value=(False, None))
    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
        self,
        m_can_disable,
        m_platform_info,
        _m_update_apt_and_motd_msgs,
        silent,
    ):
        """When can_disable is false disable returns false and noops."""
        entitlement = ESMInfraEntitlement({})

        with mock.patch("uaclient.apt.remove_auth_apt_repo") as m_remove_apt:
            ret, fail = entitlement.disable(silent)
            assert ret is False
            assert fail is None
        assert [mock.call()] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count

    @mock.patch(
        "uaclient.system.get_platform_info", return_value={"series": "xenial"}
    )
    def test_disable_on_can_disable_true_removes_apt_config(
        self, _m_platform_info, m_update_apt_and_motd_msgs, entitlement
    ):
        """When can_disable, disable removes apt configuration"""

        with mock.patch.object(
            entitlement, "can_disable", return_value=(True, None)
        ):
            with mock.patch.object(
                entitlement, "remove_apt_config"
            ) as m_remove_apt_config:
                assert entitlement.disable(True)
        assert [mock.call(silent=True)] == m_remove_apt_config.call_args_list
        assert [
            mock.call(entitlement.cfg)
        ] == m_update_apt_and_motd_msgs.call_args_list
