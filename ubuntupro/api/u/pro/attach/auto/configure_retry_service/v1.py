from ubuntupro import system
from ubuntupro.api.api import APIEndpoint
from ubuntupro.api.data_types import AdditionalInfo
from ubuntupro.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from ubuntupro.config import UAConfig
from ubuntupro.daemon import retry_auto_attach
from ubuntupro.data_types import DataObject
from ubuntupro.files import state_files

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
