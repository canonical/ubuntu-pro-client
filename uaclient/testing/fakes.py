import json

from uaclient.config import UAConfig
from uaclient.contract import UAContractClient

try:
    from typing import Any, Dict, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class FakeContractClient(UAContractClient):

    _requests = []
    _responses = {}

    def __init___(self, cfg, responses=None):
        super().__init__(cfg)
        if responses:
            self._responses = responses

    def request_url(self, path, data=None, headers=None, method=None):
        request = {
            'path': path, 'data': data, 'headers': headers, 'method': method}
        self._requests.append(request)
        # Return a response if we have one or empty
        return self._responses.get(path, {}), {'header1': ''}


class FakeConfig(UAConfig):

    def __init__(self, cache_contents: 'Dict[str, Any]' = None) -> None:
        self._cache_contents = {}
        if cache_contents:
            self._cache_contents = {
                k: json.dumps(v) for k, v in cache_contents.items()}

        super().__init__({})

    def read_cache(self, key: str, silent: bool = False) -> 'Optional[str]':
        value = self._cache_contents.get(key)
        if value:
            value = json.loads(value)
        return value

    def write_cache(
            self, key: str, content: 'Any', private: bool = True) -> None:
        content = json.dumps(content)
        if private:
            self._cache_contents[key] = content
        else:
            self._cache_contents['public-' + key] = content

    @classmethod
    def for_attached_machine(
            cls, account_name: str = 'test_account',
            machine_token: 'Dict[str, Any]' = None):
        value = {
            'machine-token': {
                'machineToken': 'not-null',
                'machineTokenInfo': {
                    'accountInfo': {'name': account_name},
                    'contractInfo': {'id': 'cid', 'name': 'test_contract',
                                     'resourceEntitlements': []}}}
        }
        if machine_token:
            value['machine-token'] = machine_token
        return cls(value)
