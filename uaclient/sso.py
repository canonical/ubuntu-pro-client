import base64
import getpass
import json
import logging
import pymacaroons
from urllib import parse

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


class MacaroonFormatError(RuntimeError):
    pass


class InvalidRootMacaroonError(MacaroonFormatError):
    """Raised when root macaroon is not parseable"""
    pass


class NoThirdPartySSOCaveatFoundError(MacaroonFormatError):
    """Raised when valid Macaroon is found but missing SSO caveat"""
    pass


class SSOAuthError(util.UrlError):

    def __init__(self, e, error_response):
        super().__init__(e, e.code, e.headers, e.url)
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
        prefix = super().__str__()
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
            API_PATH_USER_KEYS + parse.quote(email))
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


def binary_serialize_macaroons(macaroons):
    """Encode all serialized macaroons and concatonate as a serialize bytes

    @param macaroons: Iterable of macaroons lead by root_macaroon as first
       element followed by any discharge macaroons to serialize
    """
    serialized_macaroons = []
    for macaroon in macaroons:
        serialized = macaroon.serialize()
        if '_' or '-' in serialized:
            encoded = serialized.encode('utf-8')
            padded = encoded + b'=' * (-len(encoded) % 4)
            serialized_macaroons.append(base64.urlsafe_b64decode(padded))
        else:
            padded = serialized + b'=' * (-len(serialized) % 4)
            serialized_macaroons.append(base64.b64decode(padded))
    return base64.urlsafe_b64encode(
        b''.join(serialized_macaroons)).rstrip(b'=')


def extract_macaroon_caveat_id(macaroon):
    """Extract the macaroon caveat_id for interaction with Ubuntu SSO

    @param macaroon: Base64 encoded macaroon string

    @return: caveat_id
    @raises: NoThirdPartySSOCaveatFoundError on missing login.ubuntu.com caveat
             InvalidRootMacaroonError on inability to parse macaroon
    """
    padded_macaroon = macaroon + '=' * (len(macaroon) % 3)
    try:
        root_macaroon = pymacaroons.Macaroon.deserialize(padded_macaroon)
        caveat_id_by_location = dict(
            (c.location, c.caveat_id)
            for c in root_macaroon.third_party_caveats())
    except Exception as e:
        raise InvalidRootMacaroonError("Invalid root macaroon. %s" % e)
    if 'login.ubuntu.com' in caveat_id_by_location:
        return caveat_id_by_location['login.ubuntu.com']
    raise NoThirdPartySSOCaveatFoundError(
        'Missing login.ubuntu.com 3rd party caveat. Found caveats: %s' %
        caveat_id_by_location.keys())


def bind_discharge_macarooon_to_root_macaroon(discharge_mac, root_mac):
    """Bind discharge macaroon to root macaroon.

     The resulting bound macaroons is uses for SSOAuth against UA Contract
     routes.

     @param discharge_macaroon: The discharge macaroon from Login Ubuntu SSO
     @param root_macaroon: The root macaroon from UA Contract Service

     @return: The seriealized root_macaroon with the bound discharge macaroon.
     """
    padded_root = root_mac + '=' * (-len(root_mac) % 4)
    discharge_mac = pymacaroons.Macaroon.deserialize(discharge_mac)
    root_mac = pymacaroons.Macaroon.deserialize(padded_root)
    bound_mac = root_mac.prepare_for_request(discharge_mac)
    serialized_macaroons = binary_serialize_macaroons([root_mac, bound_mac])
    return serialized_macaroons


def prompt_request_macaroon(cfg, caveat_id):
    discharge_macaroon = cfg.read_cache('macaroon')
    if discharge_macaroon:
        # TODO(invalidate cached macaroon on root-macaroon or discharge expiry)
        return discharge_macaroon
    email = input('Email: ')
    password = getpass.getpass('Password: ')
    args = {'email': email, 'password': password, 'caveat_id': caveat_id}
    sso_client = UbuntuSSOClient(cfg)
    content = None
    while True:
        try:
            content = sso_client.request_discharge_macaroon(**args)
        except SSOAuthError as e:
            if API_ERROR_2FA_REQUIRED not in e:
                logging.error(str(e))
                break
            args['otp'] = input('Second-factor auth: ')
        if content:
            return content
    return None


def discharge_root_macaroon(contract_client):
    """Prompt for SSO authentication to create an discharge macaroon from SSO

    Extract contract client's root_macaroon caveat for login.ubuntu.com and
    prompt authentication to SSO to provide a discharge macaroon. Bind that
    discharge macaroon to the root macaroon to provide an authentication
    token for accessing authenticated UA Contract routes.

    @param contract_client: UAContractClient instance for talking to contract
        service routes.

    @return: The serialized bound root macaroon or None upon error.
    """
    cfg = contract_client.cfg
    try:
        root_macaroon = contract_client.request_root_macaroon()
        caveat_id = extract_macaroon_caveat_id(root_macaroon['macaroon'])
        discharge_macaroon = prompt_request_macaroon(cfg, caveat_id)
    except (util.UrlError) as e:
        logging.error("Could not reach url '%s' to authenticate.", e.url)
        return None
    except (MacaroonFormatError) as e:
        logging.error("Invalid root macaroon: %s", str(e))

    if not discharge_macaroon:
        return None
    return bind_discharge_macarooon_to_root_macaroon(
        discharge_macaroon['discharge_macaroon'], root_macaroon['macaroon'])


def prompt_oauth_token(cfg):
    client = UbuntuSSOClient(cfg)
    oauth_token = client.cfg.read_cache('oauth')
    if oauth_token:
        return oauth_token
    try:
        email = input('Email: ')
        password = getpass.getpass('Password: ')
        token_name = input('Unique OAuth token name: ')
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
            otp = input('Second-factor auth: ')
        except KeyboardInterrupt:
            return None
        oauth_token = client.request_oauth_token(
            email=email, password=password, token_name=token_name, otp=otp)
    return oauth_token
