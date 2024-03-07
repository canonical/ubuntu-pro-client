import mock
import pytest

from lib.reboot_cmds import fix_pro_pkg_holds, main
from uaclient import exceptions
from uaclient.testing import fakes
from uaclient.testing.helpers import does_not_raise

M_FIPS_PATH = "uaclient.entitlements.fips.FIPSEntitlement."


@mock.patch("uaclient.entitlements.fips.FIPSEntitlement.install_packages")
@mock.patch("uaclient.entitlements.fips.FIPSEntitlement.setup_apt_config")
@mock.patch("uaclient.entitlements.fips.FIPSEntitlement.application_status")
class TestFixProPkgHolds:
    @pytest.mark.parametrize(
        [
            "fips_status",
            "fips_setup_apt_config_side_effect",
            "fips_install_packages_side_effect",
            "expected_fips_setup_apt_config_calls",
            "expected_fips_install_packages_calls",
            "expected_raises",
        ],
        [
            ("disabled", None, None, [], [], does_not_raise()),
            (
                "enabled",
                None,
                None,
                [mock.call()],
                [mock.call(cleanup_on_failure=False)],
                does_not_raise(),
            ),
            (
                "enabled",
                Exception(),
                None,
                [mock.call()],
                [mock.call(cleanup_on_failure=False)],
                does_not_raise(),
            ),
            (
                "enabled",
                Exception(),
                fakes.FakeUbuntuProError(),
                [mock.call()],
                [mock.call(cleanup_on_failure=False)],
                pytest.raises(exceptions.UbuntuProError),
            ),
        ],
    )
    @mock.patch("uaclient.files.state_files.status_cache_file.read")
    def test_fix_pro_pkg_holds(
        self,
        m_status_cache_file_read,
        m_fips_status,
        m_fips_setup_apt_config,
        m_fips_install_packages,
        fips_status,
        fips_setup_apt_config_side_effect,
        fips_install_packages_side_effect,
        expected_fips_setup_apt_config_calls,
        expected_fips_install_packages_calls,
        expected_raises,
        FakeConfig,
    ):
        m_fips_setup_apt_config.side_effect = fips_setup_apt_config_side_effect
        m_fips_install_packages.side_effect = fips_install_packages_side_effect
        cfg = FakeConfig()
        m_status_cache_file_read.return_value = {
            "services": [{"name": "fips", "status": fips_status}]
        }

        with expected_raises:
            fix_pro_pkg_holds(cfg)

        assert (
            expected_fips_setup_apt_config_calls
            == m_fips_setup_apt_config.call_args_list
        )
        assert (
            expected_fips_install_packages_calls
            == m_fips_install_packages.call_args_list
        )


@mock.patch("uaclient.files.notices.add")
@mock.patch("uaclient.files.notices.remove")
@mock.patch(
    "uaclient.upgrade_lts_contract.process_contract_delta_after_apt_lock"
)  # noqa: E501
@mock.patch("lib.reboot_cmds.refresh_contract")
@mock.patch("lib.reboot_cmds.fix_pro_pkg_holds")
@mock.patch("uaclient.lock.SpinLock")
@mock.patch("lib.reboot_cmds._is_attached")
@mock.patch(
    "uaclient.files.state_files.reboot_cmd_marker_file",
    new_callable=mock.PropertyMock,
)
class TestMain:
    @pytest.mark.parametrize(
        [
            "marker_file_present",
            "is_attached",
            "expected_delete_marker",
            "expected_calls",
            "expected_ret",
        ],
        [
            (False, False, False, False, 0),
            (True, False, True, False, 0),
            (False, True, False, False, 0),
            (True, True, True, True, 0),
        ],
    )
    def test_main_success_cases(
        self,
        m_reboot_cmd_marker_file,
        m_is_attached,
        m_spin_lock,
        m_fix_pro_pkg_holds,
        m_refresh_contract,
        m_process_contract_delta_after_apt_lock,
        m_notices_remove,
        m_notices_add,
        marker_file_present,
        is_attached,
        expected_delete_marker,
        expected_calls,
        expected_ret,
        FakeConfig,
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=is_attached)
        m_reboot_cmd_marker_file.is_present = marker_file_present
        assert expected_ret == main(FakeConfig())

        # no notices are added in any success scenario
        assert [] == m_notices_add.call_args_list
        # any existing notice should always be cleaned up on success
        assert [mock.call(mock.ANY)] == m_notices_remove.call_args_list

        if expected_delete_marker:
            assert [
                mock.call()
            ] == m_reboot_cmd_marker_file.delete.call_args_list
        else:
            assert [] == m_reboot_cmd_marker_file.delete.call_args_list

        if expected_calls:
            assert [
                mock.call(lock_holder="pro-reboot-cmds")
            ] == m_spin_lock.call_args_list
            assert [mock.call(mock.ANY)] == m_fix_pro_pkg_holds.call_args_list
            assert [mock.call(mock.ANY)] == m_refresh_contract.call_args_list
            assert [
                mock.call(mock.ANY)
            ] == m_process_contract_delta_after_apt_lock.call_args_list
        else:
            assert [] == m_spin_lock.call_args_list
            assert [] == m_fix_pro_pkg_holds.call_args_list
            assert [] == m_refresh_contract.call_args_list
            assert [] == m_process_contract_delta_after_apt_lock.call_args_list

    @pytest.mark.parametrize(
        [
            "error",
            "expected_ret",
        ],
        [
            (Exception(), 1),
            (
                exceptions.LockHeldError(
                    lock_request="", lock_holder="", pid=1
                ),
                1,
            ),
            (fakes.FakeUbuntuProError(), 1),
        ],
    )
    def test_main_error_cases(
        self,
        m_reboot_cmd_marker_file,
        m_is_attached,
        m_spin_lock,
        m_fix_pro_pkg_holds,
        m_refresh_contract,
        m_process_contract_delta_after_apt_lock,
        m_notices_remove,
        m_notices_add,
        error,
        expected_ret,
        FakeConfig,
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)
        m_reboot_cmd_marker_file.is_present = True
        m_fix_pro_pkg_holds.side_effect = error
        assert expected_ret == main(FakeConfig())
        assert [mock.call(mock.ANY)] == m_notices_add.call_args_list
