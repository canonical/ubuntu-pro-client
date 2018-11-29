import getpass
import json
import os
import six

from uaclient import config
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


class UAServiceClient(object):

    # Set in subclasses to the config key referenced by this client
    service_url_cfg_key = None

    # Set in subclasses to define any cached data files stored by this class
    data_paths = {}

    def __init__(self, cfg=None):
        if not cfg:
            self.cfg = config.parse_config()
        else:
            self.cfg = cfg

    def data_path(self, key):
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


class UAContractClient(UAServiceClient):

    service_url_cfg_key = 'contract_url'

    data_paths = {'machine-token': 'machine-token.json', 'status': 'entitlement-satus.json'}

    def request_url(self, path, data=None, headers=None):
        if path[0] != '/':
            path = '/' + path
        if not headers:
            headers=self.headers()
        if headers.get('content-type') == 'application/json' and data:
            data = util.encode_text(json.dumps(data))
        url = self.cfg[self.service_url_cfg_key] + path
        try:
            response = util.readurl(url=url, data=data, headers=headers)
        except six.moves.urllib.error.URLError as e:
            code = e.errno
            if hasattr(e, 'read'):
                error_details = util.maybe_parse_json(e.read())
                if error_details:
                    raise ContractAPIError(e, error_details)
            raise util.UrlError(e, code=code, headers=headers, url=url)
        return response

    def request_status(self, machine_token, machine_id=None):
        """Request entitlement status details for a given machine.

        @return: Dict of JSON reposnse from entitlements endpoint
        """
        if not machine_id:
            machine_id = util.load_file('/etc/machine-id')
        data = {'machine-token': machine_token, 'machine-id': machine_id}
        entitlement_status = self.request_url(
            API_PATH_MACHINE_STATUS, data=data)
        util.write_file(
            self.data_path('status'), json.dumps(entitlement_status))
        return entitlement_status

    def request_machine_attach(self, user_token, machine_id=None):
        """Requests machine attach from Contract service.

        @return: Dict of the JSON response containing the machine-token.
        """
        machine_token = self.read_cached_data('machine-token')
        if machine_token:
            return machine_token
        if not machine_id:
            machine_id = util.load_file('/etc/machine-id')
        data = {'user-token': user_token, 'machine-id': machine_id}
        machine_token = self.request_url(API_PATH_MACHINE_ATTACH, data=data)
        util.write_file(
            self.data_path('machine-token'), json.dumps(machine_token))
        return machine_token
