import mock
import textwrap

import pytest

from uaclient import exceptions

try:
    from typing import Any, Dict, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

from uaclient import status
from uaclient.cli import action_refresh, main

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: ua refresh [flags]

Refresh existing Ubuntu Advantage contract and update services.

Flags:
  -h, --help  show this help message and exit
"""
)


@mock.patch(M_PATH + "os.getuid", return_value=0)
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

    def test_not_attached_errors(self, getuid, FakeConfig):
        """Check that an unattached machine emits message and exits 1"""
        cfg = FakeConfig()

        with pytest.raises(exceptions.UnattachedError):
            action_refresh(mock.MagicMock(), cfg)

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

    @mock.patch(M_PATH + "logging.error")
    @mock.patch(M_PATH + "contract.request_updated_contract")
    def test_refresh_contract_error_on_failure_to_update_contract(
        self, request_updated_contract, logging_error, getuid, FakeConfig
    ):
        """On failure in request_updates_contract emit an error."""
        request_updated_contract.side_effect = exceptions.UserFacingError(
            "Failure to refresh"
        )

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(), cfg)

        assert "Failure to refresh" == excinfo.value.msg

    @mock.patch(M_PATH + "contract.request_updated_contract")
    def test_refresh_contract_happy_path(
        self, request_updated_contract, getuid, capsys, FakeConfig
    ):
        """On success from request_updates_contract root user can refresh."""
        request_updated_contract.return_value = True

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(), cfg)

        assert 0 == ret
        assert status.MESSAGE_REFRESH_SUCCESS in capsys.readouterr()[0]
        assert [mock.call(cfg)] == request_updated_contract.call_args_list
