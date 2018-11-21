import json
import oauth
import six

from uaclient import config
import logging


API_PATH_V2 = '/api/v2'
API_PATH_USER_KEYS = API_PATH_V2 + '/keys/'
API_PATH_TOKEN_DISCHARGE = API_PATH_V2 + '/tokens/discharge'
API_PATH_TOKEN_REFRESH = API_PATH_V2 + '/tokens/refresh'


API_ERROR_2FA_REQUIRED = 'twofactor-required'
API_ERROR_2FA_FAILURE = 'twofactor-failure'
API_ERROR_ACCOUNT_DEACTIVATED = 'account-deactivated'
API_ERROR_ACCOUNT_SUSPENDED = 'account-suspended'
API_ERROR_EMAIL_INVALIDATED = 'email-invalidated'
API_ERROR_INVALID_CREDENTIALS = 'invalid-credentials'
API_ERROR_PASSWORD_POLICY_ERROR = 'password-policy-error'
API_ERROR_TOO_MANY_REQUESTS = 'too-many-requests'


class SSOAuthError(six.moves.urllib.error.URLError):
    pass


class SSOAuthMissingOTPError(SSOAuthError):
    pass


class UbuntuSSOAPIErrors(object):
    """Optional Ubuntu SSO detailed error response."""

    def __init__(self, error_response):
        try:
            parsed_response = json.loads(error_response)
        except ValueError:
            parsed_response = {}
        self.errors = parsed_response.get('error_list', [])

    def __str__(self):
        if not self.errors:
            return ''
        return 'SSO API errors: ' + ', '.join(
            ['%s:%s' % (error['code'], error['message'])
             for error in self.errors])

    def __contains__(self, error_code):
        return error_code in self.codes()

    def __get__(self, error_code, default=None):
        for error in self.errors:
            if error['code'] == error_code:
                return error['message']
        return default

    def codes(self):
        return [error['code'] for error in self.errors]

    def messages(self):
        return [error['message'] for error in self.errors]


class UbuntuSSOClient(object):

    def __init__(self, base_url=None):
        if not base_url:
            base_url = config.parse_config()['sso_auth_url']
        self.base_url = base_url

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
            data = json.dumps(data).encode('utf-8')
        url = self.base_url + path
        return readurl(url=url, data=data, headers=headers)

    def get_user_keys(self, email):
        return self.request_url(
            API_PATH_USER_KEYS + six.moves.urllib.parse.quote(email))

    def request_discharge_macaroon(self, email, password, caveat_id, otp=None):
        """Request a discharge macaroon for the authenticated user

        @param email: String with the email address of the SSO account holder.
        @param password: String with the password of the SSO account holder.
        @param caveat_id: String with the macaroon caveat ID obtained from
            subscription service.

        @return: the response from the SSO service for a macaroon request.

        @raises:
             SSOMissingOTPError when authenticate requires otp
             SSOInvalidCredentials on invalid email, password or otp
             SSOError for unexcected SSO Authentication issues
        """
        data = {'email': email, 'password': password, 'caveat_id': caveat_id}
        if otp:
            data['otp'] = otp
        try:
            response = self.request_url(API_PATH_TOKEN_DISCHARGE, data=data)
        except six.moves.urllib.error.URLError as e:
            import pdb; pdb.set_trace()
            if e.code in (401, 403):
                if API_ERROR_2FA_REQUIRED in e.api_errors:
                    msg = (
                        "Missing Two factor authentication for '%s'" % email)
                    raise SSOAuthMissingOTPError(msg)
            msg = 'Unexpected SSO error: [%s] %s' % (e.code, e)
            raise SSOAuthError(msg)
        return


def readurl(url, data=None, headers=None):
    req = six.moves.urllib.request.Request(url, data=data, headers=headers)
    logging.debug(
       'Reading url: %s, headers: %s, data: %s', url, headers, data)
    try:
        resp = six.moves.urllib.request.urlopen(req)
    except six.moves.urllib.error.URLError as e:
        e.api_errors = UbuntuSSOAPIErrors(e.read())
        logging.error('URLError: %s %s', e, e.api_errors)
        raise
    content = config.decode_binary(resp.read())
    if 'application/json' in resp.headers.get('Content-type', ''):
        content = json.loads(content)
    return content


def prompt_request_macaroon(caveat_id=None):
    content = None
    if not caveat_id:
        caveat_id='{"secret": "thesecret", "version": 1}'
    email = six.moves.input('Email: ')
    password = six.moves.input('Password: ')
    client = UbuntuSSOClient()
    try:
        content = client.request_discharge_macaroon(
            email=email, password=password, caveat_id=caveat_id)
    except SSOAuthMissingOTPError as e:
        otp = six.moves.input('Second-factor auth: ')
    if not content:
        try:
            content = client.request_discharge_macaroon(
                email=email, password=password, caveat_id=caveat_id, otp=otp)
        except SSOAuthError as e:
            import pdb; pdb.set_trace()
    return content
