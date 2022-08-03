import mock
import pytest

from uaclient.api.api import call_api
from uaclient.api.data_types import APIResponse, ErrorWarningObject
from uaclient.api.errors import APIError, error_out
from uaclient.data_types import IncorrectFieldTypeError
from uaclient.exceptions import UserFacingError
from uaclient.messages import (
    API_BAD_ARGS_FORMAT,
    API_INVALID_ENDPOINT,
    API_MISSING_ARG,
    API_NO_ARG_FOR_ENDPOINT,
    API_UNKNOWN_ARG,
    WARN_NEW_VERSION_AVAILABLE,
)


class TestAPIErrors:
    @mock.patch("uaclient.api.errors.get_pro_environment")
    def test_error_out_fields(self, _m_environment):
        error_response = error_out(None)
        assert isinstance(error_response, APIResponse)
        assert error_response._schema_version == "v1"
        assert error_response.data == {"meta": {"environment_vars": []}}
        assert error_response.result == "failure"
        assert len(error_response.errors) == 1

    @pytest.mark.parametrize(
        "exception,title,code,meta",
        (
            (
                UserFacingError(
                    msg="msg",
                    msg_code="msg_code",
                    additional_info={"some": "information"},
                ),
                "msg",
                "msg_code",
                {"some": "information"},
            ),
            (
                APIError(msg="msg", additional_info={"some": "information"}),
                "msg",
                "api-error",
                {"some": "information"},
            ),
            (TypeError("msg"), "msg", "generic-TypeError", {}),
        ),
    )
    def test_error_out_response(self, exception, title, code, meta):
        error_response = error_out(exception)
        error = error_response.errors[0]

        assert error.title == title
        assert error.code == code
        assert error.meta == meta


class TestAPICall:
    @mock.patch("uaclient.api.api.error_out")
    def test_invalid_endpoint(self, m_error_out, FakeConfig):
        result = call_api("invalid_endpoint", [], cfg=FakeConfig())
        assert result == m_error_out.return_value
        assert m_error_out.call_count == 1
        arg = m_error_out.call_args[0][0]
        assert isinstance(arg, APIError)
        assert (
            arg.msg
            == API_INVALID_ENDPOINT.format(endpoint="invalid_endpoint").msg
        )
        assert arg.msg_code == API_INVALID_ENDPOINT.name

    @pytest.mark.parametrize(
        "arguments", (["badformat"], ["=badformat"], ["badformat="])
    )
    @mock.patch("uaclient.api.api.error_out")
    @mock.patch("uaclient.api.api.import_module")
    def test_bad_formatted_args(
        self, _m_import_module, m_error_out, arguments, FakeConfig
    ):
        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):
            result = call_api("example_endpoint", arguments, FakeConfig)

        assert result == m_error_out.return_value
        assert m_error_out.call_count == 1
        arg = m_error_out.call_args[0][0]
        assert isinstance(arg, APIError)
        assert arg.msg == API_BAD_ARGS_FORMAT.format(arg=arguments[0]).msg
        assert arg.msg_code == API_BAD_ARGS_FORMAT.name

    @pytest.mark.parametrize("options_cls", (None, mock.MagicMock()))
    @mock.patch("uaclient.api.api.error_out")
    @mock.patch("uaclient.api.api.import_module")
    def test_wrong_args(
        self, m_import_module, m_error_out, options_cls, FakeConfig
    ):
        mock_endpoint = mock.MagicMock()
        mock_endpoint.options_cls = options_cls

        m_import_module.return_value.endpoint = mock_endpoint

        if options_cls:
            options_cls.from_dict.side_effect = IncorrectFieldTypeError(
                err=mock.MagicMock(), key="k"
            )

        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):
            result = call_api("example_endpoint", ["not=valid"], FakeConfig())

        assert result == m_error_out.return_value
        assert m_error_out.call_count == 1
        arg = m_error_out.call_args[0][0]
        assert isinstance(arg, APIError)

        if options_cls:
            assert (
                arg.msg
                == API_MISSING_ARG.format(
                    arg="k", endpoint="example_endpoint"
                ).msg
            )
            assert arg.msg_code == API_MISSING_ARG.name
        else:
            assert (
                arg.msg
                == API_NO_ARG_FOR_ENDPOINT.format(
                    endpoint="example_endpoint"
                ).msg
            )
            assert arg.msg_code == API_NO_ARG_FOR_ENDPOINT.name

    @mock.patch("uaclient.api.api.check_for_new_version", return_value=None)
    @mock.patch("uaclient.api.api.import_module")
    def test_warning_on_extra_args(
        self, m_import_module, _m_new_version, FakeConfig
    ):
        mock_endpoint = mock.MagicMock()
        mock_endpoint.fn.return_value.warnings = []
        mock_endpoint.options_cls.fields = []

        m_import_module.return_value.endpoint = mock_endpoint

        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):
            result = call_api(
                "example_endpoint", ["extra=argument"], FakeConfig()
            )

        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert warning.title == API_UNKNOWN_ARG.format(arg="extra").msg
        assert warning.code == API_UNKNOWN_ARG.name
        assert warning.meta == {}

    @pytest.mark.parametrize(
        "options_cls,arguments",
        ((None, []), (mock.MagicMock(), ["key=value"])),
    )
    @mock.patch("uaclient.api.api.import_module")
    def test_call_endpoint(
        self, m_import_module, options_cls, arguments, FakeConfig
    ):
        mock_endpoint = mock.MagicMock()
        mock_endpoint.options_cls = options_cls

        mock_endpoint_fn = mock.MagicMock()
        mock_endpoint.fn = mock_endpoint_fn

        m_import_module.return_value.endpoint = mock_endpoint
        cfg = FakeConfig()

        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):
            result = call_api("example_endpoint", arguments, cfg)

        assert isinstance(result, APIResponse)
        assert result.result == "success"
        assert result.data.attributes == mock_endpoint_fn.return_value
        assert mock_endpoint_fn.call_count == 1
        if options_cls:
            assert options_cls.from_dict.call_args_list == [
                mock.call({"key": "value"})
            ]
            assert mock_endpoint_fn.call_args_list == [
                mock.call(options_cls.from_dict.return_value, cfg)
            ]
        else:
            assert mock_endpoint_fn.call_args_list == [mock.call(cfg)]

    @mock.patch("uaclient.api.api.error_out")
    @mock.patch("uaclient.api.api.import_module")
    def test_endpoint_function_error(
        self, m_import_module, m_error_out, FakeConfig
    ):
        mock_endpoint = mock.MagicMock()
        exception = UserFacingError(
            "something is wrong", "fn-specific", {"extra": "info"}
        )
        mock_endpoint.fn.side_effect = exception

        m_import_module.return_value.endpoint = mock_endpoint

        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):
            result = call_api("example_endpoint", [], FakeConfig())

        assert result == m_error_out.return_value
        assert m_error_out.call_count == 1
        assert m_error_out.call_args[0][0] == exception

    @pytest.mark.parametrize(
        "env_return,env_list",
        (
            ({}, []),
            (
                {"UA_EXAMPLE_KEY1": "value1", "UA_EXAMPLE_KEY2": "value2"},
                [
                    {"name": "UA_EXAMPLE_KEY1", "value": "value1"},
                    {"name": "UA_EXAMPLE_KEY2", "value": "value2"},
                ],
            ),
        ),
    )
    @mock.patch("uaclient.api.api.check_for_new_version", return_value=None)
    @mock.patch("uaclient.api.data_types.get_pro_environment")
    @mock.patch("uaclient.api.api.import_module")
    def test_endpoint_function_warning_and_meta(
        self,
        m_import_module,
        m_environment,
        _m_new_version_api,
        env_return,
        env_list,
        FakeConfig,
    ):
        m_environment.return_value = env_return
        mock_endpoint = mock.MagicMock()
        mock_endpoint.fn.return_value.warnings = [
            ErrorWarningObject(
                title="there is a warning",
                code="fn-specific",
                meta={"reason": "something"},
            )
        ]
        mock_endpoint.fn.return_value.meta = {"metadata": "information"}

        m_import_module.return_value.endpoint = mock_endpoint

        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):
            result = call_api("example_endpoint", [], FakeConfig())

        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert warning.title == "there is a warning"
        assert warning.code == "fn-specific"
        assert warning.meta == {"reason": "something"}

        assert len(result.data.meta) == 2
        assert result.data.meta == {
            "environment_vars": env_list,
            "metadata": "information",
        }

    @pytest.mark.parametrize("api_error", (False, True))
    @mock.patch("uaclient.api.api.check_for_new_version", return_value="1.2.3")
    @mock.patch(
        "uaclient.api.errors.check_for_new_version", return_value="1.2.3"
    )
    @mock.patch("uaclient.api.api.import_module")
    def test_warning_for_new_version(
        self,
        m_import_module,
        _m_new_version_error,
        _m_new_version_api,
        api_error,
        FakeConfig,
    ):
        mock_endpoint = mock.MagicMock()
        if api_error:
            exception = UserFacingError("something is wrong")
            mock_endpoint.fn.side_effect = exception
        else:
            mock_endpoint.fn.return_value.warnings = []

        m_import_module.return_value.endpoint = mock_endpoint

        with mock.patch(
            "uaclient.api.api.VALID_ENDPOINTS", ["example_endpoint"]
        ):

            result = call_api("example_endpoint", [], FakeConfig())

        assert len(result.warnings) == 1
        warning = result.warnings[0]
        assert (
            warning.title
            == WARN_NEW_VERSION_AVAILABLE.format(version="1.2.3").msg
        )
        assert warning.code == WARN_NEW_VERSION_AVAILABLE.name
        assert warning.meta == {}
