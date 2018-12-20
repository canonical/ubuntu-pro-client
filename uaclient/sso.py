import getpass
import json
import logging
import six

from uaclient import serviceclient
from uaclient import util


API_PATH_V2 = '/api/v2'
API_PATH_USER_KEYS = API_PATH_V2 + '/keys/'
API_PATH_OAUTH_TOKEN = API_PATH_V2 + '/tokens/oauth'
API_PATH_TOKEN_DISCHARGE = API_PATH_V2 + '/tokens/discharge'
API_PATH_TOKEN_REFRESH = API_PATH_V2 + '/tokens/refresh'


# Some Ubuntu SSO API responses use UNDERSCORE_DELIMITED codes, others use
# lowercase-hyphenated. We'll standardize on lowercase-hyphenated
API_ERROR_2FA_REQUIRED = 'twofactor-required'
API_ERROR_2FA_FAILURE = 'twofactor-failure'
API_ERROR_ACCOUNT_DEACTIVATED = 'account-deactivated'
API_ERROR_ACCOUNT_SUSPENDED = 'account-suspended'
API_ERROR_EMAIL_INVALIDATED = 'email-invalidated'
API_ERROR_INVALID_DATA = 'invalid-data'
API_ERROR_INVALID_CREDENTIALS = 'invalid-credentials'
API_ERROR_PASSWORD_POLICY_ERROR = 'password-policy-error'
API_ERROR_TOO_MANY_REQUESTS = 'too-many-requests'

PATH_SSO_TOKEN = 'sso-oauth.json'
PATH_MACAROON_TOKEN = 'sso-macaroon.json'


class SSOAuthError(util.UrlError):

    def __init__(self, e, error_response):
        super(SSOAuthError, self).__init__(e, e.code, e.headers, e.url)
        self.full_api_response = error_response
        if 'error_list' in error_response:
            self.api_errors = error_response['error_list']
        else:
            self.api_errors = [error_response]
        # Convert old api error codes from ERROR_CODE to error-code
        for error in self.api_errors:
            error['code'] = error['code'].lower().replace('_', '-')

    def __contains__(self, error_code):
        return error_code in [error['code'] for error in self.api_errors]

    def __get__(self, error_code, default=None):
        for error in self.api_errors:
            if error['code'] == error_code:
                return error['message']
        return default

    def __str__(self):
        prefix = super(SSOAuthError, self).__str__()
        details = []
        for err in self.api_errors:
            if not err.get('extra'):
                details.append(err['message'])
            else:
                for extra in err['extra'].values():
                    if isinstance(extra, list):
                        details.extend(extra)
                    else:
                        details.append(extra)
        return prefix + ': ' + ', '.join(details)


class UbuntuSSOClient(serviceclient.UAServiceClient):

    api_error_cls = SSOAuthError
    cfg_url_base_attr = 'sso_auth_url'

    def request_user_keys(self, email):
        content, _headers = self.request_url(
            API_PATH_USER_KEYS + six.moves.urllib.parse.quote(email))
        return content

    def request_oauth_token(self, email, password, token_name, otp=None):
        """Request a named oauth token for the authenticated user

        @param email: String with the email address of the SSO account holder.
        @param password: String with the password of the SSO account holder.
        @param token_name: String of the unique name to give the Oauth token.

        @return: the response from the SSO service for a OAuth token request.

        @raises:
             UrlError on unexpected url handling errors, timeouts etc
             SSOAuthError on expected SSO authentication issues
        """
        sso_token = self.cfg.read_cache('oauth')
        if sso_token:
            return sso_token
        data = {'email': email, 'password': password, 'token_name': token_name}
        if otp:
            data['otp'] = otp
        content, _headers = self.request_url(API_PATH_OAUTH_TOKEN, data=data)
        self.cfg.write_cache('oauth', json.dumps(content))
        return content

    def request_discharge_macaroon(self, email, password, caveat_id, otp=None):
        """Request a discharge macaroon for the authenticated user

        @param email: String with the email address of the SSO account holder.
        @param password: String with the password of the SSO account holder.
        @param caveat_id: String with the macaroon caveat ID obtained from
            subscription service.

        @return: the response from the SSO service for a macaroon request.

        @raises:
             UrlError on unexpected url handling errors, timeouts etc
             SSOAuthError on expected SSO authentication issues
        """
        macaroon_token = self.cfg.read_cache('macaroon')
        if macaroon_token:
            return macaroon_token
        data = {'email': email, 'password': password, 'caveat_id': caveat_id}
        if otp:
            data['otp'] = otp
        content, _hdrs = self.request_url(API_PATH_TOKEN_DISCHARGE, data=data)
        self.cfg.write_cache('macaroon', json.dumps(content))
        return content


def prompt_oauth_token(cfg):
    client = UbuntuSSOClient(cfg)
    oauth_token = client.cfg.read_cache('oauth')
    if oauth_token:
        return oauth_token
    try:
        email = six.moves.input('Email: ')
        password = getpass.getpass('Password: ')
        token_name = six.moves.input('Unique OAuth token name: ')
    except KeyboardInterrupt:
        return None
    try:
        oauth_token = client.request_oauth_token(
            email=email, password=password, token_name=token_name)
    except SSOAuthError as e:
        if API_ERROR_2FA_REQUIRED not in e:
            logging.error(str(e))
            return None
        try:
            otp = six.moves.input('Second-factor auth: ')
        except KeyboardInterrupt:
            return None
        oauth_token = client.request_oauth_token(
            email=email, password=password, token_name=token_name, otp=otp)
    return oauth_token


def prompt_request_macaroon(caveat_id=None):
    if not caveat_id:
        caveat_id = '{"secret": "thesecret", "version": 1}'
    email = six.moves.input('Email: ')
    password = getpass.getpass('Password: ')
    client = UbuntuSSOClient()
    try:
        content = client.request_discharge_macaroon(
            email=email, password=password, caveat_id=caveat_id)
    except SSOAuthError as e:
        if API_ERROR_2FA_REQUIRED not in e:
            logging.error(str(e))
            return None
        otp = six.moves.input('Second-factor auth: ')
        content = client.request_discharge_macaroon(
            email=email, password=password, caveat_id=caveat_id, otp=otp)
    return content
