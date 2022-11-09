from importlib import import_module
from typing import Callable, List

from uaclient.api.data_types import APIData, APIResponse, ErrorWarningObject
from uaclient.api.errors import APIError, error_out
from uaclient.config import UAConfig
from uaclient.data_types import IncorrectFieldTypeError
from uaclient.messages import (
    API_BAD_ARGS_FORMAT,
    API_INVALID_ENDPOINT,
    API_MISSING_ARG,
    API_NO_ARG_FOR_ENDPOINT,
    API_UNKNOWN_ARG,
    WARN_NEW_VERSION_AVAILABLE,
)
from uaclient.version import check_for_new_version

VALID_ENDPOINTS = [
    "u.pro.attach.auto.configure_retry_service.v1",
    "u.pro.attach.auto.full_auto_attach.v1",
    "u.pro.attach.auto.should_auto_attach.v1",
    "u.pro.attach.magic.initiate.v1",
    "u.pro.attach.magic.revoke.v1",
    "u.pro.attach.magic.wait.v1",
    "u.pro.packages.summary.v1",
    "u.pro.packages.updates.v1",
    "u.pro.security.status.livepatch_cves.v1",
    "u.pro.security.status.reboot_required.v1",
    "u.pro.version.v1",
    "u.security.package_manifest.v1",
]


def call_api(
    endpoint_path: str, options: List[str], cfg: UAConfig
) -> APIResponse:
    if endpoint_path not in VALID_ENDPOINTS:
        return error_out(
            APIError(
                msg=API_INVALID_ENDPOINT.format(endpoint=endpoint_path).msg,
                msg_code=API_INVALID_ENDPOINT.name,
            )
        )

    module = import_module("uaclient.api." + endpoint_path)
    endpoint = module.endpoint

    option_warnings = []

    if endpoint.options_cls:
        kwargs = {}
        fields = [f.key for f in endpoint.options_cls.fields]

        for option in options:
            try:
                k, v = option.split("=")
            except ValueError:
                return error_out(
                    APIError(
                        msg=API_BAD_ARGS_FORMAT.format(arg=option).msg,
                        msg_code=API_BAD_ARGS_FORMAT.name,
                    )
                )

            if not k or not v:
                return error_out(
                    APIError(
                        msg=API_BAD_ARGS_FORMAT.format(arg=option).msg,
                        msg_code=API_BAD_ARGS_FORMAT.name,
                    )
                )

            if k not in fields:
                option_warnings.append(
                    ErrorWarningObject(
                        title=API_UNKNOWN_ARG.format(arg=k).msg,
                        code=API_UNKNOWN_ARG.name,
                        meta={},
                    )
                )

            kwargs[k] = v

        try:
            options = endpoint.options_cls.from_dict(kwargs)
        except IncorrectFieldTypeError as e:
            return error_out(
                APIError(
                    msg=API_MISSING_ARG.format(
                        arg=e.key, endpoint=endpoint_path
                    ).msg,
                    msg_code=API_MISSING_ARG.name,
                )
            )

        try:
            result = endpoint.fn(options, cfg)
        except Exception as e:
            return error_out(e)

    else:
        if options:
            return error_out(
                APIError(
                    msg=API_NO_ARG_FOR_ENDPOINT.format(
                        endpoint=endpoint_path
                    ).msg,
                    msg_code=API_NO_ARG_FOR_ENDPOINT.name,
                )
            )
        try:
            result = endpoint.fn(cfg)
        except Exception as e:
            return error_out(e)

    new_version = check_for_new_version()
    if new_version:
        option_warnings.append(
            ErrorWarningObject(
                title=WARN_NEW_VERSION_AVAILABLE.format(
                    version=new_version
                ).msg,
                code=WARN_NEW_VERSION_AVAILABLE.name,
                meta={},
            )
        )

    return APIResponse(
        _schema_version=endpoint.version,
        warnings=result.warnings + option_warnings,
        data=APIData(
            type=endpoint.name,
            attributes=result,
            meta=result.meta,
        ),
    )


class APIEndpoint:
    def __init__(
        self,
        version: str,
        name: str,
        fn: Callable,
        options_cls,
    ):
        self.version = version
        self.name = name
        self.fn = fn
        self.options_cls = options_cls
