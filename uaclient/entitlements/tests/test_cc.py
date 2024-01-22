"""Tests related to uaclient.entitlement.base module."""

import itertools
import os.path

import mock
import pytest

from uaclient import apt, messages, system
from uaclient.entitlements.cc import CC_README, CommonCriteriaEntitlement
from uaclient.entitlements.tests.conftest import machine_token

M_REPOPATH = "uaclient.entitlements.repo."

CC_MACHINE_TOKEN = machine_token(
    entitlement_type="cc-eal",
    obligations={"enableByDefault": False},
    entitled=True,
    directives={
        "aptURL": "http://CC",
        "aptKey": "APTKEY",
        "suites": ["xenial"],
        "additionalPackages": ["ubuntu-commoncriteria"],
    },
    affordances={
        "architectures": ["x86_64", "ppc64le", "s390x"],
        "series": ["xenial"],
    },
)


class TestCommonCriteriaEntitlementEnable:
    # Paramterize True/False for apt_transport_https and ca_certificates
    @pytest.mark.parametrize(
        "apt_transport_https,ca_certificates",
        itertools.product([False, True], repeat=2),
    )
    @mock.patch("uaclient.system.get_kernel_info")
    @mock.patch("uaclient.apt.update_sources_list")
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch("uaclient.system.should_reboot")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.apt.get_apt_cache_policy")
    @mock.patch("uaclient.system.get_dpkg_arch")
    @mock.patch("uaclient.system.get_release_info")
    @mock.patch("uaclient.contract.apply_contract_overrides")
    def test_enable_configures_apt_sources_and_auth_files(
        self,
        _m_contract_overrides,
        m_release_info,
        m_dpkg_arch,
        m_apt_cache_policy,
        m_subp,
        m_should_reboot,
        m_setup_apt_proxy,
        m_update_sources_list,
        m_get_kernel_info,
        capsys,
        event,
        apt_transport_https,
        ca_certificates,
        tmpdir,
        FakeConfig,
    ):
        """When entitled, configure apt repo auth token, pinning and url."""
        m_subp.return_value = ("fakeout", "")
        m_apt_cache_policy.return_value = "fakeout"
        m_should_reboot.return_value = False
        m_release_info.return_value = system.ReleaseInfo(
            distribution="", release="", series="xenial", pretty_version=""
        )
        m_dpkg_arch.return_value = "s390x"
        original_exists = os.path.exists

        def exists(path):
            if path == apt.APT_METHOD_HTTPS_FILE:
                return not apt_transport_https
            elif path == apt.CA_CERTIFICATES_FILE:
                return not ca_certificates
            elif not path.startswith(tmpdir.strpath):
                raise Exception(
                    "os.path.exists call outside of tmpdir: {}".format(path)
                )
            return original_exists(path)

        cfg = FakeConfig().for_attached_machine(
            machine_token=CC_MACHINE_TOKEN,
        )
        entitlement = CommonCriteriaEntitlement(cfg, allow_beta=True)

        with mock.patch("uaclient.apt.add_auth_apt_repo") as m_add_apt:
            with mock.patch("uaclient.apt.add_ppa_pinning") as m_add_pin:
                with mock.patch(M_REPOPATH + "exists", side_effect=exists):
                    assert (True, None) == entitlement.enable()

        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-cc-eal.list",
                "http://CC/ubuntu",
                "{}-token".format(entitlement.name),
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]

        apt_cache_policy_cmds = [
            mock.call(
                error_msg=messages.APT_POLICY_FAILED,
            )
        ]

        prerequisite_pkgs = []
        if apt_transport_https:
            prerequisite_pkgs.append("apt-transport-https")
        if ca_certificates:
            prerequisite_pkgs.append("ca-certificates")

        subp_apt_cmds = []
        if prerequisite_pkgs:
            expected_stdout = "Installing {}\n".format(
                ", ".join(prerequisite_pkgs)
            )
            subp_apt_cmds.append(
                mock.call(
                    ["apt-get", "install", "--assume-yes"] + prerequisite_pkgs,
                    capture=True,
                    retry_sleeps=apt.APT_RETRIES,
                    override_env_vars=None,
                )
            )
        else:
            expected_stdout = ""

        subp_apt_cmds.extend(
            [
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
        )

        assert add_apt_calls == m_add_apt.call_args_list
        # No apt pinning for cc
        assert [] == m_add_pin.call_args_list
        assert 1 == m_setup_apt_proxy.call_count
        assert 1 == m_should_reboot.call_count
        assert 1 == m_apt_cache_policy.call_count
        assert apt_cache_policy_cmds == m_apt_cache_policy.call_args_list
        assert subp_apt_cmds == m_subp.call_args_list
        assert 2 == m_update_sources_list.call_count
        expected_stdout += "\n".join(
            [
                "Updating CC EAL2 package lists",
                "(This will download more than 500MB of packages, so may take"
                " some time.)",
                "Updating standard Ubuntu package lists",
                "Installing CC EAL2 packages",
                "CC EAL2 enabled",
                "Please follow instructions in {} to configure EAL2\n".format(
                    CC_README
                ),
            ]
        )
        assert (expected_stdout, "") == capsys.readouterr()
