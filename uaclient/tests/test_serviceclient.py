import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

import mock
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
        return "contract_url"


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
        self, m_readurl, fp, expected_exception, expected_attrs, FakeConfig
    ):
        m_readurl.side_effect = HTTPError(None, 619, None, None, fp)
        cfg = FakeConfig()
        cfg.cfg["contract_url"] = "http://example.com"
        client = OurServiceClient(cfg=cfg)
        with pytest.raises(expected_exception) as excinfo:
            client.request_url("/")

        for attr, expected_value in expected_attrs.items():
            assert expected_value == getattr(excinfo.value, attr)

    @mock.patch("uaclient.serviceclient.util.readurl")
    def test_urlerror_handling(self, m_readurl, FakeConfig):
        m_readurl.side_effect = URLError(None)

        cfg = FakeConfig()
        cfg.cfg["contract_url"] = "http://example.com"
        client = OurServiceClient(cfg=cfg)
        with pytest.raises(util.UrlError) as excinfo:
            client.request_url("/")

        assert excinfo.value.code is None

    @pytest.mark.parametrize(
        "m_kwargs", ({"a": 1, "b": "2", "c": "try me"}, {})
    )
    @mock.patch("uaclient.serviceclient.util.readurl")
    def test_url_query_params_append_querystring(
        self, m_readurl, m_kwargs, FakeConfig
    ):
        m_readurl.return_value = (m_kwargs, {})  # (response, resp_headers)

        cfg = FakeConfig()
        url = "http://example.com/"
        cfg.cfg["contract_url"] = url
        client = OurServiceClient(cfg=cfg)
        assert (m_kwargs, {}) == client.request_url("/", query_params=m_kwargs)
        if m_kwargs:
            url += "?" + urlencode(m_kwargs)
        assert [
            mock.call(
                url=url,
                data=None,
                headers=client.headers(),
                method=None,
                timeout=None,
            )
        ] == m_readurl.call_args_list


URL_FAKES = {
    "http://a": [{"code": 200, "response": {"key": "val", "key2": "val2"}}],
    "http://anerror": [{"code": 404, "response": "nothing to see"}],
    "http://multiresp": [
        {"code": 200, "response": "resp1"},
        {
            "code": 200,
            "response": "resp2",
            "headers": {"content-type": "application/json"},
        },
    ],
}


class Test_GetResponseOverlay:
    @pytest.mark.parametrize(
        "url,expected",
        (
            ("http://a", URL_FAKES["http://a"]),
            ("http://multiresp", URL_FAKES["http://multiresp"]),
        ),
    )
    def test_overlay_returns_matching_url(
        self, url, expected, FakeConfig, tmpdir
    ):
        overlay_path = tmpdir.join("overlay.json")
        overlay_path.write(json.dumps(URL_FAKES))
        cfg = FakeConfig()
        cfg.override_features(
            {"serviceclient_url_responses": overlay_path.strpath}
        )
        client = OurServiceClient(cfg=cfg)
        assert expected == client._get_response_overlay(url)
        # url overrides are cached and not re-read from disk
        overlay_path.write(json.dumps({}))
        assert expected == client._get_response_overlay(url)


class Test_GetFakeResponses:
    @pytest.mark.parametrize(
        "url,overlay,responses",
        (
            # When URL has no fakes
            ("http://a", {}, [(None, {})]),
            # When URL has 1 fake, repeat that response for all calls
            (
                "http://a",
                URL_FAKES,
                [(URL_FAKES["http://a"][0]["response"], {})] * 2,
            ),
            # When URL has >1 fake, pop through that list and repeat last item
            (
                "http://multiresp",
                URL_FAKES,
                [(URL_FAKES["http://multiresp"][0]["response"], {})]
                + [
                    (
                        URL_FAKES["http://multiresp"][1]["response"],
                        URL_FAKES["http://multiresp"][1]["headers"],
                    )
                ]
                * 2,
            ),
            # When URL fake is code != 200 raise URLError
            (
                "http://anerror",
                URL_FAKES,
                [(URLError(URL_FAKES["http://anerror"][0]["response"]), {})],
            ),
        ),
    )
    def test_overlay_returns_matching_url(
        self, url, overlay, responses, FakeConfig, tmpdir
    ):
        overlay_path = tmpdir.join("overlay.json")
        overlay_path.write(json.dumps(overlay))
        cfg = FakeConfig()
        cfg.override_features(
            {"serviceclient_url_responses": overlay_path.strpath}
        )
        client = OurServiceClient(cfg=cfg)
        for response, headers in responses:
            if isinstance(response, Exception):
                with pytest.raises(util.UrlError) as excinfo:
                    client._get_fake_responses(url)
                assert 404 == excinfo.value.code
                assert "nothing to see" == str(excinfo.value)
            else:
                assert (response, headers) == client._get_fake_responses(url)
