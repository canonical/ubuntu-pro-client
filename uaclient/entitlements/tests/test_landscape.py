import mock
import pytest

from uaclient import exceptions, messages
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.entitlements.landscape import LandscapeEntitlement


class TestLandscapeEntitlement:
    @pytest.mark.parametrize(
        [
            "assume_yes",
            "extra_args",
            "subp_sideeffect",
            "expected_subp_calls",
            "expected_result",
        ],
        [
            (
                False,
                None,
                None,
                [mock.call(["landscape-config"], pipe_stdouterr=False)],
                True,
            ),
            (
                False,
                ["extra"],
                None,
                [
                    mock.call(
                        ["landscape-config", "extra"], pipe_stdouterr=False
                    )
                ],
                True,
            ),
            (
                True,
                None,
                None,
                [
                    mock.call(
                        ["landscape-config", "--silent"], pipe_stdouterr=True
                    )
                ],
                True,
            ),
            (
                True,
                ["extra"],
                None,
                [
                    mock.call(
                        ["landscape-config", "extra", "--silent"],
                        pipe_stdouterr=True,
                    )
                ],
                True,
            ),
            (
                True,
                ["--silent", "extra"],
                None,
                [
                    mock.call(
                        ["landscape-config", "--silent", "extra"],
                        pipe_stdouterr=True,
                    )
                ],
                True,
            ),
            (
                False,
                None,
                exceptions.ProcessExecutionError("test"),
                [mock.call(["landscape-config"], pipe_stdouterr=False)],
                False,
            ),
        ],
    )
    @mock.patch("uaclient.system.subp")
    def test_perform_enable(
        self,
        m_subp,
        assume_yes,
        extra_args,
        subp_sideeffect,
        expected_subp_calls,
        expected_result,
        FakeConfig,
    ):
        m_subp.side_effect = subp_sideeffect
        landscape = LandscapeEntitlement(
            FakeConfig(), assume_yes=assume_yes, extra_args=extra_args
        )
        assert expected_result == landscape._perform_enable()
        assert expected_subp_calls == m_subp.call_args_list

    @pytest.mark.parametrize(
        [
            "subp_sideeffect",
            "expected_subp_calls",
            "expected_result",
        ],
        [
            (
                None,
                [mock.call(["landscape-config", "--disable"])],
                True,
            ),
            (
                exceptions.ProcessExecutionError("test"),
                [mock.call(["landscape-config", "--disable"])],
                True,
            ),
        ],
    )
    @mock.patch("uaclient.system.subp")
    def test_perform_disable(
        self,
        m_subp,
        subp_sideeffect,
        expected_subp_calls,
        expected_result,
        FakeConfig,
    ):
        m_subp.side_effect = subp_sideeffect
        landscape = LandscapeEntitlement(FakeConfig())
        assert expected_result == landscape._perform_disable()
        assert expected_subp_calls == m_subp.call_args_list

    @pytest.mark.parametrize(
        [
            "are_required_packages_installed",
            "is_systemd_unit_active",
            "expected_result",
        ],
        [
            (
                False,
                False,
                (
                    ApplicationStatus.DISABLED,
                    messages.LANDSCAPE_SERVICE_NOT_ACTIVE,
                ),
            ),
            (
                False,
                True,
                (
                    ApplicationStatus.DISABLED,
                    messages.LANDSCAPE_SERVICE_NOT_ACTIVE,
                ),
            ),
            (
                True,
                False,
                (
                    ApplicationStatus.DISABLED,
                    messages.LANDSCAPE_SERVICE_NOT_ACTIVE,
                ),
            ),
            (
                True,
                True,
                (ApplicationStatus.ENABLED, None),
            ),
        ],
    )
    @mock.patch("uaclient.system.is_systemd_unit_active")
    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement.are_required_packages_installed"  # noqa: E501
    )
    def test_application_status(
        self,
        m_are_required_packages_installed,
        m_is_systemd_unit_active,
        are_required_packages_installed,
        is_systemd_unit_active,
        expected_result,
        FakeConfig,
    ):
        m_are_required_packages_installed.return_value = (
            are_required_packages_installed
        )
        m_is_systemd_unit_active.return_value = is_systemd_unit_active
        landscape = LandscapeEntitlement(FakeConfig())
        assert expected_result == landscape.application_status()

    @pytest.mark.parametrize(
        [
            "we_are_currently_root",
            "subp_sideeffect",
            "expected_subp_calls",
            "expected_result",
        ],
        [
            (
                True,
                exceptions.ProcessExecutionError("test"),
                [mock.call(mock.ANY)],
                (True, messages.LANDSCAPE_NOT_REGISTERED),
            ),
            (True, None, [mock.call(mock.ANY)], (False, None)),
            (False, None, [], (False, None)),
        ],
    )
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_enabled_warning_status(
        self,
        m_we_are_currently_root,
        m_subp,
        we_are_currently_root,
        subp_sideeffect,
        expected_subp_calls,
        expected_result,
        FakeConfig,
    ):
        m_we_are_currently_root.return_value = we_are_currently_root
        m_subp.side_effect = subp_sideeffect
        landscape = LandscapeEntitlement(FakeConfig())
        assert expected_result == landscape.enabled_warning_status()
        assert expected_subp_calls == m_subp.call_args_list
