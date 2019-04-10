import logging

from uaclient import serviceclient
from uaclient import util


API_PATH_TMPL_ACCOUNT_USERS = '/accounts/{account}/users'
API_PATH_TMPL_CONTRACT_MACHINES = '/contracts/{contract}/context/machines'
API_PATH_TMPL_MACHINE_CONTRACT = '/machines/{machine}/contract'
API_PATH_TMPL_RESOURCE_MACHINE_ACCESS = '/resources/{resource}/context/machine'

API_V1_ACCOUNTS = '/v1/accounts'
API_V1_TMPL_ACCOUNT_CONTRACTS = '/v1/accounts/{account}/contracts'
API_V1_TMPL_ADD_CONTRACT_TOKEN = '/v1/contracts/{contract}/token'
API_V1_CONTEXT_MACHINE_TOKEN = '/v1/context/machines/token'
API_V1_SSO_MACAROON = '/v1/canonical-sso-macaroon'
API_V1_TMPL_RESOURCE_MACHINE_ACCESS = (
    '/v1/resources/{resource}/context/machines/{machine}')

# API Errors for Contract service
API_ERROR_INVALID_DATA = 'BAD REQUEST'

# TODO(Add bearer token route handshake once contract service defines it)


class ContractAPIError(util.UrlError):

    def __init__(self, e, error_response):
        super().__init__(e, e.code, e.headers, e.url)
        self.full_api_response = error_response
        if 'error_list' in error_response:
            self.api_errors = error_response['error_list']
        else:
            self.api_errors = [error_response]
        for error in self.api_errors:
            error['code'] = error.get('title', error.get('code'))

    def __contains__(self, error_code):
        return error_code in [error['code'] for error in self.api_errors]

    def __get__(self, error_code, default=None):
        for error in self.api_errors:
            if error['code'] == error_code:
                return error['detail']
        return default

    def __str__(self):
        prefix = super().__str__()
        details = []
        for err in self.api_errors:
            if not err.get('extra'):
                details.append(err.get('detail', err.get('message', '')))
            else:
                for extra in err['extra'].values():
                    if isinstance(extra, list):
                        details.extend(extra)
                    else:
                        details.append(extra)
        return prefix + ': [' + self.url + ']' + ', '.join(details)


class UAContractClient(serviceclient.UAServiceClient):

    cfg_url_base_attr = 'contract_url'
    api_error_cls = ContractAPIError

    def request_root_macaroon(self):
        """Request root macaroon with 3rd party caveat for Ubuntu SSO."""
        root_macaroon, _headers = self.request_url(API_V1_SSO_MACAROON)
        self.cfg.write_cache('root-macaroon', root_macaroon)
        return root_macaroon

    def request_accounts(self, macaroon_token=None, machine_token=None):
        """Request list of accounts this user has access to."""
        headers = self.headers()
        if macaroon_token:
            headers.update({'Authorization': 'Macaroon %s' % macaroon_token})
        else:
            headers.update({'Authorization': 'Bearer %s' % machine_token})
        accounts, _headers = self.request_url(
            API_V1_ACCOUNTS, headers=headers)
        self.cfg.write_cache('accounts', accounts)
        return accounts

    def request_account_contracts(
            self, account_id, macaroon_token=None, machine_token=None):
        """Request a list of contracts authorized for account_id."""
        url = API_V1_TMPL_ACCOUNT_CONTRACTS.format(account=account_id)
        headers = self.headers()
        if macaroon_token:
            headers.update({'Authorization': 'Macaroon %s' % macaroon_token})
        else:
            headers.update({'Authorization': 'Bearer %s' % machine_token})
        account_contracts, _headers = self.request_url(url, headers=headers)
        self.cfg.write_cache('account-contracts', account_contracts)
        return account_contracts

    def request_add_contract_token(
            self, contract_id, macaroon_token=None, machine_token=None):
        """Create a contract token for use when adding a machine to a contract

        """
        headers = self.headers()
        if macaroon_token:
            headers.update({'Authorization': 'Macaroon %s' % macaroon_token})
        else:
            headers.update({'Authorization': 'Bearer %s' % machine_token})
        url = API_V1_TMPL_ADD_CONTRACT_TOKEN.format(contract=contract_id)
        contract_token, _headers = self.request_url(
            url, headers=headers,
            data={"TODO": "any other request body params?"})
        self.cfg.write_cache('contract-token', contract_token)
        return contract_token

    def request_account_users(self, account_id):
        """Request a list of users authorized for account_id."""
        url = API_PATH_TMPL_ACCOUNT_USERS.format(account=account_id)
        account_users, _headers = self.request_url(url)
        self.cfg.write_cache('account-users', account_users)
        return account_users

    def request_machine_contract_status(
            self, machine_token, contract_machine_id, machine_id=None,
            product_name=None):
        """Request contract and entitlement status details for a given machine.

        @param machine_token: The authentication token needed to talk to
            the contract service endpoints.
        @param contract_machine_id: The machine id obtained from the contract
            service.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.
        @param product_name: Optional specific product name to limit query to
            a specific entitlement: livepatch, esm, fips, or fips-updates.

        @return: Dict of JSON response from machine contracts endpoint
        """
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg.data_dir)
        data = {'machine': machine_id}
        if product_name:
            data['product'] = product_name
        url = API_PATH_TMPL_MACHINE_CONTRACT.format(
            machine=contract_machine_id)
        contracts, _headers = self.request_url(url, data=data)
        self.cfg.write_cache('machine-contracts', contracts)
        return contracts

    def request_contract_machine_attach(self, contract_token, machine_id=None):
        """Requests machine attach to the provided contact_id.

        @param contract_id: Unique contract id provided by contract service.
        @param contract_token: Token string providing authentication to
            ContractBearer service endpoint.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing the machine-token.
        """
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg.data_dir)
        os = util.get_platform_info()
        arch = os.pop('arch')
        headers = self.headers()
        headers.update({'Authorization': 'Bearer %s' % contract_token})
        data = {'machineId': machine_id, 'architecture': arch, 'os': os}
        machine_token, _headers = self.request_url(
            API_V1_CONTEXT_MACHINE_TOKEN, data=data, headers=headers)
        self.cfg.write_cache('machine-token', machine_token)
        redacted_content = redact_sensitive(machine_token)
        self.cfg.write_cache('machine-token', redacted_content, private=False)
        return machine_token

    def request_contract_machine_detach(self, contract_id, user_token):
        """Requests machine detach from the provided contact_id.

        @param contract_id: Unique contract id provided by contract service.
        @param user_token: Token string providing authentication to contract
            service endpoints.

        @return: Dict of the JSON response containing the machine-token.
        """
        machine_token, _headers = self.request_url(
            API_PATH_TMPL_CONTRACT_MACHINES.format(contract=contract_id),
            method='DELETE')
        self.cfg.write_cache('machine-detach', machine_token)
        return machine_token

    def request_resource_machine_access(
            self, machine_token, resource, machine_id=None):
        """Requests machine access context for a given resource

        @param machine_token: The authentication token needed to talk to
            this contract service endpoint.
        @param resource: Entitlement name. One of: livepatch, esm, fips or
            fips-updates.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing entitlement accessInfo.
        """
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg.data_dir)
        headers = self.headers()
        headers.update({'Authorization': 'Bearer %s' % machine_token})
        url = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
            resource=resource, machine=machine_id)
        resource_access, headers = self.request_url(url, headers=headers)
        if headers.get('expires'):
            resource_access['expires'] = headers['expires']
        self.cfg.write_cache('machine-access-%s' % resource, resource_access)
        redacted_content = redact_sensitive(resource_access)
        self.cfg.write_cache(
            'machine-access-%s' % resource, redacted_content, private=False)
        return resource_access


def get_contract_token_for_account(
        contract_client, account_id, macaroon_token=None, machine_token=None):
    """Obtain a contract token for the account_id using the contract_client.

    @raises: SSOAuthError on auth failure or util.UrlError on connection
             failure.
    """
    contract_client.request_accounts(
        macaroon_token=macaroon_token, machine_token=machine_token)
    contracts = contract_client.request_account_contracts(
        account_id, macaroon_token=macaroon_token, machine_token=machine_token)
    contract_id = contracts['contracts'][0]['contractInfo']['id']
    contract_token_response = contract_client.request_add_contract_token(
        contract_id, macaroon_token=macaroon_token,
        machine_token=machine_token)
    return contract_token_response['contractToken']


def redact_sensitive(contract_response):
    """Redact security-sensitive content from contract_response dict."""
    redacted = {}
    for key, value in contract_response.items():
        if key in util.SENSITIVE_KEYS:
            redacted[key] = '<REDACTED>'
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted


def request_contract_updates(cfg, contract_token):
    """Request contract updates from ua-contracts service.

    @param cfg: Instance of UAConfig for this machine.
    @param contract_token: Token of the contract we are updating.

    @return: True on success False otherwise.
    """
    contract_client = UAContractClient(cfg)
    if not contract_token:  # Crawl the accounts contract routes to get details
        machine_token = cfg.machine_token['machineToken']
        try:
            contract_client.request_accounts(machine_token=machine_token)
            contract_token = get_contract_token_for_account(
                contract_client, cfg.accounts[0]['id'],
                machine_token=machine_token)
        except util.UrlError as e:
            logging.error(str(e))
            print('Could not update contract info from %s' %
                  cfg.contract_url)
            return False
    try:
        token_response = contract_client.request_contract_machine_attach(
            contract_token=contract_token)
        contractInfo = token_response['machineTokenInfo']['contractInfo']
        for entitlement in contractInfo['resourceEntitlements']:
            if entitlement.get('entitled'):
                # Obtain each entitlement's accessContext for this machine
                entitlement_name = entitlement['type']
                contract_client.request_resource_machine_access(
                    cfg.machine_token['machineToken'], entitlement_name)
    except util.UrlError as e:
        logging.error(
            'Could not obtain updated contract information. %s', str(e))
        return False
    return True
