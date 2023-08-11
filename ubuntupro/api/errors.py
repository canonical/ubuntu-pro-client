from typing import Dict, Optional

from uaclient.api.data_types import APIResponse, ErrorWarningObject
from uaclient.exceptions import UserFacingError
from uaclient.messages import WARN_NEW_VERSION_AVAILABLE
from uaclient.util import get_pro_environment
from uaclient.version import check_for_new_version


def error_out(exception: Exception) -> APIResponse:
    if isinstance(exception, (UserFacingError, APIError)):
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
                title=WARN_NEW_VERSION_AVAILABLE.format(
                    version=new_version
                ).msg,
                code=WARN_NEW_VERSION_AVAILABLE.name,
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


class APIError(UserFacingError):
    def __init__(
        self,
        msg: str,
        msg_code: str = "api-error",
        additional_info: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(msg, msg_code, additional_info)
