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
    def __init__(self, data_dir: str) -> None:
        super().__init__({"data_dir": data_dir})

    @classmethod
    def for_attached_machine(
        cls,
        data_dir: str,
        account_name: str = "test_account",
        machine_token: "Dict[str, Any]" = None,
    ):
        if not machine_token:
            machine_token = {
                "availableResources": [],
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
        config = cls(data_dir)
        config.write_cache("machine-token", machine_token)
        return config
