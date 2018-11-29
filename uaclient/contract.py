import getpass
import json
import os
import six

from uaclient import config
from uaclient import util
import logging


API_PATH_MACHINE_ATTACH = '/contract/machine/attach'


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




class UAServiceClient(object):

    # Set in subclasses to the config key referenced by this client
    service_url_cfg_key = None

    def __init__(self, cfg=None):
        if not cfg:
            self.cfg = config.parse_config()
        else:
            self.cfg = cfg

    def headers(self):
        return {'user-agent': 'UA-Client/%s' % config.get_version(),
                'accept': 'application/json',
                'content-type': 'application/json'}


class UAContractClient(UAServiceClient):

    service_url_cfg_key = 'contract_url'

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
                    raise SSOAuthError(e, error_details)
            raise util.UrlError(e, code=code, headers=headers, url=url)
        return response

    def request_machine_attach(self, user_token, machine_id=None):
        """Requests machine attach from Contract service.

        @return: Dict of the JSON response containing the machine-token.
        """
        data_dir = self.cfg['data_dir']
        token_path = os.path.join(data_dir, 'machine-token.json')
        if os.path.exists(token_path):  # Use cached token
            return util.load_file(token_path)
        if not machine_id:
            machine_id = util.load_file('/etc/machine-id')
        data = {'user-token': user_token, 'machine-id': machine_id}
        return self.request_url(API_PATH_MACHINE_ATTACH, data=data)
