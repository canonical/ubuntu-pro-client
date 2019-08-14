import mock

import pytest

from uaclient import exceptions
from uaclient.testing.fakes import FakeConfig

try:
    from typing import Any, Dict, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

from uaclient import status
from uaclient.cli import action_refresh

M_PATH = 'uaclient.cli.'


@mock.patch(M_PATH + 'os.getuid', return_value=0)
class TestActionRefresh:

    def test_non_root_users_are_rejected(self, getuid):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_refresh(mock.MagicMock(), cfg)

    def test_not_attached_errors(self, getuid):
        """Check that an unattached machine emits message and exits 1"""
        cfg = FakeConfig()

        with pytest.raises(exceptions.UnattachedError):
            action_refresh(mock.MagicMock(), cfg)

    @mock.patch(M_PATH + 'logging.error')
    @mock.patch(M_PATH + 'contract.request_updated_contract')
    def test_refresh_contract_error_on_failure_to_update_contract(
            self, request_updated_contract, logging_error, getuid):
        """On failure in request_updates_contract emit an error."""
        request_updated_contract.side_effect = exceptions.UserFacingError(
            'Failure to refresh')

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(), cfg)

        assert 'Failure to refresh' == excinfo.value.msg

    @mock.patch(M_PATH + 'contract.request_updated_contract')
    def test_refresh_contract_happy_path(
            self, request_updated_contract, getuid, capsys):
        """On success from request_updates_contract root user can refresh."""
        request_updated_contract.return_value = True

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(), cfg)

        assert 0 == ret
        assert status.MESSAGE_REFRESH_SUCCESS in capsys.readouterr()[0]
        assert [mock.call(cfg)] == request_updated_contract.call_args_list
