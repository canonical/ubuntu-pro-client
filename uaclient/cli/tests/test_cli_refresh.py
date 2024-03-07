import mock
import pytest

from uaclient import exceptions, lock, messages
from uaclient.cli import action_refresh, main
from uaclient.files.notices import Notice

HELP_OUTPUT = """\
usage: pro refresh [contract|config|messages] [flags]

Refresh three distinct Ubuntu Pro related artifacts in the system:

* contract: Update contract details from the server.
* config:   Reload the config file.
* messages: Update APT and MOTD messages related to UA.

You can individually target any of the three specific actions,
by passing the target name to the command.  If no `target`
is specified, all targets are refreshed.

positional arguments:
  {contract,config,messages}
                        Target to refresh.

Flags:
  -h, --help            show this help message and exit
"""


class TestActionRefresh:
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_refresh_help(
        self, _m_resources, _m_setup_logging, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "refresh", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT in out

    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    def test_non_root_users_are_rejected(
        self, we_are_currently_root, FakeConfig
    ):
        """Check that a UID != 0 will receive a message and exit non-zero"""

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_refresh(mock.MagicMock(), cfg=cfg)

    @pytest.mark.parametrize(
        "target, expect_unattached_error",
        [(None, True), ("contract", True), ("config", False)],
    )
    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    def test_not_attached_errors(
        self,
        _m_check_lock_info,
        target,
        expect_unattached_error,
        FakeConfig,
    ):
        """Check that an unattached machine emits message and exits 1"""
        cfg = FakeConfig()

        cfg.user_config.update_messaging_timer = 0
        cfg.user_config.metering_timer = 0

        with mock.patch.object(lock, "lock_data_file"):
            if expect_unattached_error:
                with pytest.raises(exceptions.UnattachedError):
                    action_refresh(mock.MagicMock(target=target), cfg=cfg)
            else:
                action_refresh(mock.MagicMock(target=target), cfg=cfg)

    @mock.patch("uaclient.lock.check_lock_info")
    @mock.patch("time.sleep")
    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(
        self, m_subp, m_sleep, m_check_lock_info, FakeConfig
    ):
        """Check inability to refresh if operation holds lock file."""
        cfg = FakeConfig().for_attached_machine()
        m_check_lock_info.return_value = (123, "pro disable")
        with pytest.raises(exceptions.LockHeldError) as err:
            action_refresh(mock.MagicMock(), cfg=cfg)
        assert 12 == m_check_lock_info.call_count
        expected_msg = messages.E_LOCK_HELD_ERROR.format(
            lock_request="pro refresh", lock_holder="pro disable", pid=123
        )
        assert expected_msg.msg == err.value.msg

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("logging.exception")
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_refresh_contract_error_on_failure_to_update_contract(
        self,
        m_remove_notice,
        refresh,
        logging_error,
        m_check_log_info,
        FakeConfig,
    ):
        """On failure in request_updates_contract emit an error."""
        refresh.side_effect = exceptions.ConnectivityError(
            mock.MagicMock(), "url"
        )

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UbuntuProError) as excinfo:
            with mock.patch.object(lock, "lock_data_file"):
                action_refresh(mock.MagicMock(target="contract"), cfg=cfg)

        assert messages.E_REFRESH_CONTRACT_FAILURE.msg == excinfo.value.msg
        assert [
            mock.call("", messages.NOTICE_REFRESH_CONTRACT_WARNING)
        ] != m_remove_notice.call_args_list

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_refresh_contract_happy_path(
        self,
        m_remove_notice,
        refresh,
        _m_check_lock_info,
        capsys,
        FakeConfig,
    ):
        """On success from request_updates_contract root user can refresh."""
        refresh.return_value = True

        cfg = FakeConfig.for_attached_machine()
        with mock.patch.object(lock, "lock_data_file"):
            ret = action_refresh(mock.MagicMock(target="contract"), cfg=cfg)

        assert 0 == ret
        assert messages.REFRESH_CONTRACT_SUCCESS in capsys.readouterr()[0]
        assert [mock.call(cfg)] == refresh.call_args_list
        assert [
            mock.call(Notice.CONTRACT_REFRESH_WARNING),
        ] == m_remove_notice.call_args_list

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.cli.update_motd_messages")
    def test_refresh_messages_error(
        self, m_update_motd, _m_check_lock_info, FakeConfig
    ):
        """On failure in update_motd_messages emit an error."""
        m_update_motd.side_effect = Exception("test")

        with pytest.raises(exceptions.UbuntuProError) as excinfo:
            with mock.patch.object(lock, "lock_data_file"):
                action_refresh(
                    mock.MagicMock(target="messages"), cfg=FakeConfig()
                )

        assert messages.E_REFRESH_MESSAGES_FAILURE.msg == excinfo.value.msg

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.apt_news.update_apt_news")
    @mock.patch("uaclient.timer.update_messaging.exists", return_value=True)
    @mock.patch("uaclient.timer.update_messaging.LOG.exception")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.cli.update_motd_messages")
    def test_refresh_messages_doesnt_fail_if_update_notifier_does(
        self,
        m_update_motd,
        m_subp,
        log_exception,
        _m_path,
        _m_update_apt_news,
        _m_check_lock_info,
        capsys,
        FakeConfig,
    ):
        subp_exc = Exception("test")
        m_subp.side_effect = [subp_exc, ""]

        with mock.patch.object(lock, "lock_data_file"):
            ret = action_refresh(
                mock.MagicMock(target="messages"), cfg=FakeConfig()
            )

        assert 0 == ret
        assert 1 == log_exception.call_count
        assert [mock.call(subp_exc)] == log_exception.call_args_list
        assert messages.REFRESH_MESSAGES_SUCCESS in capsys.readouterr()[0]

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.apt_news.update_apt_news")
    @mock.patch("uaclient.cli.refresh_motd")
    @mock.patch("uaclient.cli.update_motd_messages")
    def test_refresh_messages_happy_path(
        self,
        m_update_motd,
        m_refresh_motd,
        m_update_apt_news,
        _m_check_lock_info,
        capsys,
        FakeConfig,
    ):
        """On success from request_updates_contract root user can refresh."""
        cfg = FakeConfig()
        with mock.patch.object(lock, "lock_data_file"):
            ret = action_refresh(mock.MagicMock(target="messages"), cfg=cfg)

        assert 0 == ret
        assert messages.REFRESH_MESSAGES_SUCCESS in capsys.readouterr()[0]
        assert [mock.call(cfg)] == m_update_motd.call_args_list
        assert [mock.call()] == m_refresh_motd.call_args_list
        assert 1 == m_update_motd.call_count
        assert 1 == m_refresh_motd.call_count
        assert 1 == m_update_apt_news.call_count

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("logging.exception")
    @mock.patch(
        "uaclient.config.UAConfig.process_config", side_effect=RuntimeError()
    )
    def test_refresh_config_error_on_failure_to_process_config(
        self,
        _m_process_config,
        _m_logging_error,
        _m_check_lock_info,
        FakeConfig,
    ):
        """On failure in process_config emit an error."""

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UbuntuProError) as excinfo:
            with mock.patch.object(lock, "lock_data_file"):
                action_refresh(mock.MagicMock(target="config"), cfg=cfg)

        assert messages.E_REFRESH_CONFIG_FAILURE.msg == excinfo.value.msg

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.config.UAConfig.process_config")
    def test_refresh_config_happy_path(
        self,
        m_process_config,
        m_check_lock_info,
        capsys,
        FakeConfig,
    ):
        """On success from process_config root user gets success message."""

        cfg = FakeConfig.for_attached_machine()
        with mock.patch.object(lock, "lock_data_file"):
            ret = action_refresh(mock.MagicMock(target="config"), cfg=cfg)

        assert 0 == ret
        assert messages.REFRESH_CONFIG_SUCCESS in capsys.readouterr()[0]
        assert [mock.call()] == m_process_config.call_args_list

    @mock.patch("uaclient.lock.check_lock_info", return_value=(-1, ""))
    @mock.patch("uaclient.apt_news.update_apt_news")
    @mock.patch("uaclient.cli.refresh_motd")
    @mock.patch("uaclient.cli.update_motd_messages")
    @mock.patch("uaclient.contract.refresh")
    @mock.patch("uaclient.config.UAConfig.process_config")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_refresh_all_happy_path(
        self,
        m_remove_notice,
        m_process_config,
        m_refresh,
        m_update_motd,
        m_refresh_motd,
        m_update_apt_news,
        _m_check_lock_info,
        capsys,
        FakeConfig,
    ):
        """On success from process_config root user gets success message."""

        cfg = FakeConfig.for_attached_machine()
        with mock.patch.object(lock, "lock_data_file"):
            ret = action_refresh(mock.MagicMock(target=None), cfg=cfg)

        out, err = capsys.readouterr()

        assert 0 == ret
        assert messages.REFRESH_CONFIG_SUCCESS in out
        assert messages.REFRESH_CONTRACT_SUCCESS in out
        assert messages.REFRESH_MESSAGES_SUCCESS in out
        assert [mock.call()] == m_process_config.call_args_list
        assert [mock.call(cfg)] == m_refresh.call_args_list
        assert [
            mock.call(Notice.CONTRACT_REFRESH_WARNING),
        ] == m_remove_notice.call_args_list
        assert 1 == m_update_motd.call_count
        assert 1 == m_refresh_motd.call_count
        assert 1 == m_update_apt_news.call_count
