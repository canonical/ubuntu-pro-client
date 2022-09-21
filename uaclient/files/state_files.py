from typing import Any, Dict

from uaclient.data_types import BoolDataValue, DataObject, Field
from uaclient.files.data_types import DataObjectFile
from uaclient.files.files import UAFile

SERVICES_ONCE_ENABLED = "services-once-enabled"


class ServicesOnceEnabledData(DataObject):
    fields = [
        Field("fips_updates", BoolDataValue, False),
    ]

    def __init__(self, fips_updates: bool):
        self.fips_updates = fips_updates


def _services_once_enable_preprocess_data(
    data: Dict[str, Any]
) -> Dict[str, Any]:
    # Since we are using now returning DataObject instances from read, we
    # cannot have variables with "-" in them. We need to explictly convert
    # them before creating the object
    updated_data = {}
    for key in data.keys():
        if "-" in key:
            updated_data[key.replace("-", "_")] = True
        else:
            updated_data[key] = True

    return updated_data


services_once_enabled_file = DataObjectFile(
    data_object_cls=ServicesOnceEnabledData,
    ua_file=UAFile(
        name=SERVICES_ONCE_ENABLED,
        private=False,
    ),
    preprocess_data=_services_once_enable_preprocess_data,
)
