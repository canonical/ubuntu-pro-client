import abc
import json
import os
from posixpath import join as urljoin
from typing import Any, Dict, Optional, Tuple, Type
from urllib import error
from urllib.parse import urlencode

from uaclient import config, exceptions, util, version


class UAServiceClient(metaclass=abc.ABCMeta):

    url_timeout = None  # type: Optional[int]
    # Cached serviceclient_url_responses if provided in uaclient.conf
    # via features: {serviceclient_url_responses: /some/file.json}
    _response_overlay = None  # type: Dict[str, Any]

    @property
    @abc.abstractmethod
    def api_error_cls(self) -> Type[Exception]:
        """Set in subclasses to the type of API error raised"""
        pass

    @property
    @abc.abstractmethod
    def cfg_url_base_attr(self) -> str:
        """String in subclasses, the UAConfig attribute containing base url"""
        pass

    def __init__(self, cfg: Optional[config.UAConfig] = None) -> None:
        if not cfg:
            self.cfg = config.UAConfig()
        else:
            self.cfg = cfg

    def headers(self):
        return {
            "user-agent": "UA-Client/{}".format(version.get_version()),
            "accept": "application/json",
            "content-type": "application/json",
        }

    def request_url(
        self, path, data=None, headers=None, method=None, query_params=None
    ):
        path = path.lstrip("/")
        if not headers:
            headers = self.headers()
        if headers.get("content-type") == "application/json" and data:
            data = json.dumps(data).encode("utf-8")
        url = urljoin(getattr(self.cfg, self.cfg_url_base_attr), path)
        fake_response, fake_headers = self._get_fake_responses(url)
        if fake_response:
            return fake_response, fake_headers  # URL faked by uaclient.conf
        if query_params:
            # filter out None values
            filtered_params = {
                k: v for k, v in sorted(query_params.items()) if v is not None
            }
            url += "?" + urlencode(filtered_params)
        try:
            response, headers = util.readurl(
                url=url,
                data=data,
                headers=headers,
                method=method,
                timeout=self.url_timeout,
            )
        except error.URLError as e:
            body = None
            if hasattr(e, "body"):
                body = e.body
            elif hasattr(e, "read"):
                body = e.read().decode("utf-8")
            if body:
                try:
                    error_details = json.loads(
                        body, cls=util.DatetimeAwareJSONDecoder
                    )
                except ValueError:
                    error_details = None
                if error_details:
                    raise self.api_error_cls(e, error_details)
            raise exceptions.UrlError(
                e, code=getattr(e, "code", None), headers=headers, url=url
            )
        return response, headers

    def _get_response_overlay(self, url: str):
        """Return a list of fake response dicts for a given URL.

        serviceclient_url_responses in uaclient.conf should be a path
        to a json file which contains a dictionary keyed by full URL path.
        Each value will be a list of dicts representing each faked response
        for the given URL.

            The response dict item will have a code: <HTTP_STATUS_CODE> and
               response: "some string of content".
            The JSON string below fakes the available_resources URL on the
            contract server:
            '{"https://contracts.canonical.com/v1/resources": \
               [{"code": 200, "response": {"key": "val1", "key2": "val2"}}]}'

        :return: List of dicts for each faked response matching the url, or
           and empty list when no matching url found.
        """
        if self._response_overlay is not None:
            # Cache it so we don't re-read config every readurl call
            return self._response_overlay.get(url, [])
        response_overlay_path = self.cfg.features.get(
            "serviceclient_url_responses"
        )
        if not response_overlay_path:
            self._response_overlay = {}
        elif not os.path.exists(response_overlay_path):
            self._response_overlay = {}
        else:
            self._response_overlay = json.loads(
                util.load_file(response_overlay_path)
            )
        return self._response_overlay.get(url, [])

    def _get_fake_responses(
        self, url: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
        """Return response and headers if faked for this URL in uaclient.conf.

        :return: A tuple of response and header dicts if the URL has an overlay
            response defined. Return (None, {}) otherwise.

        :raises exceptions.URLError: When faked response "code" is != 200.
            URLError reason will be "response" value and any optional
            "headers" provided.
        """
        responses = self._get_response_overlay(url)
        if not responses:
            return None, {}
        if len(responses) == 1:
            # When only one respose is defined, repeat it for all calls
            response = responses[0]
        else:
            # When multiple responses defined pop the first one off the list.
            response = responses.pop(0)
        if response["code"] == 200:
            return response["response"], response.get("headers", {})
        # Must be an error
        e = error.URLError(response["response"])
        raise exceptions.UrlError(
            e,
            code=response["code"],
            headers=response.get("headers", {}),
            url=url,
        )
