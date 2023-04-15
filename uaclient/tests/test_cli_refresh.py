import mock
import pytest

from uaclient import exceptions, messages
from uaclient.cli import action_refresh, main
from uaclient.files.notices import Notice

HELP_OUTPUT = """\
usage: pro refresh [contract|config|messages] [flags]

Refresh three distinct Ubuntu Pro related artifacts in the system:

* contract: Update contract details from the server.
* config:   Reload the config file.
* messages: Update APT and MOTD messages related to UA.

You can individually target any of the three specific actions,
by passing it's target to nome to the command.  If no `target`
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
    def test_not_attached_errors(
        self,
        target,
        expect_unattached_error,
        FakeConfig,
    ):
        """Check that an unattached machine emits message and exits 1"""
        cfg = FakeConfig()

        cfg.user_config.update_messaging_timer = 0
        cfg.user_config.metering_timer = 0

        if expect_unattached_error:
            with pytest.raises(exceptions.UnattachedError):
                action_refresh(mock.MagicMock(target=target), cfg=cfg)
        else:
            action_refresh(mock.MagicMock(target=target), cfg=cfg)

    @mock.patch("uaclient.system.subp")
    def test_lock_file_exists(self, m_subp, FakeConfig):
        """Check inability to refresh if operation holds lock file."""
        cfg = FakeConfig().for_attached_machine()
        cfg.write_cache("lock", "123:pro disable")
        with pytest.raises(exceptions.LockHeldError) as err:
            action_refresh(mock.MagicMock(), cfg=cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: pro refresh.\n"
            "Operation in progress: pro disable (pid:123)"
        ) == err.value.msg

    @mock.patch("logging.exception")
    @mock.patch("uaclient.contract.request_updated_contract")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_refresh_contract_error_on_failure_to_update_contract(
        self,
        m_remove_notice,
        request_updated_contract,
        logging_error,
        FakeConfig,
    ):
        """On failure in request_updates_contract emit an error."""
        request_updated_contract.side_effect = exceptions.UrlError(
            mock.MagicMock()
        )

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(target="contract"), cfg=cfg)

        assert messages.REFRESH_CONTRACT_FAILURE == excinfo.value.msg
        assert [
            mock.call("", messages.NOTICE_REFRESH_CONTRACT_WARNING)
        ] != m_remove_notice.call_args_list

    @mock.patch("uaclient.contract.request_updated_contract")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_refresh_contract_happy_path(
        self,
        m_remove_notice,
        request_updated_contract,
        capsys,
        FakeConfig,
    ):
        """On success from request_updates_contract root user can refresh."""
        request_updated_contract.return_value = True

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(target="contract"), cfg=cfg)

        assert 0 == ret
        assert messages.REFRESH_CONTRACT_SUCCESS in capsys.readouterr()[0]
        assert [mock.call(cfg)] == request_updated_contract.call_args_list
        assert [
            mock.call(Notice.CONTRACT_REFRESH_WARNING),
            mock.call(Notice.OPERATION_IN_PROGRESS),
        ] == m_remove_notice.call_args_list

    @mock.patch("uaclient.cli.update_motd_messages")
    def test_refresh_messages_error(self, m_update_motd, FakeConfig):
        """On failure in update_motd_messages emit an error."""
        m_update_motd.side_effect = Exception("test")

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(target="messages"), cfg=FakeConfig())

        assert messages.REFRESH_MESSAGES_FAILURE == excinfo.value.msg

    @mock.patch("uaclient.apt_news.update_apt_news")
    @mock.patch("uaclient.timer.update_messaging.exists", return_value=True)
    @mock.patch("logging.exception")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.cli.update_motd_messages")
    def test_refresh_messages_doesnt_fail_if_update_notifier_does(
        self,
        m_update_motd,
        m_subp,
        logging_error,
        _m_path,
        _m_update_apt_news,
        capsys,
        FakeConfig,
    ):
        subp_exc = Exception("test")
        m_subp.side_effect = [subp_exc, ""]

        ret = action_refresh(
            mock.MagicMock(target="messages"), cfg=FakeConfig()
        )

        assert 0 == ret
        assert 1 == logging_error.call_count
        assert [mock.call(subp_exc)] == logging_error.call_args_list
        assert messages.REFRESH_MESSAGES_SUCCESS in capsys.readouterr()[0]

    @mock.patch("uaclient.apt_news.update_apt_news")
    @mock.patch("uaclient.cli.refresh_motd")
    @mock.patch("uaclient.cli.update_motd_messages")
    def test_refresh_messages_happy_path(
        self,
        m_update_motd,
        m_refresh_motd,
        m_update_apt_news,
        capsys,
        FakeConfig,
    ):
        """On success from request_updates_contract root user can refresh."""
        cfg = FakeConfig()
        ret = action_refresh(mock.MagicMock(target="messages"), cfg=cfg)

        assert 0 == ret
        assert messages.REFRESH_MESSAGES_SUCCESS in capsys.readouterr()[0]
        assert [mock.call(cfg)] == m_update_motd.call_args_list
        assert [mock.call()] == m_refresh_motd.call_args_list
        assert 1 == m_update_motd.call_count
        assert 1 == m_refresh_motd.call_count
        assert 1 == m_update_apt_news.call_count

    @mock.patch("logging.exception")
    @mock.patch(
        "uaclient.config.UAConfig.process_config", side_effect=RuntimeError()
    )
    def test_refresh_config_error_on_failure_to_process_config(
        self,
        _m_process_config,
        _m_logging_error,
        FakeConfig,
    ):
        """On failure in process_config emit an error."""

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(target="config"), cfg=cfg)

        assert messages.REFRESH_CONFIG_FAILURE == excinfo.value.msg

    @mock.patch("uaclient.config.UAConfig.process_config")
    def test_refresh_config_happy_path(
        self,
        m_process_config,
        capsys,
        FakeConfig,
    ):
        """On success from process_config root user gets success message."""

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(target="config"), cfg=cfg)

        assert 0 == ret
        assert messages.REFRESH_CONFIG_SUCCESS in capsys.readouterr()[0]
        assert [mock.call()] == m_process_config.call_args_list

    @mock.patch("uaclient.apt_news.update_apt_news")
    @mock.patch("uaclient.cli.refresh_motd")
    @mock.patch("uaclient.cli.update_motd_messages")
    @mock.patch("uaclient.contract.request_updated_contract")
    @mock.patch("uaclient.config.UAConfig.process_config")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_refresh_all_happy_path(
        self,
        m_remove_notice,
        m_process_config,
        m_request_updated_contract,
        m_update_motd,
        m_refresh_motd,
        m_update_apt_news,
        capsys,
        FakeConfig,
    ):
        """On success from process_config root user gets success message."""

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(target=None), cfg=cfg)
        out, err = capsys.readouterr()

        assert 0 == ret
        assert messages.REFRESH_CONFIG_SUCCESS in out
        assert messages.REFRESH_CONTRACT_SUCCESS in out
        assert messages.REFRESH_MESSAGES_SUCCESS in out
        assert [mock.call()] == m_process_config.call_args_list
        assert [mock.call(cfg)] == m_request_updated_contract.call_args_list
        assert [
            mock.call(Notice.CONTRACT_REFRESH_WARNING),
            mock.call(Notice.OPERATION_IN_PROGRESS),
        ] == m_remove_notice.call_args_list
        assert 1 == m_update_motd.call_count
        assert 1 == m_refresh_motd.call_count
        assert 1 == m_update_apt_news.call_count
