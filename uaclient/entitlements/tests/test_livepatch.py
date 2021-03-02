"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
import io
import logging
import mock
from functools import partial
from types import MappingProxyType

try:
    from typing import Any, Dict, List  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


import pytest

from uaclient import apt
from uaclient import exceptions
from uaclient.entitlements.livepatch import (
    LivepatchEntitlement,
    process_config_directives,
)
from uaclient.entitlements.tests.conftest import machine_token
from uaclient import status
from uaclient.status import ApplicationStatus, ContractStatus
from uaclient.util import ProcessExecutionError

PLATFORM_INFO_SUPPORTED = MappingProxyType(
    {
        "arch": "x86_64",
        "kernel": "4.4.0-00-generic",
        "series": "xenial",
        "version": "16.04 LTS (Xenial Xerus)",
    }
)

M_PATH = "uaclient.entitlements.livepatch."  # mock path
M_LIVEPATCH_STATUS = M_PATH + "LivepatchEntitlement.application_status"
DISABLED_APP_STATUS = (status.ApplicationStatus.DISABLED, "")

M_BASE_PATH = "uaclient.entitlements.base.UAEntitlement."

DEFAULT_AFFORDANCES = {
    "architectures": ["x86_64"],
    "minKernelVersion": "4.4",
    "kernelFlavors": ["generic", "lowlatency"],
    "tier": "stable",
}


@pytest.fixture
def livepatch_entitlement_factory(entitlement_factory):
    directives = {"caCerts": "", "remoteServer": "https://alt.livepatch.com"}
    return partial(
        entitlement_factory,
        LivepatchEntitlement,
        affordances=DEFAULT_AFFORDANCES,
        directives=directives,
    )


@pytest.fixture
def entitlement(livepatch_entitlement_factory):
    return livepatch_entitlement_factory()


class TestLivepatchContractStatus:
    def test_contract_status_entitled(self, entitlement):
        """The contract_status returns ENTITLED when entitled is True."""
        assert ContractStatus.ENTITLED == entitlement.contract_status()

    def test_contract_status_unentitled(self, livepatch_entitlement_factory):
        """The contract_status returns NONE when entitled is False."""
        entitlement = livepatch_entitlement_factory(entitled=False)
        assert ContractStatus.UNENTITLED == entitlement.contract_status()


class TestLivepatchUserFacingStatus:
    @mock.patch(
        "uaclient.entitlements.livepatch.util.is_container", return_value=False
    )
    def test_user_facing_status_inapplicable_on_inapplicable_status(
        self, _m_is_container, livepatch_entitlement_factory
    ):
        """The user-facing details INAPPLICABLE applicability_status"""
        affordances = copy.deepcopy(DEFAULT_AFFORDANCES)
        affordances["series"] = ["bionic"]

        entitlement = livepatch_entitlement_factory(affordances=affordances)

        with mock.patch("uaclient.util.get_platform_info") as m_platform_info:
            m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
            uf_status, details = entitlement.user_facing_status()
        assert uf_status == status.UserFacingStatus.INAPPLICABLE
        expected_details = (
            "Livepatch is not available for Ubuntu 16.04 LTS"
            " (Xenial Xerus)."
        )
        assert expected_details == details

    def test_user_facing_status_unavailable_on_unentitled(self, entitlement):
        """Status UNAVAILABLE on absent entitlement contract status."""
        no_entitlements = machine_token(LivepatchEntitlement.name)
        # Delete livepatch entitlement info
        no_entitlements["machineTokenInfo"]["contractInfo"][
            "resourceEntitlements"
        ].pop()
        entitlement.cfg.write_cache("machine-token", no_entitlements)

        with mock.patch("uaclient.util.get_platform_info") as m_platform_info:
            m_platform_info.return_value = PLATFORM_INFO_SUPPORTED
            uf_status, details = entitlement.user_facing_status()
        assert uf_status == status.UserFacingStatus.UNAVAILABLE
        assert "Livepatch is not entitled" == details


class TestLivepatchProcessConfigDirectives:
    @pytest.mark.parametrize(
        "directive_key,livepatch_param_tmpl",
        (("remoteServer", "remote-server={}"), ("caCerts", "ca-certs={}")),
    )
    def test_call_livepatch_config_command(
        self, directive_key, livepatch_param_tmpl
    ):
        """Livepatch config directives are passed to livepatch config."""
        directive_value = "{}-value".format(directive_key)
        cfg = {"entitlement": {"directives": {directive_key: directive_value}}}
        with mock.patch("uaclient.util.subp") as m_subp:
            process_config_directives(cfg)
        expected_subp = mock.call(
            [
                "/snap/bin/canonical-livepatch",
                "config",
                livepatch_param_tmpl.format(directive_value),
            ],
            capture=True,
        )
        assert [expected_subp] == m_subp.call_args_list

    def test_handle_multiple_directives(self):
        """Handle multiple Livepatch directives using livepatch config."""
        cfg = {
            "entitlement": {
                "directives": {
                    "remoteServer": "value1",
                    "caCerts": "value2",
                    "ignored": "ignoredvalue",
                }
            }
        }
        with mock.patch("uaclient.util.subp") as m_subp:
            process_config_directives(cfg)
        expected_calls = [
            mock.call(
                ["/snap/bin/canonical-livepatch", "config", "ca-certs=value2"],
                capture=True,
            ),
            mock.call(
                [
                    "/snap/bin/canonical-livepatch",
                    "config",
                    "remote-server=value1",
                ],
                capture=True,
            ),
        ]
        assert expected_calls == m_subp.call_args_list

    @pytest.mark.parametrize("directives", ({}, {"otherkey": "othervalue"}))
    def test_ignores_other_or_absent(self, directives):
        """Ignore empty or unexpected directives and do not call livepatch."""
        cfg = {"entitlement": {"directives": directives}}
        with mock.patch("uaclient.util.subp") as m_subp:
            process_config_directives(cfg)
        assert 0 == m_subp.call_count


@mock.patch(M_LIVEPATCH_STATUS, return_value=DISABLED_APP_STATUS)
@mock.patch(
    "uaclient.entitlements.livepatch.util.is_container", return_value=False
)
class TestLivepatchEntitlementCanEnable:
    @pytest.mark.parametrize(
        "supported_kernel_ver",
        ("4.4.0-00-generic", "5.0.0-00-generic", "4.19.0-00-generic"),
    )
    def test_can_enable_true_on_entitlement_inactive(
        self,
        _m_is_container,
        _m_livepatch_status,
        supported_kernel_ver,
        capsys,
        entitlement,
    ):
        """When entitlement is INACTIVE, can_enable returns True."""
        supported_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        supported_kernel["kernel"] = supported_kernel_ver
        with mock.patch("uaclient.util.get_platform_info") as m_platform:
            with mock.patch("uaclient.util.is_container") as m_container:
                m_platform.return_value = supported_kernel
                m_container.return_value = False
                assert entitlement.can_enable()
        assert ("", "") == capsys.readouterr()
        assert [mock.call()] == m_container.call_args_list

    def test_can_enable_false_on_unsupported_kernel_min_version(
        self, _m_is_container, _m_livepatch_status, capsys, entitlement
    ):
        """"False when on a kernel less or equal to minKernelVersion."""
        unsupported_min_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_min_kernel["kernel"] = "4.2.9-00-generic"
        with mock.patch("uaclient.util.get_platform_info") as m_platform:
            m_platform.return_value = unsupported_min_kernel
            entitlement = LivepatchEntitlement(entitlement.cfg)
            assert not entitlement.can_enable()
        msg = (
            "Livepatch is not available for kernel 4.2.9-00-generic.\n"
            "Minimum kernel version required: 4.4.\n"
        )
        assert (msg, "") == capsys.readouterr()

    def test_can_enable_false_on_unsupported_kernel_flavor(
        self, _m_is_container, _m_livepatch_status, capsys, entitlement
    ):
        """"When on an unsupported kernel, can_enable returns False."""
        unsupported_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_kernel["kernel"] = "4.4.0-140-notgeneric"
        with mock.patch("uaclient.util.get_platform_info") as m_platform:
            m_platform.return_value = unsupported_kernel
            entitlement = LivepatchEntitlement(entitlement.cfg)
            assert not entitlement.can_enable()
        msg = (
            "Livepatch is not available for kernel 4.4.0-140-notgeneric.\n"
            "Supported flavors are: generic, lowlatency.\n"
        )
        assert (msg, "") == capsys.readouterr()

    @pytest.mark.parametrize(
        "kernel_version,meets_min_version",
        (
            ("3.5.0-00-generic", False),
            ("4.3.0-00-generic", False),
            ("4.4.0-00-generic", True),
            ("4.10.0-00-generic", True),
            ("5.0.0-00-generic", True),
        ),
    )
    def test_can_enable_false_on_unsupported_min_kernel_version(
        self,
        _m_is_container,
        _m_livepatch_status,
        kernel_version,
        meets_min_version,
        capsys,
        entitlement,
    ):
        """"When on an unsupported kernel version, can_enable returns False."""
        unsupported_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_kernel["kernel"] = kernel_version
        with mock.patch("uaclient.util.get_platform_info") as m_platform:
            m_platform.return_value = unsupported_kernel
            entitlement = LivepatchEntitlement(entitlement.cfg)
            if meets_min_version:
                assert entitlement.can_enable()
            else:
                assert not entitlement.can_enable()
        if meets_min_version:
            msg = ""
        else:
            msg = (
                "Livepatch is not available for kernel {}.\n"
                "Minimum kernel version required: 4.4.\n".format(
                    kernel_version
                )
            )
        assert (msg, "") == capsys.readouterr()

    def test_can_enable_false_on_unsupported_architecture(
        self, _m_is_container, _m_livepatch_status, capsys, entitlement
    ):
        """"When on an unsupported architecture, can_enable returns False."""
        unsupported_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_kernel["arch"] = "ppc64le"
        with mock.patch("uaclient.util.get_platform_info") as m_platform:
            m_platform.return_value = unsupported_kernel
            assert not entitlement.can_enable()
        msg = (
            "Livepatch is not available for platform ppc64le.\n"
            "Supported platforms are: x86_64.\n"
        )
        assert (msg, "") == capsys.readouterr()

    def test_can_enable_false_on_containers(
        self, m_is_container, _m_livepatch_status, capsys, entitlement
    ):
        """When is_container is True, can_enable returns False."""
        unsupported_min_kernel = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        unsupported_min_kernel["kernel"] = "4.2.9-00-generic"
        with mock.patch("uaclient.util.get_platform_info") as m_platform:
            m_platform.return_value = unsupported_min_kernel
            m_is_container.return_value = True
            entitlement = LivepatchEntitlement(entitlement.cfg)
            assert not entitlement.can_enable()
        msg = "Cannot install Livepatch on a container.\n"
        assert (msg, "") == capsys.readouterr()


class TestLivepatchProcessContractDeltas:
    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    def test_true_on_parent_process_deltas(
        self, m_setup_livepatch_config, entitlement
    ):
        """When parent's process_contract_deltas returns True do no setup."""
        assert entitlement.process_contract_deltas({}, {}, False)
        assert [] == m_setup_livepatch_config.call_args_list

    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.applicability_status")
    def test_true_on_inactive_livepatch_service(
        self,
        m_applicability_status,
        m_application_status,
        m_setup_livepatch_config,
        entitlement,
    ):
        """When livepatch is INACTIVE return True and do no setup."""
        m_applicability_status.return_value = (
            status.ApplicabilityStatus.APPLICABLE,
            "",
        )
        m_application_status.return_value = (
            status.ApplicationStatus.DISABLED,
            "",
        )
        deltas = {"entitlement": {"directives": {"caCerts": "new"}}}
        assert entitlement.process_contract_deltas({}, deltas, False)
        assert [] == m_setup_livepatch_config.call_args_list

    @pytest.mark.parametrize(
        "directives,process_directives,process_token",
        (
            ({"caCerts": "new"}, True, False),
            ({"remoteServer": "new"}, True, False),
            ({"unhandledKey": "new"}, False, False),
        ),
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    def test_setup_performed_when_active_and_supported_deltas(
        self,
        m_application_status,
        m_setup_livepatch_config,
        entitlement,
        directives,
        process_directives,
        process_token,
    ):
        """Run setup when livepatch ACTIVE and deltas are supported keys."""
        application_status = status.ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        deltas = {"entitlement": {"directives": directives}}
        assert entitlement.process_contract_deltas({}, deltas, False)
        if any([process_directives, process_token]):
            setup_calls = [
                mock.call(
                    process_directives=process_directives,
                    process_token=process_token,
                )
            ]
        else:
            setup_calls = []
        assert setup_calls == m_setup_livepatch_config.call_args_list

    @pytest.mark.parametrize(
        "deltas,process_directives,process_token",
        (
            ({"entitlement": {"something": 1}}, False, False),
            ({"resourceToken": "new"}, False, True),
        ),
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.setup_livepatch_config")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    def test_livepatch_disable_and_setup_performed_when_resource_token_changes(
        self,
        m_application_status,
        m_setup_livepatch_config,
        entitlement,
        deltas,
        process_directives,
        process_token,
    ):
        """Run livepatch calls setup when resourceToken changes."""
        application_status = status.ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        entitlement.process_contract_deltas({}, deltas, False)
        if any([process_directives, process_token]):
            setup_calls = [
                mock.call(
                    process_directives=process_directives,
                    process_token=process_token,
                )
            ]
        else:
            setup_calls = []
        assert setup_calls == m_setup_livepatch_config.call_args_list


class TestLivepatchEntitlementEnable:

    mocks_apt_update = [
        mock.call(["apt-get", "update"], status.MESSAGE_APT_UPDATE_FAILED)
    ]
    mocks_snapd_install = [
        mock.call(
            ["apt-get", "install", "--assume-yes", "snapd"],
            capture=True,
            retry_sleeps=apt.APT_RETRIES,
        )
    ]
    mocks_snap_wait_seed = [
        mock.call(
            ["/usr/bin/snap", "wait", "system", "seed.loaded"], capture=True
        )
    ]
    mocks_livepatch_install = [
        mock.call(
            ["/usr/bin/snap", "install", "canonical-livepatch"],
            capture=True,
            retry_sleeps=[0.5, 1, 5],
        )
    ]
    mocks_install = (
        mocks_snapd_install + mocks_snap_wait_seed + mocks_livepatch_install
    )
    mocks_config = [
        mock.call(
            [
                "/snap/bin/canonical-livepatch",
                "config",
                "remote-server=https://alt.livepatch.com",
            ],
            capture=True,
        ),
        mock.call(["/snap/bin/canonical-livepatch", "disable"]),
        mock.call(
            ["/snap/bin/canonical-livepatch", "enable", "livepatch-token"],
            capture=True,
        ),
    ]

    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=False)
    def test_enable_false_when_can_enable_false(
        self, m_can_enable, caplog_text, capsys, entitlement
    ):
        """When can_enable returns False enable returns False."""
        assert not entitlement.enable()
        assert "" == caplog_text()
        assert ("", "") == capsys.readouterr()  # No additional prints
        assert [mock.call(silent=mock.ANY)] == m_can_enable.call_args_list

    @pytest.mark.parametrize("silent_if_inapplicable", (True, False, None))
    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=False)
    def test_enable_passes_silent_if_inapplicable_through(
        self, m_can_enable, caplog_text, entitlement, silent_if_inapplicable
    ):
        """When can_enable returns False enable returns False."""
        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs["silent_if_inapplicable"] = silent_if_inapplicable
        entitlement.enable(**kwargs)

        expected_call = mock.call(silent=bool(silent_if_inapplicable))
        assert [expected_call] == m_can_enable.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("apt_update_success", (True, False))
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.run_apt_command")
    @mock.patch("uaclient.util.which", return_value=False)
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=True)
    def test_enable_installs_snapd_and_livepatch_snap_when_absent(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        m_run_apt,
        m_subp,
        _m_get_platform_info,
        capsys,
        caplog_text,
        entitlement,
        apt_update_success,
    ):
        """Install snapd and canonical-livepatch snap when not on system."""
        application_status = status.ApplicationStatus.ENABLED
        m_app_status.return_value = application_status, "enabled"

        def fake_run_apt(cmd, message):
            if apt_update_success:
                return
            raise exceptions.UserFacingError("Apt go BOOM")

        m_run_apt.side_effect = fake_run_apt

        assert entitlement.enable()
        assert self.mocks_install + self.mocks_config in m_subp.call_args_list
        assert self.mocks_apt_update == m_run_apt.call_args_list
        msg = (
            "Installing snapd\n"
            "Updating package lists\n"
            "Installing canonical-livepatch snap\n"
            "Canonical livepatch enabled.\n"
        )
        assert (msg, "") == capsys.readouterr()
        expected_log = (
            "DEBUG    Trying to install snapd."
            " Ignoring apt-get update failure: Apt go BOOM"
        )
        if apt_update_success:
            assert expected_log not in caplog_text()
        else:
            assert expected_log in caplog_text()
        expected_calls = [
            mock.call("/snap/bin/canonical-livepatch"),
            mock.call("/usr/bin/snap"),
        ]
        assert expected_calls == m_which.call_args_list

    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.subp", return_value=("snapd", ""))
    @mock.patch(
        "uaclient.util.which", side_effect=lambda cmd: cmd == "/usr/bin/snap"
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=True)
    def test_enable_installs_only_livepatch_snap_when_absent_but_snapd_present(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        m_subp,
        _m_get_platform_info,
        capsys,
        entitlement,
    ):
        """Install canonical-livepatch snap when not present on the system."""
        application_status = status.ApplicationStatus.ENABLED
        m_app_status.return_value = application_status, "enabled"
        assert entitlement.enable()
        assert (
            self.mocks_snap_wait_seed
            + self.mocks_livepatch_install
            + self.mocks_config
            in m_subp.call_args_list
        )
        msg = (
            "Installing canonical-livepatch snap\n"
            "Canonical livepatch enabled.\n"
        )
        assert (msg, "") == capsys.readouterr()
        expected_calls = [
            mock.call("/snap/bin/canonical-livepatch"),
            mock.call("/usr/bin/snap"),
        ]
        assert expected_calls == m_which.call_args_list

    @mock.patch("uaclient.util.subp")
    @mock.patch(
        "uaclient.util.which", side_effect=lambda cmd: cmd == "/usr/bin/snap"
    )
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=True)
    def test_enable_bails_if_snap_cmd_exists_but_snapd_pkg_not_installed(
        self, m_can_enable, m_app_status, m_which, m_subp, capsys, entitlement
    ):
        """Install canonical-livepatch snap when not present on the system."""
        m_app_status.return_value = status.ApplicationStatus.ENABLED, "enabled"
        with mock.patch(
            M_PATH + "apt.get_installed_packages", return_value=[]
        ):
            with pytest.raises(exceptions.UserFacingError) as excinfo:
                entitlement.enable()

        expected_msg = (
            "/usr/bin/snap is present but snapd is not installed;"
            " cannot enable {}".format(entitlement.title)
        )
        assert expected_msg == excinfo.value.msg

    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.util.which", return_value="/found/livepatch")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=True)
    def test_enable_does_not_install_livepatch_snap_when_present(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        m_subp,
        _m_get_platform_info,
        capsys,
        entitlement,
    ):
        """Do not attempt to install livepatch snap when it is present."""
        application_status = status.ApplicationStatus.ENABLED
        m_app_status.return_value = application_status, "enabled"
        assert entitlement.enable()
        assert self.mocks_config == m_subp.call_args_list
        assert ("Canonical livepatch enabled.\n", "") == capsys.readouterr()

    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.util.which", return_value="/found/livepatch")
    @mock.patch(M_PATH + "LivepatchEntitlement.application_status")
    @mock.patch(M_PATH + "LivepatchEntitlement.can_enable", return_value=True)
    def test_enable_does_not_disable_inactive_livepatch_snap_when_present(
        self,
        m_can_enable,
        m_app_status,
        m_which,
        m_subp,
        _m_get_platform_info,
        capsys,
        entitlement,
    ):
        """Do not attempt to disable livepatch snap when it is inactive."""

        m_app_status.return_value = status.ApplicationStatus.DISABLED, "nope"
        assert entitlement.enable()
        subp_no_livepatch_disable = [
            mock.call(
                [
                    "/snap/bin/canonical-livepatch",
                    "config",
                    "remote-server=https://alt.livepatch.com",
                ],
                capture=True,
            ),
            mock.call(
                ["/snap/bin/canonical-livepatch", "enable", "livepatch-token"],
                capture=True,
            ),
        ]
        assert subp_no_livepatch_disable == m_subp.call_args_list
        assert ("Canonical livepatch enabled.\n", "") == capsys.readouterr()

    @pytest.mark.parametrize(
        "cls_name, cls_title",
        (
            ("FIPSEntitlement", "FIPS"),
            ("FIPSUpdatesEntitlement", "FIPS Updates"),
        ),
    )
    @mock.patch("uaclient.entitlements.repo.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_blocking_service_is_enabled(
        self,
        m_is_container,
        m_handle_message_op,
        cls_name,
        cls_title,
        entitlement,
    ):
        m_handle_message_op.return_value = True

        fake_stdout = io.StringIO()
        with mock.patch(M_LIVEPATCH_STATUS, return_value=DISABLED_APP_STATUS):
            with mock.patch(
                "uaclient.entitlements.fips.{}.application_status".format(
                    cls_name
                )
            ) as m_fips:
                m_fips.return_value = (status.ApplicationStatus.ENABLED, "")
                with contextlib.redirect_stdout(fake_stdout):
                    entitlement.enable()

        expected_msg = "Cannot enable Livepatch when {} is enabled.".format(
            cls_title
        )
        assert expected_msg.strip() == fake_stdout.getvalue().strip()


class TestLivepatchApplicationStatus:
    @pytest.mark.parametrize("which_result", ((True), (False)))
    @pytest.mark.parametrize("subp_raise_exception", ((True), (False)))
    @mock.patch("uaclient.util.which")
    @mock.patch("uaclient.util.subp")
    def test_application_status(
        self, m_subp, m_which, subp_raise_exception, which_result, entitlement
    ):
        m_which.return_value = which_result

        if subp_raise_exception:
            m_subp.side_effect = ProcessExecutionError("error msg")

        status, details = entitlement.application_status()

        if not which_result:
            assert status == ApplicationStatus.DISABLED
            assert "canonical-livepatch snap is not installed." in details
        elif subp_raise_exception:
            assert status == ApplicationStatus.DISABLED
            assert "error msg" in details
        else:
            assert status == ApplicationStatus.ENABLED
            assert "" == details

    @mock.patch("time.sleep")
    @mock.patch("uaclient.util.which", return_value=True)
    def test_status_command_retry_on_application_status(
        self, m_which, m_sleep, entitlement
    ):
        from uaclient import util

        with mock.patch.object(util, "_subp") as m_subp:
            m_subp.side_effect = ProcessExecutionError("error msg")
            status, details = entitlement.application_status()

            assert m_subp.call_count == 3
            assert m_sleep.call_count == 2
            assert status == ApplicationStatus.DISABLED
            assert "error msg" in details
