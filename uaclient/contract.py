import getpass
import json
import os
import six

from uaclient import config
from uaclient import serviceclient
from uaclient import util
import logging


API_PATH_MACHINE_ATTACH = '/contract/machine/attach'
API_PATH_MACHINE_STATUS = '/account/machine/entitlements'

# API Errors for Contract service
API_ERROR_INVALID_DATA = 'BAD REQUEST'


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

    def request_status(self, machine_token, machine_id=None):
        """Request entitlement status details for a given machine.

        @return: Dict of JSON reposnse from entitlements endpoint
        """
        if not machine_id:
            machine_id = util.load_file('/etc/machine-id')
        data = {'machine-token': machine_token, 'machine-id': machine_id}
        entitlement_status = self.request_url(
            API_PATH_MACHINE_STATUS, data=data)
        self.cfg.write_cache('entitlements', json.dumps(entitlement_status))
        return entitlement_status

    def request_machine_attach(self, user_token, machine_id=None):
        """Requests machine attach from Contract service.

        @return: Dict of the JSON response containing the machine-token.
        """
        token_response = self.cfg.read_cache('machine-token')
        if token_response:
            return token_response
        if not machine_id:
            machine_id = util.load_file('/etc/machine-id')
        data = {'user-token': user_token, 'machine-id': machine_id}
        machine_token = self.request_url(API_PATH_MACHINE_ATTACH, data=data)
        self.cfg.write_cache('machine-token', json.dumps(machine_token))
        return machine_token
