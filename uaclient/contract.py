from uaclient import serviceclient
from uaclient import util


API_PATH_ACCOUNTS = '/accounts'
API_PATH_TMPL_ACCOUNT_CONTRACTS = '/accounts/{account}/contracts'
API_PATH_TMPL_ACCOUNT_USERS = '/accounts/{account}/users'
API_PATH_TMPL_CONTRACT_MACHINES = '/contracts/{contract}/context/machines'
API_PATH_TMPL_MACHINE_CONTRACT = '/machines/{machine}/contract'
API_PATH_TMPL_RESOURCE_MACHINE_ACCESS = '/resources/{resource}/context/machine'

# API Errors for Contract service
API_ERROR_INVALID_DATA = 'BAD REQUEST'

# TODO(Add bearer token route handshake once contract service defines it)


class ContractAPIError(util.UrlError):

    def __init__(self, e, error_response):
        super(ContractAPIError, self).__init__(e, e.code, e.headers, e.url)
        self.full_api_response = error_response
        if 'error_list' in error_response:
            self.api_errors = error_response['error_list']
        else:
            self.api_errors = [error_response]
        for error in self.api_errors:
            error['code'] = error['title']

    def __contains__(self, error_code):
        return error_code in [error['code'] for error in self.api_errors]

    def __get__(self, error_code, default=None):
        for error in self.api_errors:
            if error['code'] == error_code:
                return error['detail']
        return default

    def __str__(self):
        prefix = super(ContractAPIError, self).__str__()
        details = []
        for err in self.api_errors:
            if not err.get('extra'):
                details.append(err['detail'])
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

    def request_accounts(self):
        """Request list of accounts this user has access to."""
        accounts = self.cfg.read_cache('accounts')
        if accounts:
            return accounts
        accounts = self.request_url(API_PATH_ACCOUNTS)
        self.cfg.write_cache('accounts', accounts)
        return accounts

    def request_account_contracts(self, account_id):
        """Request a list of contracts authorized for account_id."""
        account_contracts = self.cfg.read_cache('account-contracts')
        if account_contracts:
            return account_contracts
        url = API_PATH_TMPL_ACCOUNT_CONTRACTS.format(account=account_id)
        account_contracts = self.request_url(url)
        self.cfg.write_cache('account-contracts', account_contracts)
        return account_contracts

    def request_account_users(self, account_id):
        """Request a list of users authorized for account_id."""
        account_users = self.cfg.read_cache('account-users')
        if account_users:
            return account_users
        url = API_PATH_TMPL_ACCOUNT_USERS.format(account=account_id)
        account_users = self.request_url(url)
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
            machine_id = util.load_file('/etc/machine-id')
        data = {'machine': machine_id}
        if product_name:
            data['product'] = product_name
        url = API_PATH_TMPL_MACHINE_CONTRACT.format(
            machine=contract_machine_id)
        contracts = self.request_url(url, data=data)
        self.cfg.write_cache('machine-contracts', contracts)
        return contracts

    def request_contract_machine_attach(self, contract_id, user_token,
                                        machine_id=None):
        """Requests machine attach to the provided contact_id.

        @param contract_id: Unique contract id provided by contract service.
        @param user_token: Token string providing authentication to contract
            service endpoints.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing the machine-token.
        """
        token_response = self.cfg.read_cache('machine-token')
        if token_response:
            return token_response
        if not machine_id:
            machine_id = util.load_file('/etc/machine-id')
        os = util.get_platform_info()
        arch = os.pop('arch')
        data = {'machineId': machine_id, 'arch': arch, 'os': os}
        machine_token = self.request_url(
            API_PATH_TMPL_CONTRACT_MACHINES.format(contract=contract_id),
            data=data)
        self.cfg.write_cache('machine-token', machine_token)
        return machine_token

    def request_contract_machine_detach(self, contract_id, user_token):
        """Requests machine detach from the provided contact_id.

        @param contract_id: Unique contract id provided by contract service.
        @param user_token: Token string providing authentication to contract
            service endpoints.

        @return: Dict of the JSON response containing the machine-token.
        """
        machine_token = self.request_url(
            API_PATH_TMPL_CONTRACT_MACHINES.format(contract=contract_id),
            method='DELETE')
        self.cfg.write_cache('machine-detach', machine_token)
        return machine_token

    def request_resource_machine_access(self, machine_token, resource):
        """Requests machine access context for a given resource

        @param machine_token: The authentication token needed to talk to
            this contract service endpoint.
        @param resource: Entitlement name. One of: livepatch, esm, fips or
            fips-updates.

        @return: Dict of the JSON response containing entitlement accessInfo.
        """
        url = API_PATH_TMPL_RESOURCE_MACHINE_ACCESS.format(resource=resource)
        resource_access = self.request_url(url)
        self.cfg.write_cache('machine-access-%s' % resource, resource_access)
        return resource_access
