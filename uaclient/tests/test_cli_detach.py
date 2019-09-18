import mock

import pytest

from uaclient.cli import action_detach
from uaclient import exceptions
from uaclient import status
from uaclient.testing.fakes import FakeConfig


@mock.patch("uaclient.cli.os.getuid")
class TestActionDetach:
    def test_non_root_users_are_rejected(self, getuid):
        """Check that a UID != 0 will receive a message and exit non-zero"""
        getuid.return_value = 1

        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.NonRootUserError):
            action_detach(mock.MagicMock(), cfg)

    def test_unattached_error_message(self, getuid):
        """Check that root user gets unattached message."""

        getuid.return_value = 0
        cfg = FakeConfig()
        with pytest.raises(exceptions.UnattachedError) as err:
            action_detach(mock.MagicMock(), cfg)
        assert status.MESSAGE_UNATTACHED == err.value.msg
