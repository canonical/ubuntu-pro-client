from typing import Dict, List, Union  # noqa: F401

from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.util import get_pro_environment
from uaclient.version import get_version


class AdditionalInfo:
    meta = {}  # type: Dict[str, str]
    warnings = []  # type: List[ErrorWarningObject]


class ErrorWarningObject(DataObject):
    fields = [
        Field("title", StringDataValue),
        Field("code", StringDataValue),
        Field("meta", DataObject),
    ]

    def __init__(self, *, title: str, code: str, meta: dict):
        self.title = title
        self.code = code
        self.meta = meta


class APIData(DataObject):
    fields = [
        Field("type", StringDataValue),
        Field("attributes", DataObject),
        Field("meta", DataObject),
    ]

    def __init__(self, *, type: str, attributes: DataObject, meta: dict):
        self.type = type
        self.attributes = attributes
        self.meta = {
            "environment_vars": [
                {"name": name, "value": value}
                for name, value in sorted(get_pro_environment().items())
            ],
            **meta,
        }


class APIResponse(DataObject):
    fields = [
        Field("_schema_version", StringDataValue),
        Field("result", StringDataValue),
        Field("version", StringDataValue),
        Field("errors", data_list(ErrorWarningObject)),
        Field("warnings", data_list(ErrorWarningObject)),
        Field("data", APIData),
    ]

    def __init__(
        self,
        *,
        _schema_version: str,
        result: str = "success",
        errors: List[ErrorWarningObject] = [],
        warnings: List[ErrorWarningObject] = [],
        data: Union[APIData, dict]
    ):
        self._schema_version = _schema_version
        self.result = result
        self.version = get_version()
        self.errors = errors
        self.warnings = warnings
        self.data = data
