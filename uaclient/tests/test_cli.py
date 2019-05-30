import mock

import pytest

from uaclient.cli import assert_attached_root, main
from uaclient.exceptions import (
    NonRootUserError, UserFacingError, UnattachedError)
from uaclient.testing.fakes import FakeConfig


class TestAssertAttachedRoot:

    @pytest.mark.parametrize('attached,uid,expected_message', (
        (True, 0, None),
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

    @pytest.mark.parametrize('attached,uid,expected_exception', [
        (True, 1000, NonRootUserError),
        (False, 1000, NonRootUserError),
        (False, 0, UnattachedError),
    ])
    def test_assert_attached_root_exceptions(
            self, attached, uid, expected_exception):

        @assert_attached_root
        def test_function(args, cfg):
            return mock.sentinel.success

        if attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()

        with pytest.raises(expected_exception):
            with mock.patch('uaclient.cli.os.getuid', return_value=uid):
                test_function(mock.Mock(), cfg)


class TestMain:

    @mock.patch('uaclient.cli.setup_logging')
    @mock.patch('uaclient.cli.get_parser')
    def test_keyboard_interrupt_handled_gracefully(
            self, m_get_parser, _m_setup_logging, capsys):
        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = KeyboardInterrupt

        with pytest.raises(SystemExit) as excinfo:
            main(['some', 'args'])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert '' == out
        assert 'Interrupt received; exiting.\n' == err

    @mock.patch('uaclient.cli.setup_logging')
    @mock.patch('uaclient.cli.get_parser')
    def test_user_facing_error_handled_gracefully(
            self, m_get_parser, _m_setup_logging, capsys):
        msg = 'You need to know about this.'

        m_args = m_get_parser.return_value.parse_args.return_value
        m_args.action.side_effect = UserFacingError(msg)

        with pytest.raises(SystemExit) as excinfo:
            main(['some', 'args'])

        exc = excinfo.value
        assert 1 == exc.code

        out, err = capsys.readouterr()
        assert '' == out
        assert 'ERROR: {}\n'.format(msg) == err
