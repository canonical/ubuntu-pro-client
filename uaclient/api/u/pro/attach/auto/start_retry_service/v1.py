from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject
from uaclient.services import retry_auto_attach

StartRetryServiceOptions = FullAutoAttachOptions


class StartRetryServiceResult(DataObject, AdditionalInfo):
    pass


def start_retry_service(
    options: StartRetryServiceOptions,
) -> StartRetryServiceResult:
    return _start_retry_service(options, UAConfig())


def _start_retry_service(
    options: StartRetryServiceOptions, cfg: UAConfig
) -> StartRetryServiceResult:
    retry_auto_attach.OPTIONS_FILE.write(
        retry_auto_attach.RetryOptions(
            enable=options.enable, enable_beta=options.enable_beta
        )
    )
    retry_auto_attach.start()
    return StartRetryServiceResult()


endpoint = APIEndpoint(
    version="v1",
    name="StartRetryService",
    fn=_start_retry_service,
    options_cls=StartRetryServiceOptions,
)
