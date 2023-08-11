import mock
import pytest

from ubuntupro import exceptions, messages
from ubuntupro.entitlements.entitlement_status import ApplicationStatus
from ubuntupro.entitlements.landscape import LandscapeEntitlement


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
    @mock.patch("ubuntupro.system.subp")
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
            "rename_sideeffect",
            "expected_subp_calls",
            "expected_rename_calls",
            "expected_result",
        ],
        [
            (
                None,
                None,
                [mock.call(["landscape-config", "--disable"])],
                [
                    mock.call(
                        "/etc/landscape/client.conf",
                        "/etc/landscape/client.conf.pro-disable-backup",
                    )
                ],
                True,
            ),
            (
                exceptions.ProcessExecutionError("test"),
                None,
                [mock.call(["landscape-config", "--disable"])],
                [
                    mock.call(
                        "/etc/landscape/client.conf",
                        "/etc/landscape/client.conf.pro-disable-backup",
                    )
                ],
                True,
            ),
            (
                None,
                FileNotFoundError(),
                [mock.call(["landscape-config", "--disable"])],
                [
                    mock.call(
                        "/etc/landscape/client.conf",
                        "/etc/landscape/client.conf.pro-disable-backup",
                    )
                ],
                True,
            ),
        ],
    )
    @mock.patch("os.rename")
    @mock.patch("ubuntupro.system.subp")
    def test_perform_disable(
        self,
        m_subp,
        m_rename,
        subp_sideeffect,
        rename_sideeffect,
        expected_subp_calls,
        expected_rename_calls,
        expected_result,
        FakeConfig,
    ):
        m_subp.side_effect = subp_sideeffect
        m_rename.side_effect = rename_sideeffect
        landscape = LandscapeEntitlement(FakeConfig())
        assert expected_result == landscape._perform_disable()
        assert expected_subp_calls == m_subp.call_args_list
        assert expected_rename_calls == m_rename.call_args_list

    @pytest.mark.parametrize(
        [
            "is_installed",
            "expected_is_installed_calls",
            "expected_result",
        ],
        [
            (
                False,
                [mock.call("landscape-client")],
                (
                    ApplicationStatus.DISABLED,
                    messages.LANDSCAPE_CLIENT_NOT_INSTALLED,
                ),
            ),
            (
                True,
                [mock.call("landscape-client")],
                (ApplicationStatus.ENABLED, None),
            ),
        ],
    )
    @mock.patch("ubuntupro.apt.is_installed")
    def test_application_status(
        self,
        m_is_installed,
        is_installed,
        expected_is_installed_calls,
        expected_result,
        FakeConfig,
    ):
        m_is_installed.return_value = is_installed
        landscape = LandscapeEntitlement(FakeConfig())
        assert expected_result == landscape.application_status()
        assert expected_is_installed_calls == m_is_installed.call_args_list

    @pytest.mark.parametrize(
        [
            "exists",
            "we_are_currently_root",
            "subp_sideeffect",
            "unit_active",
            "expected_subp_calls",
            "expected_result",
        ],
        [
            (
                False,
                None,
                None,
                None,
                [],
                (True, messages.LANDSCAPE_NOT_CONFIGURED),
            ),
            (
                True,
                True,
                exceptions.ProcessExecutionError("test"),
                None,
                [mock.call(mock.ANY)],
                (True, messages.LANDSCAPE_NOT_REGISTERED),
            ),
            (
                True,
                True,
                None,
                False,
                [mock.call(mock.ANY)],
                (True, messages.LANDSCAPE_SERVICE_NOT_ACTIVE),
            ),
            (True, True, None, True, [mock.call(mock.ANY)], (False, None)),
            (
                True,
                False,
                None,
                False,
                [],
                (True, messages.LANDSCAPE_SERVICE_NOT_ACTIVE),
            ),
            (True, False, None, True, [], (False, None)),
        ],
    )
    @mock.patch("ubuntupro.system.is_systemd_unit_active")
    @mock.patch("ubuntupro.system.subp")
    @mock.patch("ubuntupro.util.we_are_currently_root")
    @mock.patch("os.path.exists")
    def test_enabled_warning_status(
        self,
        m_exists,
        m_we_are_currently_root,
        m_subp,
        m_is_systemd_unit_active,
        exists,
        we_are_currently_root,
        subp_sideeffect,
        unit_active,
        expected_subp_calls,
        expected_result,
        FakeConfig,
    ):
        m_exists.return_value = exists
        m_we_are_currently_root.return_value = we_are_currently_root
        m_subp.side_effect = subp_sideeffect
        m_is_systemd_unit_active.return_value = unit_active
        landscape = LandscapeEntitlement(FakeConfig())
        assert expected_result == landscape.enabled_warning_status()
        assert expected_subp_calls == m_subp.call_args_list
