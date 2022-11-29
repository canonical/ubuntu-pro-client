import json
from enum import Enum
from typing import Callable, Dict, Generic, Optional, Type, TypeVar

import yaml

from uaclient import exceptions
from uaclient.data_types import DataObject
from uaclient.files.files import UAFile
from uaclient.util import DatetimeAwareJSONDecoder


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
    ):
        self.data_object_cls = data_object_cls
        self.ua_file = ua_file
        self.file_format = file_format
        self.preprocess_data = preprocess_data

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
                    self.ua_file.path, "json"
                )
        elif self.file_format == DataObjectFileFormat.YAML:
            try:
                parsed_data = yaml.safe_load(raw_data)
            except yaml.parser.ParserError:
                raise exceptions.InvalidFileFormatError(
                    self.ua_file.path, "yaml"
                )

        if parsed_data is None:
            return None

        if self.preprocess_data:
            parsed_data = self.preprocess_data(parsed_data)

        return self.data_object_cls.from_dict(parsed_data)

    def write(self, content: DOFType):
        if self.file_format == DataObjectFileFormat.JSON:
            str_content = content.to_json()
        elif self.file_format == DataObjectFileFormat.YAML:
            data = content.to_dict()
            str_content = yaml.dump(data, default_flow_style=False)

        self.ua_file.write(str_content)

    def delete(self):
        self.ua_file.delete()
