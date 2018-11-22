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
API_ERROR_INVALID_DATA = 'invalid-data'
API_ERROR_INVALID_CREDENTIALS = 'invalid-credentials'
API_ERROR_PASSWORD_POLICY_ERROR = 'password-policy-error'
API_ERROR_TOO_MANY_REQUESTS = 'too-many-requests'


class UrlError(IOError):

    def __init__(self, cause, code=None, headers=None, url=None):
        super(UrlError, self).__init__(str(cause))
        self.cause = cause
        self.code = code
        self.headers = headers
        if self.headers is None:
            self.headers = {}
        self.url = url


class SSOAuthError(UrlError):

    def __init__(self, e, error_response):
        super(SSOAuthError, self).__init__(e, e.code, e.headers, e.url)
        self.full_api_response = error_response
        if 'error_list' in error_response:
            self.api_errors = error_response['error_list']
        else:
            self.api_errors = [error_response]

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


def maybe_parse_json(content):
    """Attempt to parse json content.

    @return: Structured content on success and None on failure.
    """
    try:
        return json.loads(content)
    except ValueError:
        return None


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
             UrlError on unexpected url handling errors, timeouts etc
             SSOAuthError on expected SSO authentication issues
        """
        data = {'email': email, 'password': password, 'caveat_id': caveat_id}
        if otp:
            data['otp'] = otp
        try:
            response = self.request_url(API_PATH_TOKEN_DISCHARGE, data=data)
        except six.moves.urllib.error.URLError as e:
            sso_error_details = maybe_parse_json(e.read())
            if sso_error_details:
                raise SSOAuthError(e, sso_error_details)
            raise URLError(e, code=e.code, headers=e.hdrs, url=e.url)
        return response


def readurl(url, data=None, headers=None, quiet=False):
    req = six.moves.urllib.request.Request(url, data=data, headers=headers)
    if not quiet:
        logging.debug(
            'Reading url: %s, headers: %s, data: %s', url, headers, data)
    resp = six.moves.urllib.request.urlopen(req)
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
    except SSOAuthError as e:
        if not API_ERROR_2FA_REQUIRED in e:
            raise
        otp = six.moves.input('Second-factor auth: ')
    if not content:
        content = client.request_discharge_macaroon(
            email=email, password=password, caveat_id=caveat_id, otp=otp)
    return content
