import socket
import urllib

import mock
import pytest

from uaclient import exceptions, http, messages


class TestIsServiceUrl:
    @pytest.mark.parametrize(
        "url,is_valid",
        (
            ("http://asdf", True),
            ("http://asdf/", True),
            ("asdf", False),
            ("http://host:port", False),
            ("http://asdf:1234", True),
        ),
    )
    def test_is_valid_url(self, url, is_valid):
        ret = http.is_service_url(url)
        assert is_valid is ret


class TestValidateProxy:
    @pytest.mark.parametrize(
        "proxy", ["invalidurl", "htp://wrongscheme", "http//missingcolon"]
    )
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_fails_on_invalid_url(self, m_open, proxy):
        """
        Check that invalid urls are rejected with the correct message
        and that we don't even attempt to use them
        """
        with pytest.raises(exceptions.UserFacingError) as e:
            http.validate_proxy("http", proxy, "http://example.com")

        assert (
            e.value.msg
            == messages.NOT_SETTING_PROXY_INVALID_URL.format(proxy=proxy).msg
        )

    @pytest.mark.parametrize(
        "protocol, proxy, test_url",
        [
            ("http", "http://localhost:1234", "http://example.com"),
            ("https", "http://localhost:1234", "https://example.com"),
            ("https", "https://localhost:1234", "https://example.com"),
        ],
    )
    @mock.patch("urllib.request.Request")
    @mock.patch("urllib.request.ProxyHandler")
    @mock.patch("urllib.request.build_opener")
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_calls_open_on_valid_url(
        self,
        m_open,
        m_build_opener,
        m_proxy_handler,
        m_request,
        protocol,
        proxy,
        test_url,
    ):
        """
        Check that we attempt to use a valid url as a proxy
        Also check that we return the proxy value when the open call succeeds
        """
        m_build_opener.return_value = urllib.request.OpenerDirector()
        ret = http.validate_proxy(protocol, proxy, test_url)

        assert [mock.call(test_url, method="HEAD")] == m_request.call_args_list
        assert [mock.call({protocol: proxy})] == m_proxy_handler.call_args_list
        assert 1 == m_build_opener.call_count
        assert 1 == m_open.call_count

        assert proxy == ret

    @pytest.mark.parametrize(
        "open_side_effect, expected_message",
        [
            (socket.timeout(0, "timeout"), "[Errno 0] timeout"),
            (urllib.error.URLError("reason"), "reason"),
        ],
    )
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_fails_when_open_fails(
        self, m_open, open_side_effect, expected_message, caplog_text
    ):
        """
        Check that we return the appropriate error when the proxy doesn't work
        """
        m_open.side_effect = open_side_effect
        with pytest.raises(exceptions.UserFacingError) as e:
            http.validate_proxy(
                "http", "http://localhost:1234", "http://example.com"
            )

        assert (
            e.value.msg
            == messages.NOT_SETTING_PROXY_NOT_WORKING.format(
                proxy="http://localhost:1234"
            ).msg
        )

        assert (
            messages.ERROR_USING_PROXY.format(
                proxy="http://localhost:1234",
                test_url="http://example.com",
                error=expected_message,
            )
            in caplog_text()
        )


class TestConfigureWebProxy:
    @pytest.mark.parametrize(
        "http_proxy,https_proxy,m_environ,expected_environ",
        (
            (
                None,
                None,
                {},
                {
                    "NO_PROXY": "169.254.169.254,[fd00:ec2::254],metadata",
                    "no_proxy": "169.254.169.254,[fd00:ec2::254],metadata",
                },
            ),
            (
                "http://proxy",
                "https://proxy",
                {"no_proxy": "a,10.0.0.1"},
                {
                    "NO_PROXY": "10.0.0.1,169.254.169.254,[fd00:ec2::254],a,metadata",  # noqa
                    "no_proxy": "10.0.0.1,169.254.169.254,[fd00:ec2::254],a,metadata",  # noqa
                },
            ),
            (
                "http://proxy",
                "https://proxy",
                {"NO_PROXY": "a,169.254.169.254"},
                {
                    "NO_PROXY": "169.254.169.254,[fd00:ec2::254],a,metadata",
                    "no_proxy": "169.254.169.254,[fd00:ec2::254],a,metadata",
                },
            ),
        ),
    )
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_no_proxy_set_in_environ(
        self, m_open, http_proxy, https_proxy, m_environ, expected_environ
    ):
        with mock.patch.dict(http.os.environ, m_environ, clear=True):
            http.configure_web_proxy(
                http_proxy=http_proxy, https_proxy=https_proxy
            )
            assert expected_environ == http.os.environ


class TestReadurl:
    @pytest.mark.parametrize("timeout", (None, 1))
    def test_simple_call_with_url_and_timeout_works(self, timeout):
        with mock.patch("uaclient.http.request.urlopen") as m_urlopen:
            if timeout:
                http.readurl("http://some_url", timeout=timeout)
            else:
                http.readurl("http://some_url")
        assert [
            mock.call(mock.ANY, timeout=timeout)
        ] == m_urlopen.call_args_list

    def test_call_with_timeout(self):
        with mock.patch("uaclient.http.request.urlopen") as m_urlopen:
            http.readurl("http://some_url")
        assert 1 == m_urlopen.call_count

    @pytest.mark.parametrize(
        "data", [b"{}", b"not a dict", b'{"caveat_id": "dict"}']
    )
    def test_data_passed_through_unchanged(self, data):
        with mock.patch("uaclient.http.request.urlopen") as m_urlopen:
            http.readurl("http://some_url", data=data)

        assert 1 == m_urlopen.call_count
        req = m_urlopen.call_args[0][0]  # the first positional argument
        assert data == req.data
