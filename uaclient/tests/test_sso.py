import mock

import pytest

from uaclient import config, exceptions, sso, util


class TestSSOClient:

    @mock.patch('uaclient.serviceclient.util.readurl', return_value=('', ''))
    def test_configured_url_can_have_trailing_forwardslash(
            self, m_readurl, tmpdir):
        cfg = config.UAConfig(
            cfg={'data_dir': tmpdir.strpath, 'sso_auth_url': 'http://auth/'})
        client = sso.UbuntuSSOClient(cfg)
        client.request_discharge_macaroon('email', 'passwd', 'caveat')
        headers = client.headers()
        expected_call = mock.call(
            data=mock.ANY,
            headers=headers, method=None,
            url='http://auth/api/v2/tokens/discharge')
        assert [expected_call] == m_readurl.call_args_list


class TestDischargeRootMacaroon:

    def test_urlerror_converted_to_userfacing_error(self):
        m_contract_client = mock.Mock()
        url = 'https://some_url'
        error = util.UrlError(mock.Mock(), url=url)
        m_contract_client.request_root_macaroon.side_effect = error

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

    @mock.patch('uaclient.sso.prompt_request_macaroon')
    @mock.patch('uaclient.sso.extract_macaroon_caveat_id')
    def test_userfacingerror_untouched(self, m_emci, m_prompt):
        m_contract_client = mock.MagicMock()
        exception_msg = 'our exception msg'
        m_prompt.side_effect = exceptions.UserFacingError(exception_msg)

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            sso.discharge_root_macaroon(m_contract_client)

        assert exception_msg == excinfo.value.msg


class TestExtractMacaroonCaveatId:

    @mock.patch('uaclient.sso.pymacaroons.Macaroon.deserialize')
    def test_invalidrootmacaroonerror_message(self, m_deserialize):
        exception_msg = 'our exception msg'
        m_deserialize.side_effect = sso.InvalidRootMacaroonError(exception_msg)
        with pytest.raises(sso.InvalidRootMacaroonError) as excinfo:
            sso.extract_macaroon_caveat_id('')

        assert exception_msg == str(excinfo.value)


class SimpleSSOAuthError(sso.SSOAuthError):
    # SSOAuthError does a lot of work based on the response from the
    # server; we just need to be sure that the string representation is
    # included in our UserFacingError, so simplify the implementation
    def __init__(self, exception_string='', api_errors=None):
        self.exception_string = exception_string
        self.api_errors = api_errors if api_errors is not None else []

    def __str__(self):
        return self.exception_string


class TestPromptRequestMacaroon:

    @mock.patch('uaclient.sso.getpass')
    @mock.patch('builtins.input')
    @mock.patch('uaclient.sso.UbuntuSSOClient')
    def test_ssoautherrors_raise_userfacingerrors(
            self, m_sso_client, m_input, _m_getpass):
        exception_string = 'simple sso fail'

        m_sso_client.return_value.request_discharge_macaroon.side_effect = (
            SimpleSSOAuthError(exception_string))

        config_mock = mock.Mock()
        config_mock.read_cache.return_value = None
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            sso.prompt_request_macaroon(config_mock, 'caveat_id')

        assert exception_string == excinfo.value.msg
        assert mock.call('Second-factor auth: ') not in m_input.call_args_list

    @mock.patch('uaclient.sso.getpass')
    @mock.patch('builtins.input')
    @mock.patch('uaclient.sso.UbuntuSSOClient')
    def test_2fa_errors_dont_raise_and_request_extra_input(
            self, m_sso_client, m_input, _m_getpass):
        exception = SimpleSSOAuthError(
            api_errors=[{'code': sso.API_ERROR_2FA_REQUIRED}])
        m_sso_client.return_value.request_discharge_macaroon.side_effect = [
            exception, "some content"]

        config_mock = mock.Mock()
        config_mock.read_cache.return_value = None

        sso.prompt_request_macaroon(config_mock, 'caveat_id')

        assert mock.call('Second-factor auth: ') in m_input.call_args_list

    @mock.patch('uaclient.sso.getpass')
    @mock.patch('builtins.input')
    @mock.patch('uaclient.sso.UbuntuSSOClient')
    def test_empty_content_raises_userfacingerror(
            self, m_sso_client, m_input, _m_getpass):
        m_sso_client.return_value.request_discharge_macaroon.return_value = {}

        config_mock = mock.Mock()
        config_mock.read_cache.return_value = None

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            sso.prompt_request_macaroon(config_mock, 'caveat_id')

        assert 'SSO server returned empty content' == excinfo.value.msg
