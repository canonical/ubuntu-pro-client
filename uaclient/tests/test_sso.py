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

    @mock.patch('uaclient.sso.extract_macaroon_caveat_id')
    def test_macaroon_format_error_converted_to_userfacing_error(self, m_emci):
        m_contract_client = mock.MagicMock()
        exception_msg = 'our exception msg'
        m_emci.side_effect = sso.MacaroonFormatError(exception_msg)

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            sso.discharge_root_macaroon(m_contract_client)

        expected_msg = "Invalid root macaroon: {}".format(exception_msg)
        assert expected_msg == excinfo.value.msg


class TestExtractMacaroonCaveatId:

    @mock.patch('uaclient.sso.pymacaroons.Macaroon.deserialize')
    def test_invalidrootmacaroonerror_message(self, m_deserialize):
        exception_msg = 'our exception msg'
        m_deserialize.side_effect = sso.InvalidRootMacaroonError(exception_msg)
        with pytest.raises(sso.InvalidRootMacaroonError) as excinfo:
            sso.extract_macaroon_caveat_id('')

        assert exception_msg == str(excinfo.value)
