"""Tests related to ubuntupro.entitlement.base module."""

import mock
import pytest

from ubuntupro import apt, messages, system
from ubuntupro.entitlements.cis import CIS_DOCS_URL, CISEntitlement

M_REPOPATH = "ubuntupro.entitlements.repo."


@pytest.fixture
def entitlement(entitlement_factory):
    return entitlement_factory(
        CISEntitlement,
        allow_beta=True,
        called_name="cis",
        additional_packages=["pkg1"],
    )


class TestCISEntitlementEnable:
    @mock.patch("ubuntupro.apt.get_apt_cache_policy")
    @mock.patch("ubuntupro.apt.setup_apt_proxy")
    @mock.patch("ubuntupro.system.should_reboot")
    @mock.patch("ubuntupro.system.subp")
    @mock.patch("ubuntupro.system.get_kernel_info")
    @mock.patch("ubuntupro.system.get_release_info")
    def test_enable_configures_apt_sources_and_auth_files(
        self,
        m_release_info,
        m_kernel_info,
        m_subp,
        m_should_reboot,
        m_setup_apt_proxy,
        m_apt_policy,
        capsys,
        event,
        entitlement,
    ):
        """When entitled, configure apt repo auth token, pinning and url."""

        def fake_platform(key=None):
            info = {"series": "xenial", "kernel": "4.15.0-00-generic"}
            if key:
                return info[key]
            return info

        m_release_info.return_value = system.ReleaseInfo(
            distribution="", release="", series="xenial", pretty_version=""
        )
        m_kernel_info.return_value = system.KernelInfo(
            uname_machine_arch="x86_64",
            uname_release="4.15.0-00-generic",
            proc_version_signature_version=None,
            build_date=None,
            major=None,
            minor=None,
            patch=None,
            abi=None,
            flavor=None,
        )
        m_subp.return_value = ("fakeout", "")
        m_apt_policy.return_value = "fakeout"
        m_should_reboot.return_value = False

        with mock.patch(M_REPOPATH + "exists", mock.Mock(return_value=True)):
            with mock.patch("ubuntupro.apt.add_auth_apt_repo") as m_add_apt:
                with mock.patch("ubuntupro.apt.add_ppa_pinning") as m_add_pin:
                    assert entitlement.enable()

        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-cis.list",
                "http://CIS/ubuntu",
                "{}-token".format(entitlement.name),
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]

        m_apt_policy_cmds = [
            mock.call(
                error_msg=messages.APT_POLICY_FAILED.msg,
            ),
        ]

        subp_apt_cmds = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                override_env_vars=None,
            ),
            mock.call(
                [
                    "apt-get",
                    "install",
                    "--assume-yes",
                    "--allow-downgrades",
                    '-o Dpkg::Options::="--force-confdef"',
                    '-o Dpkg::Options::="--force-confold"',
                ]
                + entitlement.packages,
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
            ),
        ]

        assert add_apt_calls == m_add_apt.call_args_list
        # No apt pinning for cis
        assert [] == m_add_pin.call_args_list
        assert 1 == m_setup_apt_proxy.call_count
        assert subp_apt_cmds == m_subp.call_args_list
        assert 1 == m_apt_policy.call_count
        assert m_apt_policy_cmds == m_apt_policy.call_args_list
        assert 1 == m_should_reboot.call_count
        expected_stdout = (
            "Updating package lists\n"
            "Installing CIS Audit packages\n"
            "CIS Audit enabled\n"
            "Visit {} to learn how to use CIS\n".format(CIS_DOCS_URL)
        )
        assert (expected_stdout, "") == capsys.readouterr()
