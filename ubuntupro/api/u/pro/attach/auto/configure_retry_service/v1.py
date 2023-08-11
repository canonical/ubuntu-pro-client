from uaclient import system
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from uaclient.config import UAConfig
from uaclient.daemon import retry_auto_attach
from uaclient.data_types import DataObject
from uaclient.files import state_files

ConfigureRetryServiceOptions = FullAutoAttachOptions


class ConfigureRetryServiceResult(DataObject, AdditionalInfo):
    pass


def configure_retry_service(
    options: ConfigureRetryServiceOptions,
) -> ConfigureRetryServiceResult:
    return _configure_retry_service(options, UAConfig())


def _configure_retry_service(
    options: ConfigureRetryServiceOptions, cfg: UAConfig
) -> ConfigureRetryServiceResult:
    state_files.retry_auto_attach_options_file.write(
        state_files.RetryAutoAttachOptions(
            enable=options.enable, enable_beta=options.enable_beta
        )
    )
    system.create_file(retry_auto_attach.FLAG_FILE_PATH)
    return ConfigureRetryServiceResult()


endpoint = APIEndpoint(
    version="v1",
    name="ConfigureRetryService",
    fn=_configure_retry_service,
    options_cls=ConfigureRetryServiceOptions,
)
