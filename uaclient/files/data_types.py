import json
from enum import Enum
from typing import Callable, Dict, Generic, Optional, Type, TypeVar

from uaclient import exceptions
from uaclient.data_types import DataObject
from uaclient.files.files import UAFile
from uaclient.util import DatetimeAwareJSONDecoder
from uaclient.yaml import parser as yaml_parser
from uaclient.yaml import safe_dump, safe_load


class DataObjectFileFormat(Enum):
    JSON = "json"
    YAML = "yaml"


DOFType = TypeVar("DOFType", bound=DataObject)


class DataObjectFile(Generic[DOFType]):
    def __init__(
        self,
        data_object_cls: Type[DOFType],
        ua_file: UAFile,
        file_format: DataObjectFileFormat = DataObjectFileFormat.JSON,
        preprocess_data: Optional[Callable[[Dict], Dict]] = None,
        optional_type_errors_become_null: bool = False,
    ):
        self.data_object_cls = data_object_cls
        self.ua_file = ua_file
        self.file_format = file_format
        self.preprocess_data = preprocess_data
        self.optional_type_errors_become_null = (
            optional_type_errors_become_null
        )

    def read(self) -> Optional[DOFType]:
        raw_data = self.ua_file.read()
        if raw_data is None:
            return None

        parsed_data = None
        if self.file_format == DataObjectFileFormat.JSON:
            try:
                parsed_data = json.loads(
                    raw_data, cls=DatetimeAwareJSONDecoder
                )
            except json.JSONDecodeError:
                raise exceptions.InvalidFileFormatError(
                    file_name=self.ua_file.path, file_format="json"
                )
        elif self.file_format == DataObjectFileFormat.YAML:
            try:
                parsed_data = safe_load(raw_data)
            except yaml_parser.ParserError:
                raise exceptions.InvalidFileFormatError(
                    file_name=self.ua_file.path, file_format="yaml"
                )

        if parsed_data is None:
            return None

        if self.preprocess_data:
            parsed_data = self.preprocess_data(parsed_data)

        return self.data_object_cls.from_dict(
            parsed_data,
            optional_type_errors_become_null=self.optional_type_errors_become_null,  # noqa: E501
        )

    def write(self, content: DOFType):
        if self.file_format == DataObjectFileFormat.JSON:
            str_content = content.to_json()
        elif self.file_format == DataObjectFileFormat.YAML:
            data = content.to_dict()
            str_content = safe_dump(data, default_flow_style=False)

        self.ua_file.write(str_content)

    def delete(self):
        self.ua_file.delete()

    @property
    def path(self):
        return self.ua_file.path
