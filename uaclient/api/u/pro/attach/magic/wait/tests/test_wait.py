import mock
import pytest

from uaclient import exceptions
from uaclient.api.u.pro.attach.magic.wait.v1 import wait


@mock.patch("uaclient.contract.UAContractClient.get_magic_attach_token_info")
class TestSimplifiedAttachWaitV1:
    @mock.patch("time.sleep")
    def test_wait_succeds(self, m_sleep, m_attach_token_info):
        magic_token = "test-id"

        m_attach_token_info.side_effect = [
            {},
            {},
            {
                "token": magic_token,
                "expires": "2100-06-09T18:14:55.323733Z",
                "userEmail": "test@test.com",
                "confirmationCode": "1234",
                "contractToken": "ctoken",
                "contractID": "cid",
            },
        ]

        expected_response = wait(magic_token=magic_token)

        assert expected_response.contract_token == "ctoken"
        assert expected_response.contract_id == "cid"
        assert 3 == m_attach_token_info.call_count
        assert 2 == m_sleep.call_count

    @mock.patch("time.sleep")
    def test_wait_fails(self, m_sleep, m_attach_token_info):
        magic_token = "test-id"
        m_attach_token_info.side_effect = [
            {},
            exceptions.MagicAttachTokenExpired(magic_token=magic_token),
        ]

        with pytest.raises(exceptions.MagicAttachTokenExpired):
            wait(magic_token=magic_token)
