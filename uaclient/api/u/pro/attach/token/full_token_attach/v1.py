from typing import Dict, List  # noqa: F401

from uaclient import exceptions, lock, util
from uaclient.actions import attach_with_token
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo, ErrorWarningObject
from uaclient.api.u.pro.security.status.reboot_required.v1 import (
    _reboot_required,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    StringDataValue,
    data_list,
)


class FullTokenAttachOptions(DataObject):
    fields = [
        Field(
            "token",
            StringDataValue,
            doc="The token associated with a Pro subscription",
        ),
        Field(
            "auto_enable_services",
            BoolDataValue,
            False,
            doc=(
                "If false, the attach operation will not enable any service"
                " during the operation (default: true)"
            ),
        ),
    ]

    def __init__(self, token: str, auto_enable_services: bool = True):
        self.token = token
        self.auto_enable_services = auto_enable_services


class FullTokenAttachResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "enabled",
            data_list(StringDataValue),
            doc="The services enabled during the attach operation",
        ),
        Field(
            "reboot_required",
            BoolDataValue,
            doc=(
                "True if the system requires a reboot after the attach"
                " operation"
            ),
        ),
    ]

    def __init__(
        self,
        enabled: List[str],
        reboot_required: bool,
    ):
        self.enabled = enabled
        self.reboot_required = reboot_required


def _full_token_attach(
    options: FullTokenAttachOptions, cfg: UAConfig
) -> FullTokenAttachResult:
    """
    This endpoint allows the user to attach to a Pro subscription using a
    token.
    """
    if not util.we_are_currently_root():
        raise exceptions.NonRootUserError

    if _is_attached(cfg).is_attached:
        return FullTokenAttachResult(
            enabled=[],
            reboot_required=False,
        )

    try:
        with lock.RetryLock(
            lock_holder="pro.api.u.pro.attach.token.full_token_attach.v1",
        ):
            ret = _full_token_attach_in_lock(options, cfg)
    except Exception as e:
        lock.clear_lock_file_if_present()
        raise e
    return ret


def _full_token_attach_in_lock(
    options: FullTokenAttachOptions, cfg: UAConfig
) -> FullTokenAttachResult:
    failed_services = []  # type: List[Dict[str, str]]

    auto_enable_services = options.auto_enable_services
    if auto_enable_services is None:
        auto_enable_services = True

    try:
        attach_with_token(
            cfg,
            options.token,
            allow_enable=auto_enable_services,
            silent=True,
        )
    except (
        exceptions.AttachFailureUnknownError,
        exceptions.AttachFailureDefaultServices,
    ) as exc:
        failed_services = exc.additional_info.get("services", [])

    enabled_services = [
        service.name for service in _enabled_services(cfg).enabled_services
    ]
    reboot_required_result = _reboot_required(cfg)

    result = FullTokenAttachResult(
        enabled=enabled_services,
        reboot_required=reboot_required_result.reboot_required == "yes",
    )

    if failed_services:
        result.warnings = [
            ErrorWarningObject(
                title=service["title"],
                code=service["code"],
                meta={"service": service["name"]},
            )
            for service in failed_services
        ]

    return result


def full_token_attach(
    options: FullTokenAttachOptions,
) -> FullTokenAttachResult:
    return _full_token_attach(options, UAConfig())


endpoint = APIEndpoint(
    version="v1",
    name="FullTokenAttach",
    fn=_full_token_attach,
    options_cls=FullTokenAttachOptions,
)

_doc = {
    "introduced_in": "32",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.attach.token.full_token_attach.v1 import full_token_attach, FullTokenAttachOptions

options = FullTokenAttachOptions(token="TOKEN")
result = full_token_attach(options)
""",  # noqa: E501
    "result_class": FullTokenAttachResult,
    "exceptions": [
        (
            exceptions.ConnectivityError,
            (
                "Raised if it is not possible to connect to the contracts"
                " service."
            ),
        ),
        (
            exceptions.ContractAPIError,
            (
                "Raised if there is an unexpected error in the contracts"
                " service interaction."
            ),
        ),
        (
            exceptions.LockHeldError,
            (
                "Raised if another Client process is holding the lock on the"
                " machine."
            ),
        ),
        (
            exceptions.NonRootUserError,
            ("Raised if a non-root user executes this endpoint."),
        ),
    ],
    "example_cli": "pro api u.pro.attach.token.full_token_attach.v1 --data -",
    "example_cli_extra": """
Note that it is generally not recommended to pass secrets such as the token on
the command line. The example uses the arguments ``--data -`` which causes
``pro`` to read the input data from ``stdin``. Then the arguments can be
written as JSON to ``stdin`` of the process.

For example, if we define a JSON file (i.e. ``file.json``) with the same
attributes as the options for this endpoint:

.. code-block:: json

    {
        "token": "TOKEN",
        "auto_enable_services": false
    }

Then we can call the API like this:

.. code-block:: bash

    cat file.json | pro api u.pro.attach.token.full_token_attach.v1 --data -
""",
    "example_json": """
{
    "enabled": ["service1", "service2"],
    "reboot_required": false
}
""",
}
