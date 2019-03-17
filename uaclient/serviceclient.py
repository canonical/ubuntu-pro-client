import json
from urllib import error

from uaclient import config
from uaclient import util


class UAServiceClient(object):

    # Set in subclasses to the config key referenced by this client
    service_url_cfg_key = None

    # Set in subclasses to the type of API error raised
    api_error_cls = None

    # String in subclasses to the UAConfig attribute accessed to get base url
    cfg_url_base_attr = None

    def __init__(self, cfg=None):
        if not cfg:
            self.cfg = config.UAConfig()
        else:
            self.cfg = cfg

    def headers(self):
        return {'user-agent': 'UA-Client/%s' % config.get_version(),
                'accept': 'application/json',
                'content-type': 'application/json'}

    def request_url(self, path, data=None, headers=None, method=None):
        if path[0] != '/':
            path = '/' + path
        if not headers:
            headers = self.headers()
        if headers.get('content-type') == 'application/json' and data:
            data = util.encode_text(json.dumps(data))
        url = getattr(self.cfg, self.cfg_url_base_attr) + path
        try:
            response, headers = util.readurl(
                url=url, data=data, headers=headers, method=method)
        except error.URLError as e:
            code = e.errno
            if hasattr(e, 'read'):
                error_details = util.maybe_parse_json(e.read())
                if error_details:
                    raise self.api_error_cls(e, error_details)
            raise util.UrlError(e, code=code, headers=headers, url=url)
        return response, headers
