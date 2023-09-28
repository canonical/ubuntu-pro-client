import json
from importlib import import_module
from typing import Any, Callable, Dict, List, Tuple

from uaclient.api import errors
from uaclient.api.data_types import APIData, APIResponse, ErrorWarningObject
from uaclient.config import UAConfig
from uaclient.data_types import IncorrectFieldTypeError
from uaclient.messages import API_UNKNOWN_ARG, WARN_NEW_VERSION_AVAILABLE
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
    "u.pro.security.fix.cve.execute.v1",
    "u.pro.security.fix.cve.plan.v1",
    "u.pro.security.fix.usn.execute.v1",
    "u.pro.security.fix.usn.plan.v1",
    "u.pro.security.status.livepatch_cves.v1",
    "u.pro.security.status.reboot_required.v1",
    "u.pro.status.enabled_services.v1",
    "u.pro.status.is_attached.v1",
    "u.pro.version.v1",
    "u.security.package_manifest.v1",
    "u.unattended_upgrades.status.v1",
    "u.apt_news.current_news.v1",
]


def _process_options(
    options: List[str], fields: List[str]
) -> Tuple[Dict[str, Any], List[ErrorWarningObject]]:
    kwargs = {}
    warnings = []

    for option in options:
        try:
            k, v = option.split("=")
        except ValueError:
            raise errors.APIBadArgsFormat(arg=option)

        if not k or not v:
            raise errors.APIBadArgsFormat(arg=option)

        if k not in fields:
            warnings.append(
                ErrorWarningObject(
                    title=API_UNKNOWN_ARG.format(arg=k).msg,
                    code=API_UNKNOWN_ARG.name,
                    meta={},
                )
            )

        kwargs[k] = v

    return kwargs, warnings


def _process_data(
    data: str, fields: List[str]
) -> Tuple[Dict[str, Any], List[ErrorWarningObject]]:
    kwargs = {}
    warnings = []

    try:
        json_data = json.loads(data)
    except json.decoder.JSONDecodeError:
        raise errors.APIJSONDataFormatError(data=data)

    for k, v in json_data.items():
        if not k or not v:
            raise errors.APIBadArgsFormat(arg="{}:{}".format(k, v))

        if k not in fields:
            warnings.append(
                ErrorWarningObject(
                    title=API_UNKNOWN_ARG.format(arg=k).msg,
                    code=API_UNKNOWN_ARG.name,
                    meta={},
                )
            )

        kwargs[k] = v

    return kwargs, warnings


def call_api(
    endpoint_path: str, options: List[str], data: str, cfg: UAConfig
) -> APIResponse:

    if endpoint_path not in VALID_ENDPOINTS:
        return errors.error_out(
            errors.APIInvalidEndpoint(endpoint=endpoint_path)
        )

    module = import_module("uaclient.api." + endpoint_path)
    endpoint = module.endpoint

    option_warnings = []

    if endpoint.options_cls:
        fields = [f.key for f in endpoint.options_cls.fields]
        try:
            if options:
                kwargs, warnings = _process_options(options, fields)
            elif data:
                kwargs, warnings = _process_data(data, fields)
            else:
                kwargs, warnings = {}, []
            option_warnings.extend(warnings)
        except errors.APIError as e:
            return errors.error_out(e)

        try:
            options = endpoint.options_cls.from_dict(kwargs)
        except IncorrectFieldTypeError as e:
            return errors.error_out(
                errors.APIMissingArg(arg=e.key, endpoint=endpoint_path)
            )

        try:
            result = endpoint.fn(options, cfg)
        except Exception as e:
            return errors.error_out(e)

    else:
        if options or data:
            return errors.error_out(
                errors.APINoArgsForEndpoint(endpoint=endpoint_path)
            )
        try:
            result = endpoint.fn(cfg)
        except Exception as e:
            return errors.error_out(e)

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
