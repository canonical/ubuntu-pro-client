import mock
import pytest

from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.livepatch import LivepatchPatchStatus, LivepatchStatusStatus
from uaclient.security_status import RebootStatus
from uaclient.system import RebootRequiredPkgs

PATH = "uaclient.api.u.pro.security.status.reboot_required.v1."


class TestRebootStatus:
    @pytest.mark.parametrize(
        (
            "reboot_state,reboot_required_pkgs,livepatch_status,"
            "expected_standard_pkgs,expected_kernel_pkgs,"
            "expected_livepatch_enabled_and_kernel,"
            "expected_livepatch_enabled,expected_livepatch_state,"
            "expected_livepatch_support"
        ),
        (
            (
                RebootStatus.REBOOT_REQUIRED,
                RebootRequiredPkgs(
                    standard_packages=["pkg1"], kernel_packages=["linux-base"]
                ),
                LivepatchStatusStatus(
                    kernel=None,
                    livepatch=LivepatchPatchStatus(
                        state="nothing-to-apply", fixes=None, version=None
                    ),
                    supported="supported",
                ),
                ["pkg1"],
                ["linux-base"],
                True,
                True,
                "nothing-to-apply",
                "supported",
            ),
            (
                RebootStatus.REBOOT_NOT_REQUIRED,
                None,
                None,
                None,
                None,
                False,
                False,
                None,
                None,
            ),
            (
                RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED,
                RebootRequiredPkgs(
                    standard_packages=[], kernel_packages=["linux-base"]
                ),
                LivepatchStatusStatus(
                    kernel=None,
                    livepatch=LivepatchPatchStatus(
                        state="applied", fixes=None, version=None
                    ),
                    supported="supported",
                ),
                [],
                ["linux-base"],
                True,
                True,
                "applied",
                "supported",
            ),
            (
                RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED,
                RebootRequiredPkgs(
                    standard_packages=[], kernel_packages=["linux-base"]
                ),
                LivepatchStatusStatus(
                    kernel=None,
                    livepatch=LivepatchPatchStatus(
                        state="unknown", fixes=None, version=None
                    ),
                    supported="unknown",
                ),
                [],
                ["linux-base"],
                False,
                True,
                "unknown",
                "unknown",
            ),
        ),
    )
    @mock.patch(PATH + "status")
    @mock.patch(PATH + "get_reboot_required_pkgs")
    @mock.patch(PATH + "get_reboot_status")
    def test_reboot_status_api(
        self,
        m_get_reboot_status,
        m_get_reboot_required_pkgs,
        m_livepatch_status,
        reboot_state,
        reboot_required_pkgs,
        livepatch_status,
        expected_standard_pkgs,
        expected_kernel_pkgs,
        expected_livepatch_enabled_and_kernel,
        expected_livepatch_enabled,
        expected_livepatch_state,
        expected_livepatch_support,
    ):
        m_get_reboot_status.return_value = reboot_state
        m_get_reboot_required_pkgs.return_value = reboot_required_pkgs
        m_livepatch_status.return_value = livepatch_status
        result = _reboot_required(mock.MagicMock())
        assert reboot_state.value == result.reboot_required
        assert (
            expected_standard_pkgs
            == result.reboot_required_packages.standard_packages
        )
        assert (
            expected_livepatch_enabled_and_kernel
            == result.livepatch_enabled_and_kernel_patched
        )
        assert expected_livepatch_enabled == result.livepatch_enabled
        assert expected_livepatch_state == result.livepatch_state
        assert expected_livepatch_support == result.livepatch_support
