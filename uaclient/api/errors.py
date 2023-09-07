from uaclient import messages
from uaclient.api.data_types import APIResponse, ErrorWarningObject
from uaclient.exceptions import UbuntuProError
from uaclient.util import get_pro_environment
from uaclient.version import check_for_new_version


def error_out(exception: Exception) -> APIResponse:
    if isinstance(exception, (UbuntuProError, APIError)):
        error = ErrorWarningObject(
            title=exception.msg,
            code=exception.msg_code
            or "generic-" + exception.__class__.__name__,
            meta=exception.additional_info or {},
        )
    else:
        error = ErrorWarningObject(
            title=str(exception),
            code="generic-" + exception.__class__.__name__,
            meta={},
        )

    warnings = []
    new_version = check_for_new_version()
    if new_version:
        warnings.append(
            ErrorWarningObject(
                title=messages.WARN_NEW_VERSION_AVAILABLE.format(
                    version=new_version
                ).msg,
                code=messages.WARN_NEW_VERSION_AVAILABLE.name,
                meta={},
            )
        )

    return APIResponse(
        _schema_version="v1",
        result="failure",
        data={
            "meta": {
                "environment_vars": [
                    {"name": name, "value": value}
                    for name, value in sorted(get_pro_environment().items())
                ],
            }
        },
        errors=[error],
        warnings=warnings,
    )


class APIError(UbuntuProError):
    pass


class APIInvalidEndpoint(APIError):
    _formatted_msg = messages.E_API_INVALID_ENDPOINT


class APIMissingArg(APIError):
    _formatted_msg = messages.E_API_MISSING_ARG


class APINoArgsForEndpoint(APIError):
    _formatted_msg = messages.E_API_NO_ARG_FOR_ENDPOINT


class APIJSONDataFormatError(APIError):
    _formatted_msg = messages.E_API_JSON_DATA_FORMAT_ERROR


class APIBadArgsFormat(APIError):
    _formatted_msg = messages.E_API_BAD_ARGS_FORMAT
