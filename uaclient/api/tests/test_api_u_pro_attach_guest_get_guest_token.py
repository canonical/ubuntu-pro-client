import mock
import pytest

from uaclient.api import exceptions
from uaclient.api.u.pro.attach.guest.get_guest_token.v1 import (
    GetGuestTokenResult,
    _get_guest_token,
)
from uaclient.testing import helpers

M_PATH = "uaclient.api.u.pro.attach.guest.get_guest_token.v1."


class TestGetGuestTokenV1:
    @pytest.mark.parametrize(
        [
            "root",
            "attached",
            "machine_token_dict",
            "contract_id",
            "machine_id",
            "expected_exception",
            "expected_contract_calls",
        ],
        [
            (
                False,
                None,
                None,
                None,
                None,
                pytest.raises(exceptions.NonRootUserError),
                [],
            ),
            (
                True,
                False,
                None,
                None,
                None,
                pytest.raises(exceptions.UnattachedError),
                [],
            ),
            (
                True,
                True,
                None,
                None,
                None,
                pytest.raises(exceptions.UnattachedError),
                [],
            ),
            (
                True,
                True,
                {"machineToken": "fake_machine_token"},
                "contractId",
                "machineId",
                helpers.does_not_raise(),
                [
                    mock.call(
                        machine_token="fake_machine_token",
                        contract_id="contractId",
                        machine_id="machineId",
                    )
                ],
            ),
        ],
    )
    @mock.patch(M_PATH + "system.get_machine_id")
    @mock.patch(M_PATH + "machine_token.get_machine_token_file")
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "util.we_are_currently_root")
    @mock.patch(M_PATH + "contract.UAContractClient.get_guest_token")
    def test_get_guest_token(
        self,
        m_get_guest_token,
        m_we_are_currently_root,
        m_is_attached,
        m_get_machine_token_file,
        m_get_machine_id,
        root,
        attached,
        machine_token_dict,
        contract_id,
        machine_id,
        expected_exception,
        expected_contract_calls,
        FakeConfig,
    ):
        m_we_are_currently_root.return_value = root
        m_is_attached.return_value.is_attached = attached
        m_get_machine_token_file.return_value.machine_token = (
            machine_token_dict
        )
        m_get_machine_token_file.return_value.contract_id = contract_id
        m_get_machine_id.return_value = machine_id
        fake_guest_token = {
            "guestToken": "fake_guest_token",
            "id": "fake_id",
            "expires": "fake_expires",
        }
        m_get_guest_token.return_value = fake_guest_token
        expected_result = GetGuestTokenResult(
            guest_token=fake_guest_token["guestToken"],
            id=fake_guest_token["id"],
            expires=fake_guest_token["expires"],
        )
        with expected_exception:
            assert expected_result == _get_guest_token(FakeConfig())

        assert m_get_guest_token.call_args_list == expected_contract_calls
