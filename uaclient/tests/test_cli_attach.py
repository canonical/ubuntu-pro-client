import mock

from uaclient.testing.fakes import FakeConfig

import pytest

from uaclient.cli import UA_AUTH_TOKEN_URL, action_attach, attach_parser
from uaclient.exceptions import NonRootUserError

M_PATH = 'uaclient.cli.'

BASIC_MACHINE_TOKEN = {
    'machineTokenInfo': {'contractInfo': {'name': 'mycontract',
                                          'resourceEntitlements': []}}}


@mock.patch(M_PATH + 'os.getuid')
def test_non_root_users_are_rejected(getuid):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = FakeConfig()
    with pytest.raises(NonRootUserError):
        action_attach(mock.MagicMock(), cfg)


# For all of these tests we want to appear as root, so mock on the class
@mock.patch(M_PATH + 'os.getuid', return_value=0)
class TestActionAttach:

    def test_already_attached(self, _m_getuid, capsys):
        """Check that an already-attached machine emits message and exits 0"""
        account_name = 'test_account'
        cfg = FakeConfig.for_attached_machine(account_name=account_name)

        ret = action_attach(mock.MagicMock(), cfg)

        assert 0 == ret
        expected_msg = "This machine is already attached to '{}'.".format(
            account_name)
        assert expected_msg in capsys.readouterr()[0]

    @mock.patch(
        M_PATH + 'contract.UAContractClient.request_contract_machine_attach')
    @mock.patch(M_PATH + 'action_status')
    def test_happy_path_with_token_arg(self, action_status,
                                       contract_machine_attach,
                                       _m_getuid):
        """A mock-heavy test for the happy path with the contract token arg"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = 'contract-token'
        args = mock.MagicMock(token=token)
        cfg = FakeConfig.with_account()

        def fake_contract_attach(contract_token):
            cfg.write_cache('machine-token', BASIC_MACHINE_TOKEN)
            return BASIC_MACHINE_TOKEN

        contract_machine_attach.side_effect = fake_contract_attach

        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == action_status.call_count
        expected_calls = [mock.call(contract_token=token)]
        assert expected_calls == contract_machine_attach.call_args_list

    @pytest.mark.parametrize('auto_enable', (True, False))
    def test_auto_enable_passed_through_to_request_updated_contract(
            self, _m_getuid, auto_enable):
        args = mock.MagicMock(auto_enable=auto_enable)

        def fake_contract_updates(cfg, contract_token, allow_enable):
            cfg.write_cache('machine-token', BASIC_MACHINE_TOKEN)
            return True

        with mock.patch(M_PATH + 'contract.request_updated_contract') as m_ruc:
            m_ruc.side_effect = fake_contract_updates
            action_attach(args, FakeConfig.with_account())

        expected_call = mock.call(mock.ANY, mock.ANY, allow_enable=auto_enable)
        assert [expected_call] == m_ruc.call_args_list


class TestParser:

    def test_attach_parser_creates_a_parser_when_not_provided(self):
        """Create a named parser configured for 'attach'."""
        parser = attach_parser()

        assert 'ubuntu-advantage attach [token] [flags]' == parser.usage
        descr = ('Attach this machine to an existing Ubuntu Advantage support'
                 ' subscription')
        assert descr == parser.description
        assert 'attach' == parser.prog
        assert 'Flags' == parser._optionals.title

        with mock.patch('sys.argv', ['attach', 'token']):
            args = parser.parse_args()
        assert 'token' == args.token

    def test_attach_parser_requires_positional_token(self, capsys):
        """Token is required"""
        parser = attach_parser()
        with mock.patch('sys.argv', ['attach']):
            with pytest.raises(SystemExit):
                parser.parse_args()
        _out, err = capsys.readouterr()
        assert 'the following arguments are required: token' in err

    def test_attach_parser_help_points_to_ua_contract_dashboard_url(
            self, capsys):
        """Contracts' dashboard URL is referenced by ua attach --help."""
        parser = attach_parser()
        parser.print_help()
        assert UA_AUTH_TOKEN_URL in capsys.readouterr()[0]

    def test_attach_parser_accepts_and_stores_no_auto_enable(self):
        parser = attach_parser()
        with mock.patch('sys.argv', ['attach', '--no-auto-enable', 'token']):
            args = parser.parse_args()
        assert not args.auto_enable

    def test_attach_parser_defaults_to_auto_enable(self):
        parser = attach_parser()
        with mock.patch('sys.argv', ['attach', 'token']):
            args = parser.parse_args()
        assert args.auto_enable
