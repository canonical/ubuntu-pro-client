import json

from uaclient.config import UAConfig
from uaclient.contract import UAContractClient
from uaclient.util import DatetimeAwareJSONDecoder, DatetimeAwareJSONEncoder

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
            "path": path,
            "data": data,
            "headers": headers,
            "method": method,
        }
        self._requests.append(request)
        # Return a response if we have one or empty
        response = self._responses.get(path, {})
        if isinstance(response, Exception):
            raise response
        return response, {"header1": ""}


class FakeConfig(UAConfig):
    def __init__(self, cache_contents: "Dict[str, Any]" = None) -> None:
        self._cache_contents = {}
        if cache_contents:
            self._cache_contents = {
                k: json.dumps(v, cls=DatetimeAwareJSONEncoder)
                for k, v in cache_contents.items()
            }

        super().__init__({})

    def _perform_delete(self, cache_path: str) -> None:
        pass

    def delete_cache_key(self, key: str) -> None:
        super().delete_cache_key(key)
        if key in self._cache_contents:
            del self._cache_contents[key]

    def read_cache(self, key: str, silent: bool = False) -> "Optional[str]":
        value = self._cache_contents.get(key)
        if value:
            value = json.loads(value, cls=DatetimeAwareJSONDecoder)
        return value

    def write_cache(
        self, key: str, content: "Any", private: bool = True
    ) -> None:
        content = json.dumps(content, cls=DatetimeAwareJSONEncoder)
        if private:
            self._cache_contents[key] = content
        else:
            self._cache_contents["public-" + key] = content

    @classmethod
    def for_attached_machine(
        cls,
        account_name: str = "test_account",
        machine_token: "Dict[str, Any]" = None,
    ):
        value = {
            "machine-token": {
                "machineToken": "not-null",
                "machineTokenInfo": {
                    "accountInfo": {"id": "acct-1", "name": account_name},
                    "contractInfo": {
                        "id": "cid",
                        "name": "test_contract",
                        "resourceEntitlements": [],
                    },
                },
            }
        }
        if machine_token:
            value["machine-token"] = machine_token
        return cls(value)
