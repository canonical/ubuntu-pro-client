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
    """
    This endpoint configures options for the retry auto-attach functionality,
    and creates files that will activate the retry auto-attach functionality
    if ``ubuntu-advantage.service`` runs.

    Note that this does not start ``ubuntu-advantage.service``. This makes it
    useful for calling during the boot process
    ``Before: ubuntu-advantage.service`` so that when
    ``ubuntu-advantage.service`` starts, its ``ConditionPathExists`` check
    passes and activates the retry auto-attach function.

    If you call this function outside of the boot process and would like the
    retry auto-attach functionality to actually start, you'll need to call
    something like ``systemctl start ubuntu-advantage.service``.
    """
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

_doc = {
    "introduced_in": "27.12",
    "requires_network": False,
    "extra_args_content": """
.. note::

    If none of the lists are set, the services will be enabled based on the
    contract definitions.
""",
    "example_python": """
from uaclient.api.u.pro.attach.auto.configure_retry_service.v1 import configure_retry_service, ConfigureRetryServiceOptions

options = ConfigureRetryServiceOptions(enable=["<service1>", "<service2>"], enable_beta=["<beta_service3>"])
result = configure_retry_service(options)
""",  # noqa: E501
    "result_class": ConfigureRetryServiceResult,
    "exceptions": [],
    "example_cli": 'pro api u.pro.attach.auto.configure_retry_service.v1 --data {"enable": ["esm-infra", "esm-apps"]}',  # noqa: E501
    "example_json": """
{}
""",
}
