import mock
import pytest

from uaclient import livepatch
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    RebootStatus,
    _get_reboot_status,
    _reboot_required,
)
from uaclient.system import RebootRequiredPkgs

M_PATH = "uaclient.api.u.pro.security.status.reboot_required.v1."


class TestRebootRequired:
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
                livepatch.LivepatchStatusStatus(
                    kernel=None,
                    livepatch=livepatch.LivepatchPatchStatus(
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
                livepatch.LivepatchStatusStatus(
                    kernel=None,
                    livepatch=livepatch.LivepatchPatchStatus(
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
                livepatch.LivepatchStatusStatus(
                    kernel=None,
                    livepatch=livepatch.LivepatchPatchStatus(
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
    @mock.patch("uaclient.livepatch.status")
    @mock.patch(M_PATH + "get_reboot_required_pkgs")
    @mock.patch(M_PATH + "_get_reboot_status")
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


class TestGetRebootStatus:
    @mock.patch(M_PATH + "should_reboot", return_value=False)
    def test_get_reboot_status_no_reboot_needed(self, m_should_reboot):
        assert _get_reboot_status() == RebootStatus.REBOOT_NOT_REQUIRED
        assert 1 == m_should_reboot.call_count

    @mock.patch(M_PATH + "get_reboot_required_pkgs")
    @mock.patch(M_PATH + "should_reboot", return_value=True)
    def test_get_reboot_status_no_reboot_pkgs_file(
        self, m_should_reboot, m_get_reboot_required_pkgs
    ):
        m_get_reboot_required_pkgs.return_value = None
        assert _get_reboot_status() == RebootStatus.REBOOT_REQUIRED
        assert 1 == m_should_reboot.call_count
        assert 1 == m_get_reboot_required_pkgs.call_count

    @mock.patch("uaclient.livepatch.status")
    @mock.patch("uaclient.livepatch.is_livepatch_installed", return_value=True)
    @mock.patch(M_PATH + "get_reboot_required_pkgs")
    @mock.patch(M_PATH + "should_reboot", return_value=True)
    def test_get_reboot_status_livepatch_status_none(
        self,
        m_should_reboot,
        m_get_reboot_required_pkgs,
        _m_is_livepatch_installed,
        m_livepatch_status,
    ):
        m_get_reboot_required_pkgs.return_value = RebootRequiredPkgs(
            standard_packages=[],
            kernel_packages=["linux-base", "linux-image-5.4.0-1074"],
        )
        m_livepatch_status.return_value = None
        assert _get_reboot_status() == RebootStatus.REBOOT_REQUIRED

    @pytest.mark.parametrize(
        "reboot_required_pkgs,expected_state",
        (
            (
                RebootRequiredPkgs(
                    standard_packages=["pkg1", "pkg2"], kernel_packages=[]
                ),
                RebootStatus.REBOOT_REQUIRED,
            ),
            (
                RebootRequiredPkgs(
                    standard_packages=["pkg2"],
                    kernel_packages=["linux-base", "linux-image-5.4.0-1074"],
                ),
                RebootStatus.REBOOT_REQUIRED,
            ),
        ),
    )
    @mock.patch(M_PATH + "get_reboot_required_pkgs")
    @mock.patch(M_PATH + "should_reboot", return_value=True)
    def test_get_reboot_status_reboot_pkgs_file_present(
        self,
        m_should_reboot,
        m_get_reboot_required_pkgs,
        reboot_required_pkgs,
        expected_state,
    ):
        m_get_reboot_required_pkgs.return_value = reboot_required_pkgs
        assert _get_reboot_status() == expected_state
        assert 1 == m_should_reboot.call_count
        assert 1 == m_get_reboot_required_pkgs.call_count

    @pytest.mark.parametrize(
        [
            "livepatch_state",
            "supported_state",
            "expected_state",
            "kernel_name",
        ],
        (
            (
                "applied",
                "supported",
                RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED,
                "4.15.0-187.198-generic",
            ),
            (
                "applied",
                None,
                RebootStatus.REBOOT_REQUIRED,
                "4.15.0-187.198-generic",
            ),
            ("applied", "supported", RebootStatus.REBOOT_REQUIRED, "test"),
            (
                "nothing-to-apply",
                "supported",
                RebootStatus.REBOOT_REQUIRED_LIVEPATCH_APPLIED,
                "4.15.0-187.198-generic",
            ),
            (
                "applying",
                "supported",
                RebootStatus.REBOOT_REQUIRED,
                "4.15.0-187.198-generic",
            ),
            (
                "apply-failed",
                "supported",
                RebootStatus.REBOOT_REQUIRED,
                "4.15.0-187.198-generic",
            ),
        ),
    )
    @mock.patch(M_PATH + "get_kernel_info")
    @mock.patch("uaclient.livepatch.is_livepatch_installed")
    @mock.patch("uaclient.livepatch.status")
    @mock.patch(M_PATH + "get_reboot_required_pkgs")
    @mock.patch(M_PATH + "should_reboot", return_value=True)
    def test_get_reboot_status_reboot_pkgs_file_only_kernel_pkgs(
        self,
        m_should_reboot,
        m_get_reboot_required_pkgs,
        m_livepatch_status,
        m_is_livepatch_installed,
        m_kernel_info,
        livepatch_state,
        supported_state,
        expected_state,
        kernel_name,
    ):
        m_kernel_info.return_value = mock.MagicMock(
            proc_version_signature_version=kernel_name
        )
        m_is_livepatch_installed.return_value = True
        m_get_reboot_required_pkgs.return_value = RebootRequiredPkgs(
            standard_packages=[],
            kernel_packages=["linux-base", "linux-image-5.4.0-1074"],
        )
        m_livepatch_status.return_value = livepatch.LivepatchStatusStatus(
            kernel="4.15.0-187.198-generic",
            livepatch=livepatch.LivepatchPatchStatus(
                state=livepatch_state, fixes=None, version=None
            ),
            supported=supported_state,
        )

        assert _get_reboot_status() == expected_state
        assert 1 == m_should_reboot.call_count
        assert 1 == m_get_reboot_required_pkgs.call_count
        assert 1 == m_is_livepatch_installed.call_count
        assert 1 == m_livepatch_status.call_count
        assert 1 == m_kernel_info.call_count

    @mock.patch(M_PATH + "get_kernel_info")
    @mock.patch("uaclient.livepatch.is_livepatch_installed")
    @mock.patch("uaclient.livepatch.status")
    @mock.patch(M_PATH + "get_reboot_required_pkgs")
    @mock.patch(M_PATH + "should_reboot", return_value=True)
    def test_get_reboot_status_fail_parsing_kernel_info(
        self,
        m_should_reboot,
        m_get_reboot_required_pkgs,
        m_livepatch_status,
        m_is_livepatch_installed,
        m_kernel_info,
    ):
        m_kernel_info.return_value = mock.MagicMock(
            proc_version_signature_version=None
        )
        m_is_livepatch_installed.return_value = True
        m_get_reboot_required_pkgs.return_value = RebootRequiredPkgs(
            standard_packages=[],
            kernel_packages=["linux-base", "linux-image-5.4.0-1074"],
        )
        m_livepatch_status.return_value = livepatch.LivepatchStatusStatus(
            kernel="4.15.0-187.198-generic",
            livepatch=livepatch.LivepatchPatchStatus(
                state="applied", fixes=None, version=None
            ),
            supported=None,
        )

        assert _get_reboot_status() == RebootStatus.REBOOT_REQUIRED
        assert 1 == m_should_reboot.call_count
        assert 1 == m_get_reboot_required_pkgs.call_count
        assert 1 == m_is_livepatch_installed.call_count
        assert 1 == m_livepatch_status.call_count
        assert 1 == m_kernel_info.call_count
