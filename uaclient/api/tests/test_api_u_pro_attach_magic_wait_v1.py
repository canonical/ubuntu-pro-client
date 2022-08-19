import mock
import pytest

import uaclient.api.u.pro.attach.magic.wait.v1 as api_wait
from uaclient import exceptions
from uaclient.api.u.pro.attach.magic.wait.v1 import (
    MagicAttachWaitOptions,
    _wait,
)


@mock.patch("uaclient.contract.UAContractClient.get_magic_attach_token_info")
class TestMagicAttachWaitV1:
    @mock.patch("time.sleep")
    def test_wait_succeeds(self, m_sleep, m_attach_token_info, FakeConfig):
        magic_token = "test-id"

        m_attach_token_info.side_effect = [
            {},
            {},
            {
                "token": magic_token,
                "expires": "2100-06-09T18:14:55.323733Z",
                "expiresIn": "2000",
                "userCode": "1234",
                "contractToken": "ctoken",
                "contractID": "cid",
            },
        ]

        options = MagicAttachWaitOptions(magic_token=magic_token)
        expected_response = _wait(options, FakeConfig())

        assert expected_response.contract_token == "ctoken"
        assert expected_response.contract_id == "cid"
        assert 3 == m_attach_token_info.call_count
        assert 2 == m_sleep.call_count

    @mock.patch("time.sleep")
    def test_wait_fails(self, m_sleep, m_attach_token_info, FakeConfig):
        magic_token = "test-id"
        m_attach_token_info.side_effect = [
            {},
            exceptions.MagicAttachTokenError(),
        ]
        options = MagicAttachWaitOptions(magic_token=magic_token)

        with pytest.raises(exceptions.MagicAttachTokenError):
            _wait(options, FakeConfig())

    @mock.patch("time.sleep")
    def test_wait_fails_after_maximum_attempts(
        self, m_sleep, m_attach_token_info, FakeConfig
    ):
        magic_token = "test-id"
        m_attach_token_info.side_effect = [{}, {}, {}]

        options = MagicAttachWaitOptions(magic_token=magic_token)

        with pytest.raises(exceptions.MagicAttachTokenError):
            with mock.patch.object(api_wait, "MAXIMUM_ATTEMPTS", 2):
                _wait(options, FakeConfig())

    @mock.patch("time.sleep")
    def test_wait_fails_after_number_of_connectiviry_errors(
        self, m_sleep, m_attach_token_info, FakeConfig
    ):
        magic_token = "test-id"
        m_attach_token_info.side_effect = [
            exceptions.ConnectivityError(),
            exceptions.ConnectivityError(),
            exceptions.ConnectivityError(),
            exceptions.ConnectivityError(),
        ]

        options = MagicAttachWaitOptions(magic_token=magic_token)

        with pytest.raises(exceptions.ConnectivityError):
            _wait(options, FakeConfig())

        assert 3 == m_sleep.call_count

    @mock.patch("time.sleep")
    def test_wait_succeeds_after_number_of_connectivity_errors(
        self, m_sleep, m_attach_token_info, FakeConfig
    ):
        magic_token = "test-id"
        m_attach_token_info.side_effect = [
            exceptions.ConnectivityError(),
            exceptions.ConnectivityError(),
            exceptions.ConnectivityError(),
            {
                "token": magic_token,
                "expires": "2100-06-09T18:14:55.323733Z",
                "expiresIn": "2000",
                "userCode": "1234",
                "contractToken": "ctoken",
                "contractID": "cid",
            },
        ]

        options = MagicAttachWaitOptions(magic_token=magic_token)
        expected_response = _wait(options, FakeConfig())

        assert expected_response.contract_token == "ctoken"
        assert expected_response.contract_id == "cid"
        assert 4 == m_attach_token_info.call_count
        assert 3 == m_sleep.call_count

    @mock.patch("time.sleep")
    def test_wait_succeeds_after_unavailable_server(
        self, m_sleep, m_attach_token_info, FakeConfig
    ):
        magic_token = "test-id"
        m_attach_token_info.side_effect = [
            exceptions.ConnectivityError(),
            exceptions.MagicAttachUnavailable(),
            exceptions.MagicAttachUnavailable(),
            {
                "token": magic_token,
                "expires": "2100-06-09T18:14:55.323733Z",
                "expiresIn": "2000",
                "userCode": "1234",
            },
            {
                "token": magic_token,
                "expires": "2100-06-09T18:14:55.323733Z",
                "expiresIn": "2000",
                "userCode": "1234",
                "contractToken": "ctoken",
                "contractID": "cid",
            },
        ]

        options = MagicAttachWaitOptions(magic_token=magic_token)
        expected_response = _wait(options, FakeConfig())

        assert expected_response.contract_token == "ctoken"
        assert expected_response.contract_id == "cid"
        assert 5 == m_attach_token_info.call_count
        assert 4 == m_sleep.call_count
        assert [
            mock.call(10),
            mock.call(30),
            mock.call(30),
            mock.call(10),
        ] == m_sleep.call_args_list
