"""Tests related to uaclient.util module."""
import datetime
import json

import mock
import pytest

from uaclient import exceptions, messages, secret_manager, util


@pytest.fixture
def secret_manager_fixture():
    manager = secret_manager.SecretManager()
    secrets = [
        "SEKRET",
        "S3-Kr3T",
        "S3kR3T",
        "SEket.124-_ys",
        "reg key",
        "reg-key",
    ]
    for secret in secrets:
        manager.add_secret(secret)
    return manager


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
        with pytest.raises(exceptions.InvalidBooleanConfigValue) as excinfo:
            util.is_config_value_true(
                config=cfg.cfg, path_to_value=path_to_value
            )

        expected_msg = messages.E_INVALID_BOOLEAN_CONFIG_VALUE.format(
            path_to_value=path_to_value,
            expected_value="boolean string: true or false",
            value=key_val,
        ).msg
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
            (
                "--account-name name --registration-key=reg-key --silent",
                "--account-name name --registration-key=<REDACTED> --silent",
            ),
            (
                '--account-name name --registration-key="reg key" --silent',
                "--account-name name --registration-key=<REDACTED> --silent",
            ),
            (
                "--account-name name --registration-key='reg key' --silent",
                "--account-name name --registration-key=<REDACTED> --silent",
            ),
            (
                "--account-name name --registration-key reg-key --silent",
                "--account-name name --registration-key <REDACTED> --silent",
            ),
            (
                '--account-name name --registration-key "reg key" --silent',
                "--account-name name --registration-key <REDACTED> --silent",
            ),
            (
                "--account-name name --registration-key 'reg key' --silent",
                "--account-name name --registration-key <REDACTED> --silent",
            ),
            (
                "--account-name name -p reg-key --silent",
                "--account-name name -p <REDACTED> --silent",
            ),
            (
                '--account-name name -p "reg key" --silent',
                "--account-name name -p <REDACTED> --silent",
            ),
            (
                "--account-name name -p 'reg key' --silent",
                "--account-name name -p <REDACTED> --silent",
            ),
        ),
    )
    def test_redact_all_matching_regexs(self, raw_log, expected):
        """Redact all sensitive matches from log messages."""
        assert expected == util.redact_sensitive_logs(raw_log)

    @pytest.mark.parametrize(
        "raw_log,expected",
        (
            ("Super valuable", "Super valuable"),
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
                "/snap/bin/canonical-livepatch enable <REDACTED>, foobar",
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
                "?token=<REDACTED>: invalid token",
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
            (
                "--account-name name --registration-key=reg-key --silent",
                "--account-name name --registration-key=<REDACTED> --silent",
            ),
            (
                '--account-name name --registration-key="reg key" --silent',
                '--account-name name --registration-key="<REDACTED>" --silent',
            ),
            (
                "--account-name name --registration-key='reg key' --silent",
                "--account-name name --registration-key='<REDACTED>' --silent",
            ),
            (
                "--account-name name --registration-key reg-key --silent",
                "--account-name name --registration-key <REDACTED> --silent",
            ),
            (
                '--account-name name --registration-key "reg key" --silent',
                '--account-name name --registration-key "<REDACTED>" --silent',
            ),
            (
                "--account-name name --registration-key 'reg key' --silent",
                "--account-name name --registration-key '<REDACTED>' --silent",
            ),
            (
                "--account-name name -p reg-key --silent",
                "--account-name name -p <REDACTED> --silent",
            ),
            (
                '--account-name name -p "reg key" --silent',
                '--account-name name -p "<REDACTED>" --silent',
            ),
            (
                "--account-name name -p 'reg key' --silent",
                "--account-name name -p '<REDACTED>' --silent",
            ),
        ),
    )
    def test_secret_redaction_filter(
        self, secret_manager_fixture, raw_log, expected
    ):
        """Redact all sensitive matches from log messages."""
        assert expected == secret_manager_fixture.redact_secrets(raw_log)


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
            ("\xfcblah", "blah"),
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


class TestReplaceLoggerName:
    @pytest.mark.parametrize(
        ["logger_name", "new_logger_name"],
        (
            ("uaclient.module.name1", "ubuntupro.module.name1"),
            ("log.module1.name2", "ubuntupro.module1.name2"),
            ("prolog.lang.old", "ubuntupro.lang.old"),
            ("", ""),
            (".", "ubuntupro."),
            ("module1", "ubuntupro"),
        ),
    )
    def test_replace_top_level_logger_name(self, logger_name, new_logger_name):
        assert (
            util.replace_top_level_logger_name(logger_name) == new_logger_name
        )


class TestSetFilenameExtension:
    @pytest.mark.parametrize(
        "input_string,extension,output_string",
        (
            ("virus.exe", "test", "virus.test"),
            (
                "/many/dots.and.slashes/in/this.file",
                "test",
                "/many/dots.and.slashes/in/this.test",
            ),
            ("/no/change/when.same", "same", "/no/change/when.same"),
            ("no_extension", "test", "no_extension.test"),
            (
                "/with.previous.dots/no_extension",
                "test",
                "/with.previous.dots/no_extension.test",
            ),
            ("d.o.t.s", "test", "d.o.t.test"),
            (".dotfile", "test", ".dotfile.test"),
        ),
    )
    def test_set_filename_extension(
        self, input_string, extension, output_string
    ):
        assert (
            util.set_filename_extension(input_string, extension)
            == output_string
        )
