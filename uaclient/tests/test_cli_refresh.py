import mock
import pytest

try:
    from typing import Any, Dict, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

from uaclient import exceptions
from uaclient import status
from uaclient import util
from uaclient.cli import action_refresh, main

HELP_OUTPUT = """\
usage: ua refresh [contract|config] [flags]

Refresh existing Ubuntu Advantage contract and update services.

positional arguments:
  {contract,config}  Target to refresh. `ua refresh contract` will update
                     contract details from the server and perform any updates
                     necessary. `ua refresh config` will reload /etc/ubuntu-
                     advantage/uaclient.conf and perform any changes
                     necessary. `ua refresh` is the equivalent of `ua refresh
                     config && ua refresh contract`.

Flags:
  -h, --help         show this help message and exit
"""


@mock.patch("os.getuid", return_value=0)
class TestActionRefresh:
    def test_refresh_help(self, _getuid, capsys):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "refresh", "--help"]):
                main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    def test_non_root_users_are_rejected(self, getuid, FakeConfig):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_refresh(mock.MagicMock(), cfg)

    @pytest.mark.parametrize(
        "target, expect_unattached_error",
        [(None, True), ("contract", True), ("config", False)],
    )
    @mock.patch("uaclient.config.UAConfig.write_cfg")
    def test_not_attached_errors(
        self, _m_write_cfg, getuid, target, expect_unattached_error, FakeConfig
    ):
        """Check that an unattached machine emits message and exits 1"""
        cfg = FakeConfig()

        cfg.update_messaging_timer = 0
        cfg.update_status_timer = 0
        cfg.gcp_auto_attach_timer = 0

        if expect_unattached_error:
            with pytest.raises(exceptions.UnattachedError):
                action_refresh(mock.MagicMock(target=target), cfg)
        else:
            action_refresh(mock.MagicMock(target=target), cfg)

    @mock.patch("uaclient.cli.util.subp")
    def test_lock_file_exists(self, m_subp, _getuid, FakeConfig):
        """Check inability to refresh if operation holds lock file."""
        cfg = FakeConfig().for_attached_machine()
        with open(cfg.data_path("lock"), "w") as stream:
            stream.write("123:ua disable")
        with pytest.raises(exceptions.LockHeldError) as err:
            action_refresh(mock.MagicMock(), cfg)
        assert [mock.call(["ps", "123"])] == m_subp.call_args_list
        assert (
            "Unable to perform: ua refresh.\n"
            "Operation in progress: ua disable (pid:123)"
        ) == err.value.msg

    @mock.patch("logging.exception")
    @mock.patch("uaclient.contract.request_updated_contract")
    def test_refresh_contract_error_on_failure_to_update_contract(
        self, request_updated_contract, logging_error, getuid, FakeConfig
    ):
        """On failure in request_updates_contract emit an error."""
        request_updated_contract.side_effect = util.UrlError(mock.MagicMock())

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(target="contract"), cfg)

        assert status.MESSAGE_REFRESH_CONTRACT_FAILURE == excinfo.value.msg

    @mock.patch("uaclient.contract.request_updated_contract")
    def test_refresh_contract_happy_path(
        self, request_updated_contract, getuid, capsys, FakeConfig
    ):
        """On success from request_updates_contract root user can refresh."""
        request_updated_contract.return_value = True

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(target="contract"), cfg)

        assert 0 == ret
        assert (
            status.MESSAGE_REFRESH_CONTRACT_SUCCESS in capsys.readouterr()[0]
        )
        assert [mock.call(cfg)] == request_updated_contract.call_args_list

    @mock.patch("logging.exception")
    @mock.patch(
        "uaclient.config.UAConfig.process_config", side_effect=RuntimeError()
    )
    def test_refresh_config_error_on_failure_to_process_config(
        self, _m_process_config, _m_logging_error, getuid, FakeConfig
    ):
        """On failure in process_config emit an error."""

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(target="config"), cfg)

        assert status.MESSAGE_REFRESH_CONFIG_FAILURE == excinfo.value.msg

    @mock.patch("uaclient.config.UAConfig.process_config")
    def test_refresh_config_happy_path(
        self, m_process_config, getuid, capsys, FakeConfig
    ):
        """On success from process_config root user gets success message."""

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(target="config"), cfg)

        assert 0 == ret
        assert status.MESSAGE_REFRESH_CONFIG_SUCCESS in capsys.readouterr()[0]
        assert [mock.call()] == m_process_config.call_args_list

    @mock.patch("uaclient.contract.request_updated_contract")
    @mock.patch("uaclient.config.UAConfig.process_config")
    def test_refresh_all_happy_path(
        self,
        m_process_config,
        m_request_updated_contract,
        getuid,
        capsys,
        FakeConfig,
    ):
        """On success from process_config root user gets success message."""

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(target=None), cfg)
        out, err = capsys.readouterr()

        assert 0 == ret
        assert status.MESSAGE_REFRESH_CONFIG_SUCCESS in out
        assert status.MESSAGE_REFRESH_CONTRACT_SUCCESS in out
        assert [mock.call()] == m_process_config.call_args_list
        assert [mock.call(cfg)] == m_request_updated_contract.call_args_list
