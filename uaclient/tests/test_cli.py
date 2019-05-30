import mock

import pytest

from uaclient import status
from uaclient.cli import assert_attached_root
from uaclient.testing.fakes import FakeConfig


class TestAssertAttachedRoot:

    @pytest.mark.parametrize('attached,uid,expected_message', (
        (True, 0, None),
        (True, 1000, status.MESSAGE_NONROOT_USER),
        (False, 1000, status.MESSAGE_UNATTACHED),
        (False, 0, status.MESSAGE_UNATTACHED),
    ))
    def test_assert_attached_root(
            self, attached, uid, expected_message, capsys):

        @assert_attached_root
        def test_function(args, cfg):
            return mock.sentinel.success

        if attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()

        with mock.patch('uaclient.cli.os.getuid', return_value=uid):
            ret = test_function(mock.Mock(), cfg)

        if expected_message is None:
            assert mock.sentinel.success == ret
            expected_message = ''
        else:
            assert 1 == ret

        out, _err = capsys.readouterr()
        assert expected_message == out.strip()
