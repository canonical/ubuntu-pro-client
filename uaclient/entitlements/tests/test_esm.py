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


@mock.patch("uaclient.system.is_lts", return_value=True)
@mock.patch("uaclient.util.validate_proxy", side_effect=lambda x, y, z: y)
@mock.patch("uaclient.entitlements.esm.update_apt_and_motd_messages")
@mock.patch("uaclient.entitlements.esm.disable_local_esm_repo")
@mock.patch("uaclient.apt.setup_apt_proxy")
class TestESMEntitlementEnable:
    @pytest.mark.parametrize(
        "esm_cls", [ESMAppsEntitlement, ESMInfraEntitlement]
    )
    @pytest.mark.parametrize("apt_error", (True, False))
    def test_enable_configures_apt_sources_and_auth_files(
        self,
        m_setup_apt_proxy,
        m_disable_local_repo,
        m_update_apt_and_motd_msgs,
        m_validate_proxy,
        _m_is_lts,
        esm_cls,
        apt_error,
        entitlement_factory,
        caplog_text,
    ):
        """When entitled, configure apt repo auth token, pinning and url.
        When setup_apt_config fails, cleanup any apt artifacts.
        """
        entitlement = entitlement_factory(
            esm_cls,
            cfg_extension={
                "ua_config": {  # intentionally using apt_*
                    "apt_http_proxy": "apt_http_proxy_value",
                    "apt_https_proxy": "apt_https_proxy_value",
                }
            },
            suites=["xenial"],
            allow_beta=True,
        )
        patched_packages = ["a", "b"]

        original_exists = os.path.exists

        def fake_exists(path):
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
            if apt_error:
                m_subp = stack.enter_context(
                    mock.patch("uaclient.system.subp", side_effect=fake_subp)
                )
            else:
                m_subp = stack.enter_context(
                    mock.patch("uaclient.system.subp", return_value=("", ""))
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
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), "packages", m_packages)
            )

            m_can_enable.return_value = (True, None)

            if apt_error:
                with pytest.raises(exceptions.UserFacingError) as excinfo:
                    entitlement.enable()
            else:
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
        ]
        if not apt_error:
            subp_calls.append(install_cmd)

        update_msgs_calls = [] if apt_error else [mock.call(entitlement.cfg)]

        assert [mock.call()] == m_can_enable.call_args_list
        assert [
            mock.call(
                http_proxy="apt_http_proxy_value",
                https_proxy="apt_https_proxy_value",
                proxy_scope=apt.AptProxyScope.GLOBAL,
            )
        ] == m_setup_apt_proxy.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert subp_calls == m_subp.call_args_list
        assert update_msgs_calls == m_update_apt_and_motd_msgs.call_args_list

        if apt_error:
            error_msg = "APT update failed. Another process is running APT."
            assert error_msg == excinfo.value.msg
            assert [
                mock.call(run_apt_update=False)
            ] == m_remove_apt_config.call_args_list
            assert [] == m_disable_local_repo.call_args_list
        else:
            assert [] == m_remove_apt_config.call_args_list
            assert [
                mock.call(entitlement.__class__)
            ] == m_disable_local_repo.call_args_list


@mock.patch("uaclient.entitlements.esm.update_apt_and_motd_messages")
@mock.patch("uaclient.entitlements.esm.setup_local_esm_repo")
@mock.patch(
    "uaclient.system.get_platform_info", return_value={"series": "xenial"}
)
class TestESMEntitlementDisable:
    @pytest.mark.parametrize("silent", [False, True])
    @mock.patch(M_PATH + "can_disable", return_value=(False, None))
    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
        self,
        m_can_disable,
        _m_platform_info,
        m_setup_repo,
        m_update_apt_and_motd_msgs,
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
        assert 0 == m_update_apt_and_motd_msgs.call_count
        assert 0 == m_setup_repo.call_count

    def test_disable_removes_config_and_updates_cache_and_messages(
        self,
        _m_platform_info,
        m_setup_repo,
        m_update_apt_and_motd_msgs,
        entitlement,
    ):
        """When can_disable, disable removes apt configuration.
        Also updates messaging and sets up a local repository.
        """

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
        assert [
            mock.call(entitlement.__class__)
        ] == m_setup_repo.call_args_list
