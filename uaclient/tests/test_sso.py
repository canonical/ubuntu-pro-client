import mock

import pytest

from uaclient import exceptions, sso, util


class TestDischargeRootMacaroon:

    def test_urlerror_converted_to_userfacing_error(self):
        m_contract_client = mock.Mock()
        url = 'https://some_url'
        m_contract_client.request_root_macaroon.side_effect = util.UrlError(
            mock.Mock(), url=url)

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            sso.discharge_root_macaroon(m_contract_client)

        expected_msg = "Could not reach URL {} to authenticate".format(url)
        assert expected_msg == excinfo.value.msg
