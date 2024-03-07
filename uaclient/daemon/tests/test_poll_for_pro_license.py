import mock
import pytest

from uaclient import exceptions, lock
from uaclient.clouds.aws import UAAutoAttachAWSInstance
from uaclient.clouds.gcp import UAAutoAttachGCPInstance
from uaclient.daemon.poll_for_pro_license import (
    attempt_auto_attach,
    poll_for_pro_license,
)

M_PATH = "uaclient.daemon.poll_for_pro_license."


time_mock_curr_value = 0


def time_mock_side_effect_increment_by(increment):
    def _time_mock_side_effect():
        global time_mock_curr_value
        time_mock_curr_value += increment
        return time_mock_curr_value

    return _time_mock_side_effect


@mock.patch(M_PATH + "LOG.debug")
@mock.patch(M_PATH + "actions.auto_attach")
@mock.patch(M_PATH + "lock.SpinLock")
class TestAttemptAutoAttach:
    def test_success(
        self, m_spin_lock, m_auto_attach, m_log_debug, FakeConfig
    ):
        cfg = FakeConfig()
        cloud = mock.MagicMock()

        with mock.patch.object(lock, "lock_data_file"):
            attempt_auto_attach(cfg, cloud)

        assert [
            mock.call(lock_holder="pro.daemon.attempt_auto_attach")
        ] == m_spin_lock.call_args_list
        assert [mock.call(cfg, cloud)] == m_auto_attach.call_args_list
        assert [
            mock.call("Successful auto attach")
        ] == m_log_debug.call_args_list

    @mock.patch(M_PATH + "system.create_file")
    @mock.patch(M_PATH + "lock.clear_lock_file_if_present")
    @mock.patch(M_PATH + "LOG.error")
    @mock.patch(M_PATH + "LOG.info")
    def test_exception(
        self,
        m_log_info,
        m_log_error,
        m_clear_lock,
        m_create_file,
        m_spin_lock,
        m_auto_attach,
        m_log_debug,
        FakeConfig,
    ):
        err = Exception()
        m_auto_attach.side_effect = err
        cfg = FakeConfig()
        cloud = mock.MagicMock()

        attempt_auto_attach(cfg, cloud)

        assert [
            mock.call(lock_holder="pro.daemon.attempt_auto_attach")
        ] == m_spin_lock.call_args_list
        assert [mock.call(cfg, cloud)] == m_auto_attach.call_args_list
        assert [mock.call(err)] == m_log_error.call_args_list
        assert [mock.call()] == m_clear_lock.call_args_list
        assert [
            mock.call("creating flag file to trigger retries")
        ] == m_log_info.call_args_list
        assert [
            mock.call("/run/ubuntu-advantage/flags/auto-attach-failed")
        ] == m_create_file.call_args_list


@mock.patch(M_PATH + "LOG.debug")
@mock.patch(M_PATH + "time.sleep")
@mock.patch(M_PATH + "time.time")
@mock.patch(M_PATH + "attempt_auto_attach")
@mock.patch(M_PATH + "UAAutoAttachGCPInstance.is_pro_license_present")
@mock.patch(M_PATH + "UAAutoAttachGCPInstance.should_poll_for_pro_license")
@mock.patch(M_PATH + "cloud_instance_factory")
@mock.patch(M_PATH + "system.is_current_series_lts")
@mock.patch(M_PATH + "util.is_config_value_true")
class TestPollForProLicense:
    @pytest.mark.parametrize(
        "is_config_value_true,"
        "is_attached,"
        "is_current_series_lts,"
        "cloud_instance,"
        "should_poll,"
        "is_pro_license_present,"
        "cfg_poll_for_pro_licenses,"
        "expected_log_debug_calls,"
        "expected_is_pro_license_present_calls,"
        "expected_attempt_auto_attach_calls",
        [
            (
                True,
                None,
                None,
                None,
                None,
                None,
                None,
                [mock.call("Configured to not auto attach, shutting down")],
                [],
                [],
            ),
            (
                False,
                True,
                None,
                None,
                None,
                None,
                None,
                [mock.call("Already attached, shutting down")],
                [],
                [],
            ),
            (
                False,
                False,
                False,
                None,
                None,
                None,
                None,
                [mock.call("Not on LTS, shutting down")],
                [],
                [],
            ),
            (
                False,
                False,
                True,
                exceptions.CloudFactoryNoCloudError(),
                None,
                None,
                None,
                [mock.call("Not on cloud, shutting down")],
                [],
                [],
            ),
            (
                False,
                False,
                True,
                UAAutoAttachAWSInstance(),
                None,
                None,
                None,
                [mock.call("Not on supported cloud platform, shutting down")],
                [],
                [],
            ),
            (
                False,
                False,
                True,
                UAAutoAttachGCPInstance(),
                False,
                None,
                None,
                [mock.call("Not on supported instance, shutting down")],
                [],
                [],
            ),
            (
                False,
                False,
                True,
                UAAutoAttachGCPInstance(),
                True,
                True,
                None,
                [],
                [mock.call(wait_for_change=False)],
                [mock.call(mock.ANY, mock.ANY)],
            ),
            (
                False,
                False,
                True,
                UAAutoAttachGCPInstance(),
                True,
                exceptions.CancelProLicensePolling(),
                None,
                [mock.call("Cancelling polling")],
                [mock.call(wait_for_change=False)],
                [],
            ),
            (
                False,
                False,
                True,
                UAAutoAttachGCPInstance(),
                True,
                False,
                False,
                [
                    mock.call(
                        "Configured to not poll for pro license, shutting down"
                    )
                ],
                [mock.call(wait_for_change=False)],
                [],
            ),
            (
                False,
                False,
                True,
                UAAutoAttachGCPInstance(),
                True,
                False,
                False,
                [
                    mock.call(
                        "Configured to not poll for pro license, shutting down"
                    )
                ],
                [mock.call(wait_for_change=False)],
                [],
            ),
        ],
    )
    def test_before_polling_loop_checks(
        self,
        m_is_config_value_true,
        m_is_current_series_lts,
        m_cloud_instance_factory,
        m_should_poll,
        m_is_pro_license_present,
        m_attempt_auto_attach,
        m_time,
        m_sleep,
        m_log_debug,
        is_config_value_true,
        is_attached,
        is_current_series_lts,
        cloud_instance,
        should_poll,
        is_pro_license_present,
        cfg_poll_for_pro_licenses,
        expected_log_debug_calls,
        expected_is_pro_license_present_calls,
        expected_attempt_auto_attach_calls,
        FakeConfig,
    ):
        if is_attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()
        cfg.user_config.poll_for_pro_license = cfg_poll_for_pro_licenses

        m_is_config_value_true.return_value = is_config_value_true
        m_is_current_series_lts.return_value = is_current_series_lts
        m_cloud_instance_factory.side_effect = [cloud_instance]
        m_should_poll.return_value = should_poll
        m_is_pro_license_present.side_effect = [is_pro_license_present]

        poll_for_pro_license(cfg)

        assert expected_log_debug_calls == m_log_debug.call_args_list
        assert (
            expected_is_pro_license_present_calls
            == m_is_pro_license_present.call_args_list
        )
        assert (
            expected_attempt_auto_attach_calls
            == m_attempt_auto_attach.call_args_list
        )

    @pytest.mark.parametrize(
        "is_pro_license_present_side_effect,"
        "time_side_effect,"
        "expected_is_pro_license_present_calls,"
        "expected_attempt_auto_attach_calls,"
        "expected_log_debug_calls,"
        "expected_sleep_calls",
        [
            (
                [False, True],
                time_mock_side_effect_increment_by(100),
                [
                    mock.call(wait_for_change=False),
                    mock.call(wait_for_change=True),
                ],
                [mock.call(mock.ANY, mock.ANY)],
                [],
                [],
            ),
            (
                [False, False, False, False, False, True],
                time_mock_side_effect_increment_by(100),
                [
                    mock.call(wait_for_change=False),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                ],
                [mock.call(mock.ANY, mock.ANY)],
                [],
                [],
            ),
            (
                [False, False, True],
                time_mock_side_effect_increment_by(1),
                [
                    mock.call(wait_for_change=False),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                ],
                [mock.call(mock.ANY, mock.ANY)],
                [
                    mock.call(
                        "wait_for_change returned quickly and no pro license"
                        " present. Waiting %d seconds before polling again",
                        123,
                    )
                ],
                [mock.call(123)],
            ),
            (
                [False, False, False, False, False, True],
                time_mock_side_effect_increment_by(1),
                [
                    mock.call(wait_for_change=False),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                ],
                [mock.call(mock.ANY, mock.ANY)],
                [
                    mock.call(mock.ANY, mock.ANY),
                    mock.call(mock.ANY, mock.ANY),
                    mock.call(mock.ANY, mock.ANY),
                    mock.call(mock.ANY, mock.ANY),
                ],
                [
                    mock.call(123),
                    mock.call(123),
                    mock.call(123),
                    mock.call(123),
                ],
            ),
            (
                [
                    False,
                    False,
                    exceptions.DelayProLicensePolling(),
                    False,
                    exceptions.DelayProLicensePolling(),
                    True,
                ],
                time_mock_side_effect_increment_by(100),
                [
                    mock.call(wait_for_change=False),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                ],
                [mock.call(mock.ANY, mock.ANY)],
                [],
                [mock.call(123), mock.call(123)],
            ),
            (
                [False, False, exceptions.CancelProLicensePolling()],
                time_mock_side_effect_increment_by(100),
                [
                    mock.call(wait_for_change=False),
                    mock.call(wait_for_change=True),
                    mock.call(wait_for_change=True),
                ],
                [],
                [mock.call("Cancelling polling")],
                [],
            ),
        ],
    )
    def test_polling_loop(
        self,
        m_is_config_value_true,
        m_is_current_series_lts,
        m_cloud_instance_factory,
        m_should_poll,
        m_is_pro_license_present,
        m_attempt_auto_attach,
        m_time,
        m_sleep,
        m_log_debug,
        is_pro_license_present_side_effect,
        time_side_effect,
        expected_is_pro_license_present_calls,
        expected_attempt_auto_attach_calls,
        expected_log_debug_calls,
        expected_sleep_calls,
        FakeConfig,
    ):
        cfg = FakeConfig()
        cfg.user_config.poll_for_pro_license = True
        cfg.user_config.polling_error_retry_delay = 123

        m_is_config_value_true.return_value = False
        m_is_current_series_lts.return_value = True
        m_cloud_instance_factory.return_value = UAAutoAttachGCPInstance()
        m_should_poll.return_value = True
        m_is_pro_license_present.side_effect = (
            is_pro_license_present_side_effect
        )
        m_time.side_effect = time_side_effect

        poll_for_pro_license(cfg)

        assert expected_sleep_calls == m_sleep.call_args_list
        assert expected_log_debug_calls == m_log_debug.call_args_list
        assert (
            expected_is_pro_license_present_calls
            == m_is_pro_license_present.call_args_list
        )
        assert (
            expected_attempt_auto_attach_calls
            == m_attempt_auto_attach.call_args_list
        )
