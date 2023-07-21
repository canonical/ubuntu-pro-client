from uaclient import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.apt import is_installed
from uaclient.clouds.identity import cloud_instance_factory
from uaclient.config import UAConfig
from uaclient.data_types import BoolDataValue, DataObject, Field


class ShouldAutoAttachResult(DataObject, AdditionalInfo):
    fields = [
        Field("should_auto_attach", BoolDataValue),
    ]

    def __init__(self, should_auto_attach: bool):
        self.should_auto_attach = should_auto_attach


def should_auto_attach() -> ShouldAutoAttachResult:
    return _should_auto_attach(UAConfig())


def _should_auto_attach(cfg: UAConfig) -> ShouldAutoAttachResult:
    try:
        cloud_instance_factory()
    except exceptions.CloudFactoryError:
        return ShouldAutoAttachResult(
            should_auto_attach=False,
        )

    return ShouldAutoAttachResult(
        should_auto_attach=is_installed("ubuntu-advantage-pro"),
    )


endpoint = APIEndpoint(
    version="v1",
    name="ShouldAutoAttach",
    fn=_should_auto_attach,
    options_cls=None,
)
