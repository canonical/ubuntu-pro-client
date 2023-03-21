"""Tests related to uaclient.util module."""
import datetime
import json
import logging
import socket
import urllib

import mock
import pytest

from uaclient import cli, exceptions, messages, util
from uaclient.log import RedactionFilter


class TestGetDictDeltas:
    @pytest.mark.parametrize(
        "value1,value2", (("val1", "val2"), ([1], [2]), ((1, 2), (3, 4)))
    )
    def test_non_dict_diffs_return_new_value(self, value1, value2):
        """When two values differ and are not a dict return the new value."""
        expected = {"key": value2}
        assert expected == util.get_dict_deltas(
            {"key": value1}, {"key": value2}
        )

    def test_diffs_return_new_keys_and_values(self):
        """New keys previously absent will be returned in the delta."""
        expected = {"newkey": "val"}
        assert expected == util.get_dict_deltas(
            {"k": "v"}, {"newkey": "val", "k": "v"}
        )

    def test_diffs_return_dropped_keys_set_dropped(self):
        """Old keys which are now dropped are returned as DROPPED_KEY."""
        expected = {"oldkey": util.DROPPED_KEY, "oldkey2": util.DROPPED_KEY}
        assert expected == util.get_dict_deltas(
            {"oldkey": "v", "k": "v", "oldkey2": {}}, {"k": "v"}
        )

    def test_return_only_keys_which_represent_deltas(self):
        """Only return specific keys which have deltas."""
        orig_dict = {
            "1": "1",
            "2": "orig2",
            "3": {"3.1": "3.1", "3.2": "orig3.2"},
            "4": {"4.1": "4.1"},
        }
        new_dict = {
            "1": "1",
            "2": "new2",
            "3": {"3.1": "3.1", "3.2": "new3.2"},
            "4": {"4.1": "4.1"},
        }
        expected = {"2": "new2", "3": {"3.2": "new3.2"}}
        assert expected == util.get_dict_deltas(orig_dict, new_dict)


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
        ret = util.is_service_url(url)
        assert is_valid is ret


class TestReadurl:
    @pytest.mark.parametrize(
        "caplog_text", [(logging.DEBUG, RedactionFilter)], indirect=True
    )
    @pytest.mark.parametrize(
        "headers,data,method,url,response,expected_logs",
        (
            (
                {},
                None,
                None,
                "http://some_url",
                None,
                [
                    "URL [GET]: http://some_url, headers: {}, data: None",
                    "URL [GET] response: http://some_url, headers: {},"
                    " data: response\n",
                ],
            ),
            # AWS PRO redacts IMDSv2 token
            (
                {
                    "X-aws-ec2-metadata-token-ttl-seconds": "21600",
                    "X-aws-ec2-metadata-token": "SEKRET",
                },
                None,
                "PUT",
                "http://169.254.169.254/latest/api/token",
                b"SECRET==",
                [
                    "URL [PUT]: http://169.254.169.254/latest/api/token,"
                    " headers: {'X-aws-ec2-metadata-token': '<REDACTED>',"
                    " 'X-aws-ec2-metadata-token-ttl-seconds': '21600'}",
                    "URL [PUT] response:"
                    " http://169.254.169.254/latest/api/token, headers:"
                    " {'X-aws-ec2-metadata-token': '<REDACTED>',"
                    " 'X-aws-ec2-metadata-token-ttl-seconds': '21600'},"
                    " data: <REDACTED>\n",
                ],
            ),
            (
                {"key1": "Bearcat", "Authorization": "Bearer SEKRET"},
                b"{'token': 'HIDEME', 'tokenInfo': 'SHOWME'}",
                None,
                "http://some_url",
                b"{'machineToken': 'HIDEME', 'machineTokenInfo': 'SHOWME'}",
                [
                    "URL [POST]: http://some_url, headers: {'Authorization':"
                    " 'Bearer <REDACTED>', 'key1': 'Bearcat'}, data:"
                    " {'token': '<REDACTED>', 'tokenInfo': 'SHOWME'}",
                    "URL [POST] response: http://some_url, headers:"
                    " {'Authorization': 'Bearer <REDACTED>', 'key1': 'Bearcat'"
                    "}, data: {'machineToken': '<REDACTED>',"
                    " 'machineTokenInfo': 'SHOWME'}",
                ],
            ),
        ),
    )
    @mock.patch("uaclient.util.request.urlopen")
    def test_readurl_redacts_call_and_response(
        self,
        urlopen,
        headers,
        data,
        method,
        url,
        response,
        expected_logs,
        caplog_text,
    ):
        """Log and redact sensitive data from logs for url interactions."""

        class FakeHTTPResponse:
            def __init__(self, headers, content):
                self.headers = headers
                self._content = content

            def read(self):
                return self._content

        if not response:
            response = b"response"
        urlopen.return_value = FakeHTTPResponse(
            headers=headers, content=response
        )
        util.readurl(url, method=method, headers=headers, data=data)
        logs = caplog_text()
        for log in expected_logs:
            assert log in logs

    @pytest.mark.parametrize("timeout", (None, 1))
    def test_simple_call_with_url_and_timeout_works(self, timeout):
        with mock.patch("uaclient.util.request.urlopen") as m_urlopen:
            if timeout:
                util.readurl("http://some_url", timeout=timeout)
            else:
                util.readurl("http://some_url")
        assert [
            mock.call(mock.ANY, timeout=timeout)
        ] == m_urlopen.call_args_list

    def test_call_with_timeout(self):
        with mock.patch("uaclient.util.request.urlopen") as m_urlopen:
            util.readurl("http://some_url")
        assert 1 == m_urlopen.call_count

    @pytest.mark.parametrize(
        "data", [b"{}", b"not a dict", b'{"caveat_id": "dict"}']
    )
    def test_data_passed_through_unchanged(self, data):
        with mock.patch("uaclient.util.request.urlopen") as m_urlopen:
            util.readurl("http://some_url", data=data)

        assert 1 == m_urlopen.call_count
        req = m_urlopen.call_args[0][0]  # the first positional argument
        assert data == req.data


@mock.patch("uaclient.util.we_are_currently_root", return_value=False)
class TestDisableLogToConsole:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_no_error_if_console_handler_not_found(
        self, m_we_are_currently_root, caplog_text
    ):
        with mock.patch("uaclient.util.logging.getLogger") as m_getlogger:
            m_getlogger.return_value.handlers = []
            with util.disable_log_to_console():
                pass

        assert "no console handler found" in caplog_text()

    @pytest.mark.parametrize("disable_log", (True, False))
    @mock.patch("uaclient.log.get_user_log_file")
    def test_disable_log_to_console(
        self,
        m_get_user,
        m_we_are_currently_root,
        logging_sandbox,
        capsys,
        tmpdir,
        disable_log,
    ):
        # This test is parameterised so that we are sure that the context
        # manager is suppressing the output, not some other config change

        log_file = tmpdir.join("file.log").strpath
        m_get_user.return_value = log_file
        cli.setup_logging(logging.INFO, logging.INFO, log_file=log_file)

        if disable_log:
            context_manager = util.disable_log_to_console
        else:
            context_manager = mock.MagicMock

        with context_manager():
            logging.error("test error")
            logging.info("test info")

        out, err = capsys.readouterr()
        combined_output = out + err
        if disable_log:
            assert not combined_output
        else:
            assert "test error" in combined_output
            assert "test info" in combined_output

    @mock.patch("uaclient.log.get_user_log_file")
    def test_disable_log_to_console_does_nothing_at_debug_level(
        self,
        m_get_user,
        m_we_are_currently_root,
        logging_sandbox,
        capsys,
        FakeConfig,
        tmpdir,
    ):
        m_get_user.return_value = tmpdir.join("file.log").strpath
        with mock.patch(
            "uaclient.cli.config.UAConfig", return_value=FakeConfig()
        ):
            cli.setup_logging(logging.DEBUG, logging.DEBUG)

            with util.disable_log_to_console():
                logging.error("test error")
                logging.info("test info")

        out, err = capsys.readouterr()
        combined_output = out + err
        assert "test error" in combined_output
        assert "test info" in combined_output


JSON_TEST_PAIRS = (
    ("a", '"a"'),
    (1, "1"),
    ({"a": 1}, '{"a": 1}'),
    # See the note in DatetimeAwareJSONDecoder for why this datetime is in a
    # dict
    (
        {
            "dt": datetime.datetime(
                2019, 7, 25, 14, 35, 51, tzinfo=datetime.timezone.utc
            )
        },
        '{"dt": "2019-07-25T14:35:51+00:00"}',
    ),
)


class TestDatetimeAwareJSONEncoder:
    @pytest.mark.parametrize("input,out", JSON_TEST_PAIRS)
    def test_encode(self, input, out):
        assert out == json.dumps(input, cls=util.DatetimeAwareJSONEncoder)


class TestDatetimeAwareJSONDecoder:
    # Note that the parameter names are flipped from
    # TestDatetimeAwareJSONEncoder
    @pytest.mark.parametrize("out,input", JSON_TEST_PAIRS)
    def test_encode(self, input, out):
        assert out == json.loads(input, cls=util.DatetimeAwareJSONDecoder)


@mock.patch("builtins.input")
class TestPromptForConfirmation:
    @pytest.mark.parametrize(
        "return_value,user_input",
        [(True, yes_input) for yes_input in ["y", "Y", "yes", "YES", "YeS"]]
        + [
            (False, no_input)
            for no_input in ["n", "N", "no", "NO", "No", "asdf", "", "\nfoo\n"]
        ],
    )
    def test_input_conversion(self, m_input, return_value, user_input):
        m_input.return_value = user_input
        assert return_value == util.prompt_for_confirmation()

    @pytest.mark.parametrize(
        "assume_yes,message,input_calls",
        [
            (True, "message ignored on assume_yes=True", []),
            (False, "", [mock.call("Are you sure? (y/N) ")]),
            (False, "Custom yep? (y/N) ", [mock.call("Custom yep? (y/N) ")]),
        ],
    )
    def test_prompt_text(self, m_input, assume_yes, message, input_calls):
        util.prompt_for_confirmation(msg=message, assume_yes=assume_yes)

        assert input_calls == m_input.call_args_list


class TestIsConfigValueTrue:
    @pytest.mark.parametrize(
        "config_dict, return_val",
        [
            ({}, False),
            ({}, False),
            (None, False),
            ({None}, False),
            ({"allow_beta": "true"}, True),
            ({"allow_beta": "True"}, True),
            ({"allow_beta": "false"}, False),
            ({"allow_beta": "False"}, False),
        ],
    )
    def test_is_config_value_true(self, config_dict, return_val, FakeConfig):
        cfg = FakeConfig()
        cfg.override_features(config_dict)
        actual_val = util.is_config_value_true(
            config=cfg.cfg, path_to_value="features.allow_beta"
        )
        assert return_val == actual_val

    @pytest.mark.parametrize(
        "config_dict, key_val",
        [
            ({"allow_beta": "tru"}, "tru"),
            ({"allow_beta": "Tre"}, "Tre"),
            ({"allow_beta": "flse"}, "flse"),
            ({"allow_beta": "Fale"}, "Fale"),
        ],
    )
    def test_exception_is_config_value_true(
        self, config_dict, key_val, FakeConfig
    ):
        path_to_value = "features.allow_beta"
        cfg = FakeConfig()
        cfg.override_features(config_dict)
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            util.is_config_value_true(
                config=cfg.cfg, path_to_value=path_to_value
            )

        expected_msg = messages.ERROR_INVALID_CONFIG_VALUE.format(
            path_to_value=path_to_value,
            expected_value="boolean string: true or false",
            value=key_val,
        )
        assert expected_msg == str(excinfo.value)


class TestRedactSensitiveLogs:
    @pytest.mark.parametrize(
        "raw_log,expected",
        (
            ("Super valuable", "Super valuable"),
            (
                "Hi 'Bearer not the droids you are looking for', data",
                "Hi 'Bearer <REDACTED>', data",
            ),
            (
                "Hi 'Bearer not the droids you are looking for', data",
                "Hi 'Bearer <REDACTED>', data",
            ),
            (
                "Executed with sys.argv: ['/usr/bin/ua', 'attach', 'SEKRET']",
                "Executed with sys.argv:"
                " ['/usr/bin/ua', 'attach', '<REDACTED>']",
            ),
            (
                "'resourceTokens': [{'token': 'SEKRET', 'type': 'cc-eal'}]'",
                "'resourceTokens':"
                " [{'token': '<REDACTED>', 'type': 'cc-eal'}]'",
            ),
            (
                "'machineToken': 'SEKRET', 'machineTokenInfo': 'blah'",
                "'machineToken': '<REDACTED>', 'machineTokenInfo': 'blah'",
            ),
            (
                "Failed running command '/usr/lib/apt/apt-helper download-file"
                "https://bearer:S3-Kr3T@esm.ubuntu.com/infra/ubuntu/pool/ "
                "[exit(100)]. Message: Download of file failed"
                " pkgAcquire::Run (13: Permission denied)",
                "Failed running command '/usr/lib/apt/apt-helper download-file"
                "https://bearer:<REDACTED>@esm.ubuntu.com/infra/ubuntu/pool/ "
                "[exit(100)]. Message: Download of file failed"
                " pkgAcquire::Run (13: Permission denied)",
            ),
            (
                "/snap/bin/canonical-livepatch enable S3-Kr3T, foobar",
                "/snap/bin/canonical-livepatch enable <REDACTED> foobar",
            ),
            (
                "Contract value for 'resourceToken' changed to S3kR3T",
                "Contract value for 'resourceToken' changed to <REDACTED>",
            ),
            (
                "data: {'contractToken': 'SEKRET', "
                "'contractTokenInfo':{'expiry'}}",
                "data: {'contractToken': '<REDACTED>', "
                "'contractTokenInfo':{'expiry'}}",
            ),
            (
                "data: {'resourceToken': 'SEKRET', "
                "'entitlement': {'affordances':'blah blah' }}",
                "data: {'resourceToken': '<REDACTED>', "
                "'entitlement': {'affordances':'blah blah' }}",
            ),
            (
                "https://contracts.canonical.com/v1/resources/livepatch"
                "?token=SEKRET: invalid token",
                "https://contracts.canonical.com/v1/resources/livepatch"
                "?token=<REDACTED> invalid token",
            ),
            (
                'data: {"identityToken": "SEket.124-_ys"}',
                'data: {"identityToken": "<REDACTED>"}',
            ),
            (
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
            ),
            (
                "response: "
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
                "response: "
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: <REDACTED>",
            ),
            (
                "'token': 'SEKRET'",
                "'token': '<REDACTED>'",
            ),
            (
                "'userCode': 'SEKRET'",
                "'userCode': '<REDACTED>'",
            ),
            (
                "'magic_token=SEKRET'",
                "'magic_token=<REDACTED>'",
            ),
        ),
    )
    def test_redact_all_matching_regexs(self, raw_log, expected):
        """Redact all sensitive matches from log messages."""
        assert expected == util.redact_sensitive_logs(raw_log)


class TestParseRFC3339Date:
    @pytest.mark.parametrize(
        "datestring,expected",
        [
            (
                "2001-02-03T04:05:06",
                datetime.datetime(
                    2001, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2001-02-03T04:05:06.123456",
                datetime.datetime(
                    2001, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2001-02-03T04:05:06Z",
                datetime.datetime(
                    2001, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2001-02-03T04:05:06-08:00",
                datetime.datetime(
                    2001,
                    2,
                    3,
                    4,
                    5,
                    6,
                    tzinfo=datetime.timezone(-datetime.timedelta(hours=8)),
                ),
            ),
            (
                "2001-02-03T04:05:06+03:00",
                datetime.datetime(
                    2001,
                    2,
                    3,
                    4,
                    5,
                    6,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=3)),
                ),
            ),
            (
                "2021-05-07T09:46:37.791Z",
                datetime.datetime(
                    2021, 5, 7, 9, 46, 37, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2021-05-28T14:42:37.944609726-04:00",
                datetime.datetime(
                    2021,
                    5,
                    28,
                    14,
                    42,
                    37,
                    tzinfo=datetime.timezone(-datetime.timedelta(hours=4)),
                ),
            ),
        ],
    )
    def test_parse_rfc3339_date_from_golang(self, datestring, expected):
        """
        Check we are able to parse dates generated by golang's MarshalJSON
        """
        assert expected == util.parse_rfc3339_date(datestring)


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
        with mock.patch.dict(util.os.environ, m_environ, clear=True):
            util.configure_web_proxy(
                http_proxy=http_proxy, https_proxy=https_proxy
            )
            assert expected_environ == util.os.environ


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
            util.validate_proxy("http", proxy, "http://example.com")

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
        ret = util.validate_proxy(protocol, proxy, test_url)

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
            util.validate_proxy(
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


class TestHandleUnicodeCharacters:
    @pytest.mark.parametrize(
        "encoding", ((None), ("utf-8"), ("UTF-8"), ("test"))
    )
    @pytest.mark.parametrize(
        "message,modified_message",
        (
            (messages.OKGREEN_CHECK + " test", "test"),
            (messages.FAIL_X + " fail", "fail"),
            ("\u2014 blah", "- blah"),
        ),
    )
    def test_handle_unicode_characters(
        self, message, modified_message, encoding
    ):
        expected_message = message
        if encoding is None or encoding.upper() != "UTF-8":
            expected_message = modified_message

        with mock.patch("sys.stdout") as m_stdout:
            type(m_stdout).encoding = mock.PropertyMock(return_value=encoding)
            assert expected_message == util.handle_unicode_characters(message)


class TestGetProEnvironment:
    @mock.patch(
        "os.environ",
        {
            "UA_CONFIG_FILE": "example_config_file",
            "UA_INVALID_KEY": "some_value",
            "NOT_EVEN_UA": "some_other_value",
            "UA_FEATURES_WOW": "cool_feature",
            "UA_LOG_LEVEL": "DEBUG",
        },
    )
    def test_get_pro_environment(self):
        expected = {
            "UA_CONFIG_FILE": "example_config_file",
            "UA_FEATURES_WOW": "cool_feature",
            "UA_LOG_LEVEL": "DEBUG",
        }
        assert expected == util.get_pro_environment()


class TestDeduplicateArches:
    @pytest.mark.parametrize(
        ["arches", "expected"],
        [
            ([], []),
            (["anything"], ["anything"]),
            (["amd64"], ["amd64"]),
            (["amd64", "x86_64"], ["amd64"]),
            (
                ["amd64", "ppc64el", "ppc64le", "s390x", "x86_64"],
                ["amd64", "ppc64el", "s390x"],
            ),
            (["amd64", "i386", "i686", "x86_64"], ["amd64", "i386"]),
            (
                ["amd64", "i386", "i686", "x86_64", "armhf", "arm64"],
                ["amd64", "arm64", "armhf", "i386"],
            ),
            (
                [
                    "x86_64",
                    "amd64",
                    "i686",
                    "i386",
                    "ppc64le",
                    "aarch64",
                    "arm64",
                    "armv7l",
                    "armhf",
                    "s390x",
                ],
                ["amd64", "arm64", "armhf", "i386", "ppc64el", "s390x"],
            ),
        ],
    )
    def test_deduplicate_arches(self, arches, expected):
        assert expected == util.deduplicate_arches(arches)
