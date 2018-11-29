import getpass
import json
import os
import six

from uaclient import config
from uaclient import util
import logging


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


class UbuntuSSOClient(object):


    data_paths = {'oauth': 'sso-oauth.json', 'macaroon': 'sso-macaroon.json'}

    def __init__(self, cfg=None):
        if not cfg:
            self.cfg = config.parse_config()
        else:
            self.cfg = cfg

    def data_path(self, key=None):
        """Return the file path in the data directory represented by the key"""
        if not key:
            return self.cfg['data_dir']
        return os.path.join(self.cfg['data_dir'], self.data_paths[key])

    def read_cached_data(self, key):
        if key not in self.data_paths:
            return None
        cache_path = self.data_path(key)
        if not os.path.exists(cache_path):
            return None
        content = util.load_file(cache_path)
        json_content = util.maybe_parse_json(content)
        return json_content if json_content else content

    def headers(self):
        return {'user-agent': 'UA-Client/%s' % config.get_version(),
                'accept': 'application/json',
                'content-type': 'application/json'}

    def request_url(self, path, data=None, headers=None):
        if path[0] != '/':
            path = '/' + path
        if not headers:
            headers=self.headers()
        if headers.get('content-type') == 'application/json' and data:
            data = util.encode_text(json.dumps(data))
        url = self.cfg['sso_auth_url'] + path
        try:
            response = util.readurl(url=url, data=data, headers=headers)
        except six.moves.urllib.error.URLError as e:
            if hasattr(e, 'read'):
                sso_error_details = util.maybe_parse_json(e.read())
            else:
                sso_error_details = None
            if sso_error_details:
                raise SSOAuthError(e, sso_error_details)
            raise util.UrlError(e, code=e.code, headers=e.hdrs, url=e.url)
        return response

    def request_user_keys(self, email):
        return self.request_url(
            API_PATH_USER_KEYS + six.moves.urllib.parse.quote(email))

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
        token_path = self.data_path('oauth')
        if os.path.exists(token_path):  # Use cached oauth token
            return json.load(util.load_file(token_path))
        if not os.path.exists(self.data_path()):
            os.makedirs(self.data_path())
        data = {'email': email, 'password': password, 'token_name': token_name}
        if otp:
            data['otp'] = otp
        content = self.request_url(API_PATH_OAUTH_TOKEN, data=data)
        util.write_file(token_path, json.dumps(content))
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
        macaroon_path = self.datapath('sso-macaroon')
        if os.path.exists(macaroon_path):  # Use cached macaroon
            return json.load(util.load_file(macaroon_path))
        if not os.path.exists(self.data_path()):
            os.makedirs(self.data_path())
        data = {'email': email, 'password': password, 'caveat_id': caveat_id}
        if otp:
            data['otp'] = otp
        content = self.request_url(API_PATH_TOKEN_DISCHARGE, data=data)
        util.write_file(macaroon_path, json.dumps(content))
        return content


def prompt_oauth_token():
    client = UbuntuSSOClient()
    oauth_token = client.read_cached_data('oauth')
    if oauth_token:
        return oauth_token
    email = six.moves.input('Email: ')
    password = getpass.getpass('Password: ')
    token_name = six.moves.input('Unique OAuth token name: ')
    try:
        oauth_token = client.request_oauth_token(
            email=email, password=password, token_name=token_name)
    except SSOAuthError as e:
        if not API_ERROR_2FA_REQUIRED in e:
            logging.error(str(e))
            return None
        otp = six.moves.input('Second-factor auth: ')
        oauth_token = client.request_oauth_token(
            email=email, password=password, token_name=token_name, otp=otp)
    return oauth_token


def prompt_request_macaroon(caveat_id=None):
    if not caveat_id:
        caveat_id='{"secret": "thesecret", "version": 1}'
    email = six.moves.input('Email: ')
    password = getpass.getpass('Password: ')
    client = UbuntuSSOClient()
    try:
        content = client.request_discharge_macaroon(
            email=email, password=password, caveat_id=caveat_id)
    except SSOAuthError as e:
        if not API_ERROR_2FA_REQUIRED in e:
            logging.error(str(e))
            return None
        otp = six.moves.input('Second-factor auth: ')
        content = client.request_discharge_macaroon(
            email=email, password=password, caveat_id=caveat_id, otp=otp)
    return content
