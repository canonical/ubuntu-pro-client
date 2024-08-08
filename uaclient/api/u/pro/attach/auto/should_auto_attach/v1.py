from uaclient import exceptions
from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.apt import is_installed
from uaclient.clouds.identity import cloud_instance_factory
from uaclient.config import UAConfig
from uaclient.data_types import BoolDataValue, DataObject, Field


class ShouldAutoAttachResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "should_auto_attach",
            BoolDataValue,
            doc="True if the system should run auto-attach on boot",
        ),
    ]

    def __init__(self, should_auto_attach: bool):
        self.should_auto_attach = should_auto_attach


def should_auto_attach() -> ShouldAutoAttachResult:
    return _should_auto_attach(UAConfig())


def _should_auto_attach(cfg: UAConfig) -> ShouldAutoAttachResult:
    """
    This endpoint checks if a given system should run auto-attach on boot.
    """
    try:
        cloud_instance_factory()
    except exceptions.CloudFactoryError:
        return ShouldAutoAttachResult(
            should_auto_attach=False,
        )

    return ShouldAutoAttachResult(
        should_auto_attach=is_installed("ubuntu-advantage-pro")
        or is_installed("ubuntu-pro-auto-attach"),
    )


endpoint = APIEndpoint(
    version="v1",
    name="ShouldAutoAttach",
    fn=_should_auto_attach,
    options_cls=None,
)

_doc = {
    "introduced_in": "27.11",
    "requires_network": False,
    "example_python": """
from uaclient.api.u.pro.attach.auto.should_auto_attach.v1 import should_auto_attach

result = should_auto_attach()
""",  # noqa: E501
    "result_class": ShouldAutoAttachResult,
    "exceptions": [],
    "example_cli": "pro api u.pro.attach.auto.should_auto_attach.v1",
    "example_json": """
{
    "should_auto_attach": false
}
""",
}
