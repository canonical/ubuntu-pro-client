from uaclient.contract import (
    API_V1_TMPL_CONTEXT_MACHINE_TOKEN_RESOURCE,
    UAContractClient,
)


class FakeContractClient(UAContractClient):

    _requests = []
    _responses = {}

    refresh_route = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_RESOURCE.format(
        contract="cid", machine="mid"
    )

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
        response = self._responses.get(path)
        if isinstance(response, Exception):
            raise response
        return response, {"header1": ""}
