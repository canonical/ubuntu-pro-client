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

    def request_url(
        self, path, data=None, headers=None, method=None, query_params=None
    ):
        request = {
            "path": path,
            "data": data,
            "headers": headers,
            "method": method,
            "query_params": method,
        }
        self._requests.append(request)
        # Return a response if we have one or empty
        response = self._responses.get(path)
        if isinstance(response, Exception):
            raise response
        return response, {"header1": ""}


class FakeFile:
    def __init__(self, content: str, name: str = "fakefile"):
        self.content = content
        self.cursor = 0
        self.name = name

    def read(self, size=None):
        if self.cursor == len(self.content):
            return ""
        if size is None or size >= len(self.content):
            self.cursor = len(self.content)
            return self.content
        ret = self.content[self.cursor : size]
        self.cursor += size
        return ret

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        pass
