import mock
import unittest
from typing import Any, Dict, Optional

from uaclient import status
from uaclient.cli import action_attach
from uaclient.config import UAConfig


class TestConfig(UAConfig):

    def __init__(self, cache_contents: Dict[str, str] = None) -> None:
        self._cache_contents = (
            cache_contents if cache_contents is not None else {})
        super().__init__({})

    def read_cache(self, key: str, quiet: bool = False) -> Optional[str]:
        return self._cache_contents.get(key)

    def write_cache(self, key: str, content: Any) -> None:
        self._cache_contents[key] = content

    @classmethod
    def with_account(cls, account_name: str = 'test_account'):
        return cls({
            'accounts': {
                'accounts': [{'name': account_name, 'id': account_name}]},
        })

    @classmethod
    def for_attached_machine(cls, account_name: str = 'test_account'):
        return cls({
            'accounts': {'accounts': [{'name': account_name}]},
            'machine-token': 'not-null',
        })


@mock.patch('uaclient.cli.os.getuid')
@mock.patch('uaclient.cli.sys.stdout')
def test_non_root_users_are_rejected(stdout, getuid):
    """Check that a UID != 0 will receive a message and exit non-zero"""
    getuid.return_value = 1

    cfg = TestConfig()
    ret = action_attach(mock.MagicMock(), cfg)

    assert 1 == ret
    assert (
        mock.call(status.MESSAGE_NONROOT_USER) in stdout.write.call_args_list)


# For all of these tests we want to appear as root, so mock on the class
@mock.patch('uaclient.cli.os.getuid', mock.Mock(return_value=0))
class TestActionAttach(unittest.TestCase):

    @mock.patch('uaclient.cli.sys.stdout')
    def test_already_attached(self, stdout):
        """Check that an already-attached machine emits message and exits 0"""
        account_name = 'test_account'
        cfg = TestConfig.for_attached_machine(account_name=account_name)

        ret = action_attach(mock.MagicMock(), cfg)

        assert 0 == ret
        expected_msg = "This machine is already attached to '{}'.".format(
            account_name)
        assert mock.call(expected_msg) in stdout.write.call_args_list

    @mock.patch('uaclient.cli.sso.discharge_root_macaroon')
    @mock.patch('uaclient.cli.contract.UAContractClient')
    @mock.patch('uaclient.cli.action_status')
    def test_happy_path_without_arg(self, action_status, contract_client,
                                    discharge_root_macaroon):
        """A mock-heavy test for the happy path without an argument"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        bound_macaroon = b'bound_bytes_macaroon'
        discharge_root_macaroon.return_value = bound_macaroon
        args = mock.MagicMock(token=None)
        cfg = TestConfig.with_account()

        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == action_status.call_count
        expected_macaroon = bound_macaroon.decode('utf-8')
        assert expected_macaroon == cfg._cache_contents['bound-macaroon']

    @mock.patch('uaclient.cli.sso.discharge_root_macaroon')
    @mock.patch('uaclient.cli.contract.UAContractClient')
    @mock.patch('uaclient.cli.action_status')
    def test_happy_path_with_arg(self, action_status, contract_client,
                                 discharge_root_macaroon):
        """A mock-heavy test for the happy path without an argument"""
        # TODO: Improve this test with less general mocking and more
        # post-conditions
        token = 'my-token'
        args = mock.MagicMock(token=token)
        cfg = TestConfig.with_account()

        ret = action_attach(args, cfg)

        assert 0 == ret
        assert 1 == action_status.call_count
        assert token == cfg._cache_contents['bound-macaroon']

    @mock.patch('uaclient.cli.sys.stdout')
    @mock.patch('uaclient.cli.sso.discharge_root_macaroon')
    @mock.patch('uaclient.cli.contract.UAContractClient')
    @mock.patch('uaclient.cli.action_status')
    def test_no_discharged_macaroon(self, action_status, contract_client,
                                    discharge_root_macaroon, stdout):
        """If we can't discharge the root macaroon, fail gracefully."""
        discharge_root_macaroon.return_value = None
        args = mock.MagicMock(token=None)
        cfg = TestConfig.with_account()

        ret = action_attach(args, cfg)

        assert 1 == ret
        expected_msg = ('Could not attach machine. Unable to obtain'
                        ' authenticated user token')
        assert mock.call(expected_msg) in stdout.write.call_args_list
