import base64
import getpass
import json

import pymacaroons

from uaclient import exceptions
from uaclient import serviceclient
from uaclient import util
from uaclient.config import UAConfig
from uaclient.contract import UAContractClient


API_PATH_V2 = '/api/v2'
API_PATH_TOKEN_DISCHARGE = API_PATH_V2 + '/tokens/discharge'


# Some Ubuntu SSO API responses use UNDERSCORE_DELIMITED codes, others use
# lowercase-hyphenated. We'll standardize on lowercase-hyphenated
API_ERROR_2FA_REQUIRED = 'twofactor-required'
API_ERROR_INVALID_CREDENTIALS = 'invalid-credentials'
TWOFACTOR_RETRIES = 1  # Number of times we allow retyping on failed 2FA


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
        if 'error_list' in error_response:
            self.api_errors = error_response['error_list']
        else:
            self.api_errors = [error_response]
        # Convert old api error codes from ERROR_CODE to error-code
        for error in self.api_errors:
            error['code'] = error['code'].lower().replace('_', '-')

    def __contains__(self, error_code):
        return error_code in [error['code'] for error in self.api_errors]

    def __getitem__(self, error_code, default=None):
        for error in self.api_errors:
            if error['code'] == error_code:
                return error['message']
        return default

    def __str__(self):
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
        return ', '.join(details)


class UbuntuSSOClient(serviceclient.UAServiceClient):

    api_error_cls = SSOAuthError
    cfg_url_base_attr = 'sso_auth_url'

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


def binary_serialize_macaroons(macaroons) -> bytes:
    """Encode all serialized macaroons and concatonate as a serialize bytes

    @param macaroons: Iterable of macaroons lead by root_macaroon as first
       element followed by any discharge macaroons to serialize
    """
    serialized_macaroons = []
    for macaroon in macaroons:
        serialized = macaroon.serialize()
        encoded = serialized.encode('utf-8')
        padded = encoded + b'=' * (-len(encoded) % 4)
        serialized_macaroons.append(base64.urlsafe_b64decode(padded))
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
        raise InvalidRootMacaroonError(str(e))
    if 'login.ubuntu.com' in caveat_id_by_location:
        return caveat_id_by_location['login.ubuntu.com']
    raise NoThirdPartySSOCaveatFoundError(
        'Missing login.ubuntu.com 3rd party caveat. Found caveats: %s' %
        caveat_id_by_location.keys())


def bind_discharge_macarooon_to_root_macaroon(
        discharge_mac, root_mac) -> bytes:
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


def prompt_request_macaroon(cfg: UAConfig, caveat_id: str) -> dict:
    discharge_macaroon = cfg.read_cache('macaroon')
    if discharge_macaroon:
        # TODO(invalidate cached macaroon on root-macaroon or discharge expiry)
        return discharge_macaroon
    email = input('Email: ')
    password = getpass.getpass('Password: ')
    args = {'email': email, 'password': password, 'caveat_id': caveat_id}
    sso_client = UbuntuSSOClient(cfg)
    content = None
    twofactor_retries = 0
    while True:
        try:
            content = sso_client.request_discharge_macaroon(**args)
        except SSOAuthError as e:
            if API_ERROR_2FA_REQUIRED in e:
                args['otp'] = input('Second-factor auth: ')
                continue
            elif API_ERROR_INVALID_CREDENTIALS in e:
                # This is arguably bug in canonical-identity-provider code
                # that the error 'code' is 'invalid-credentials' when docs
                # clearly designates a 'twofactor-error' code that should be
                # emitted when the 2FA token is invalid. There are no plans for
                # changes to the error codes or messages as it might break
                # existing clients. As a result, we have to distinguish
                # email/password invalid-credentials errors from 2-factor
                # errors by searching the attached error 'message' field for
                # 2-factor.
                if '2-factor' in e[API_ERROR_INVALID_CREDENTIALS]:
                    if twofactor_retries < TWOFACTOR_RETRIES:
                        args['otp'] = input(
                            'Invalid second-factor auth, try again: ')
                        twofactor_retries += 1
                        continue
            raise exceptions.UserFacingError(str(e))
        break
    if not content:
        raise exceptions.UserFacingError('SSO server returned empty content')
    return content


def discharge_root_macaroon(contract_client: UAContractClient) -> bytes:
    """Prompt for SSO authentication to create an discharge macaroon from SSO

    Extract contract client's root_macaroon caveat for login.ubuntu.com and
    prompt authentication to SSO to provide a discharge macaroon. Bind that
    discharge macaroon to the root macaroon to provide an authentication
    token for accessing authenticated UA Contract routes.

    @param contract_client: UAContractClient instance for talking to contract
        service routes.

    @return: The serialized bound root macaroon
    """
    cfg = contract_client.cfg
    try:
        root_macaroon = contract_client.request_root_macaroon()
        caveat_id = extract_macaroon_caveat_id(root_macaroon['macaroon'])
        discharge_macaroon = prompt_request_macaroon(cfg, caveat_id)
    except (util.UrlError) as e:
        raise exceptions.UserFacingError(
            'Could not reach URL {} to authenticate'.format(e.url))
    except (MacaroonFormatError) as e:
        raise exceptions.UserFacingError('Invalid root macaroon: {}'.format(e))

    return bind_discharge_macarooon_to_root_macaroon(
        discharge_macaroon['discharge_macaroon'], root_macaroon['macaroon'])
