import json
from urllib.parse import urlencode

import mock
import pytest

from ubuntupro import http
from ubuntupro.http.serviceclient import UAServiceClient


class OurServiceClient(UAServiceClient):
    @property
    def cfg_url_base_attr(self):
        return "contract_url"


class TestRequestUrl:

    # TODO: Non error-path tests

    @pytest.mark.parametrize(
        "m_kwargs", ({"a": 1, "b": "2", "c": "try me"}, {})
    )
    @mock.patch("ubuntupro.http.readurl")
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
                timeout=30,
                log_response_body=True,
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
            ("http://a", {}, []),
            # When URL has 1 fake, repeat that response for all calls
            (
                "http://a",
                URL_FAKES,
                [URL_FAKES["http://a"][0]] * 2,
            ),
            # When URL has >1 fake, pop through that list and repeat last item
            (
                "http://multiresp",
                URL_FAKES,
                [URL_FAKES["http://multiresp"][0]]
                + [
                    URL_FAKES["http://multiresp"][1],
                    URL_FAKES["http://multiresp"][1],
                ]
                * 2,
            ),
            # When URL fake is code != 200, return that code
            (
                "http://anerror",
                URL_FAKES,
                [URL_FAKES["http://anerror"][0]],
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
        for response in responses:
            assert http.HTTPResponse(
                code=response["code"],
                headers=response.get("headers", {}),
                body=json.dumps(response["response"], sort_keys=True),
                json_dict=response["response"]
                if isinstance(response["response"], dict)
                else {},
                json_list=response["response"]
                if isinstance(response["response"], list)
                else [],
            ) == client._get_fake_responses(url)
