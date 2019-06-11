import mock

from uaclient.testing.fakes import FakeConfig

import pytest

from uaclient.cli import action_attach, attach_parser, UA_DASHBOARD_URL
from uaclient.exceptions import NonRootUserError

M_PATH = 'uaclient.cli.'


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

    @mock.patch(M_PATH + 'contract.request_updated_contract')
    @mock.patch(M_PATH + 'sso.discharge_root_macaroon')
    @mock.patch(M_PATH + 'contract.UAContractClient')
    @mock.patch(M_PATH + 'action_status')
    def test_happy_path_without_token_arg(
            self, action_status, contract_client, discharge_root_macaroon,
            request_updated_contract, _m_getuid):
        """A mock-heavy test for the happy path without an argument"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        bound_macaroon = b'bound_bytes_macaroon'
        discharge_root_macaroon.return_value = bound_macaroon
        args = mock.MagicMock(token=None)
        cfg = FakeConfig.with_account()
        machine_token = {
            'machineTokenInfo': {'contractInfo': {'name': 'mycontract',
                                                  'resourceEntitlements': []}}}

        def fake_contract_updates(cfg, contract_token, allow_enable):
            cfg.write_cache('machine-token', machine_token)
            return True

        request_updated_contract.side_effect = fake_contract_updates
        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == action_status.call_count
        expected_macaroon = bound_macaroon.decode('utf-8')
        assert expected_macaroon == cfg._cache_contents['bound-macaroon']

    @mock.patch(M_PATH + 'sso.discharge_root_macaroon')
    @mock.patch(
        M_PATH + 'contract.UAContractClient.request_contract_machine_attach')
    @mock.patch(M_PATH + 'action_status')
    def test_happy_path_with_token_arg(self, action_status,
                                       contract_machine_attach,
                                       discharge_root_macaroon, _m_getuid):
        """A mock-heavy test for the happy path with the contract token arg"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = 'contract-token'
        args = mock.MagicMock(token=token)
        cfg = FakeConfig.with_account()
        machine_token = {
            'machineTokenInfo': {'contractInfo': {'name': 'mycontract',
                                                  'resourceEntitlements': []}}}

        def fake_contract_attach(contract_token):
            cfg.write_cache('machine-token', machine_token)
            return machine_token

        contract_machine_attach.side_effect = fake_contract_attach

        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == action_status.call_count
        expected_calls = [mock.call(contract_token=token)]
        assert expected_calls == contract_machine_attach.call_args_list
        assert 0 == discharge_root_macaroon.call_count

    @mock.patch('uaclient.cli.sso.discharge_root_macaroon')
    @mock.patch('uaclient.cli.contract.UAContractClient')
    @mock.patch('uaclient.cli.action_status')
    def test_no_discharged_macaroon(self, action_status, contract_client,
                                    discharge_root_macaroon, _m_getuid,
                                    capsys):
        """If we can't discharge the root macaroon, fail gracefully."""
        discharge_root_macaroon.return_value = None
        args = mock.MagicMock(token=None)
        cfg = FakeConfig.with_account()

        ret = action_attach(args, cfg)

        assert 1 == ret
        expected_msg = ('Could not attach machine. Unable to obtain'
                        ' authenticated user token')
        assert expected_msg in capsys.readouterr()[0]


class TestParser:

    def test_attach_parser_creates_a_parser_when_not_provided(self):
        """Create a named parser configured for 'attach' on no arguments."""
        parser = attach_parser()

        assert 'ubuntu-advantage attach [token] [flags]' == parser.usage
        descr = ('Attach this machine to an existing Ubuntu Advantage support'
                 ' subscription')
        assert descr == parser.description
        assert 'attach' == parser.prog
        assert 'Flags' == parser._optionals.title

        with mock.patch('sys.argv', ['attach']):
            args = parser.parse_args()
        assert None is args.password
        assert None is args.token
        assert None is args.email
        assert None is args.otp

    @pytest.mark.parametrize('param_name', ('email', 'otp', 'password'))
    def test_attach_parser_sets_optional_params(self, param_name):
        """Optional params are accepted by attach_parser."""
        parser = attach_parser()
        arg = '--%s' % param_name
        value = 'val%s' % param_name
        with mock.patch('sys.argv', ['attach', arg, value]):
            args = parser.parse_args()
        assert value == getattr(args, param_name)

    def test_attach_parser_accepts_positional_token(self):
        """Token positional param is accepted by attach_parser."""
        parser = attach_parser()
        with mock.patch('sys.argv', ['attach', 'tokenval']):
            args = parser.parse_args()
        assert 'tokenval' == args.token

    def test_attach_parser_help_points_to_ua_contract_dashboard_url(
            self, capsys):
        """Contracts' dashboard URL is referenced by ua attach --help."""
        parser = attach_parser()
        parser.print_help()
        assert UA_DASHBOARD_URL in capsys.readouterr()[0]
