import mock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from io import BytesIO

import pytest

from uaclient import util
from uaclient.serviceclient import UAServiceClient


class OurServiceClientException(Exception):
    def __init__(self, exc, details):
        self.exc = exc
        self.details = details


class OurServiceClient(UAServiceClient):
    @property
    def api_error_cls(self):
        return OurServiceClientException

    @property
    def cfg_url_base_attr(self):
        return "url_attr"


class TestRequestUrl:

    # TODO: Non error-path tests

    @pytest.mark.parametrize(
        "fp,expected_exception,expected_attrs",
        (
            (BytesIO(), util.UrlError, {"code": 619}),
            (
                BytesIO(b'{"a": "b"}'),
                OurServiceClientException,
                {"details": {"a": "b"}},
            ),
        ),
    )
    @mock.patch("uaclient.serviceclient.util.readurl")
    def test_httperror_handling(
        self, m_readurl, fp, expected_exception, expected_attrs
    ):
        m_readurl.side_effect = HTTPError(None, 619, None, None, fp)

        client = OurServiceClient(cfg=mock.Mock(url_attr="http://example.com"))
        with pytest.raises(expected_exception) as excinfo:
            client.request_url("/")

        for attr, expected_value in expected_attrs.items():
            assert expected_value == getattr(excinfo.value, attr)

    @mock.patch("uaclient.serviceclient.util.readurl")
    def test_urlerror_handling(self, m_readurl):
        m_readurl.side_effect = URLError(None)

        client = OurServiceClient(cfg=mock.Mock(url_attr="http://example.com"))
        with pytest.raises(util.UrlError) as excinfo:
            client.request_url("/")

        assert excinfo.value.code is None

    @pytest.mark.parametrize(
        "m_kwargs", ({"a": 1, "b": "2", "c": "try me"}, {})
    )
    @mock.patch("uaclient.serviceclient.util.readurl")
    def test_url_query_params_append_querystring(self, m_readurl, m_kwargs):

        m_readurl.return_value = (m_kwargs, {})  # (response, resp_headers)

        client = OurServiceClient(cfg=mock.Mock(url_attr="http://example.com"))
        assert (m_kwargs, {}) == client.request_url("/", query_params=m_kwargs)
        url = "http://example.com/"
        if m_kwargs:
            url += "?" + urlencode(m_kwargs)
        assert [
            mock.call(
                url=url,
                data=None,
                headers=client.headers(),
                method=None,
                timeout=10,
            )
        ] == m_readurl.call_args_list
