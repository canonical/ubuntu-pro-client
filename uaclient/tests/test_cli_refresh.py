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


@mock.patch(M_PATH + 'sys.stdout')
@mock.patch(M_PATH + 'os.getuid', return_value=0)
class TestActionRefresh:

    def test_non_root_users_are_rejected(self, getuid, stdout):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(), cfg)

        assert 1 == ret
        assert (
            mock.call(status.MESSAGE_NONROOT_USER) in
            stdout.write.call_args_list)

    def test_not_attached_errors(self, getuid, stdout):
        """Check that an unattached machine emits message and exits 1"""
        cfg = FakeConfig()

        ret = action_refresh(mock.MagicMock(), cfg)

        assert 1 == ret
        expected_msg = status.MESSAGE_UNATTACHED
        assert mock.call(expected_msg) in stdout.write.call_args_list

    @mock.patch(M_PATH + 'logging.error')
    @mock.patch(M_PATH + 'contract.request_updated_contract')
    def test_refresh_contract_error_on_failure_to_update_contract(
            self, request_updated_contract, logging_error, getuid, stdout):
        """On failure in request_updates_contract emit an error."""
        request_updated_contract.return_value = False  # failure to refresh

        cfg = FakeConfig.for_attached_machine()

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            action_refresh(mock.MagicMock(), cfg)

        assert status.MESSAGE_REFRESH_FAILURE == excinfo.value.msg

    @mock.patch(M_PATH + 'contract.request_updated_contract')
    def test_refresh_contract_happy_path(
            self, request_updated_contract, getuid, stdout):
        """On success from request_updates_contract root user can refresh."""
        request_updated_contract.return_value = True

        cfg = FakeConfig.for_attached_machine()
        ret = action_refresh(mock.MagicMock(), cfg)

        assert 0 == ret
        assert (
            mock.call(status.MESSAGE_REFRESH_SUCCESS) in
            stdout.write.call_args_list)
        assert [mock.call(cfg)] == request_updated_contract.call_args_list
