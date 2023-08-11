import mock
import pytest

from ubuntupro import exceptions
from ubuntupro.data_types import (
    DataObject,
    Field,
    IncorrectFieldTypeError,
    IntDataValue,
    StringDataValue,
)
from ubuntupro.files.data_types import DataObjectFile, DataObjectFileFormat


class MockUAFile:
    def __init__(self):
        self.write = mock.MagicMock()
        self.read = mock.MagicMock()
        self.delete = mock.MagicMock()
        self.path = mock.MagicMock()


class NestedTestData(DataObject):
    fields = [
        Field("integer", IntDataValue),
    ]

    def __init__(self, integer: int):
        self.integer = integer


class TestData(DataObject):
    fields = [
        Field("string", StringDataValue),
        Field("nested", NestedTestData),
    ]

    def __init__(self, string: str, nested: NestedTestData):
        self.string = string
        self.nested = nested


class TestDataObjectFile:
    def test_write_valid_json(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
        )
        dof.write(TestData(string="test", nested=NestedTestData(integer=1)))
        assert mock_file.write.call_args_list == [
            mock.call("""{"nested": {"integer": 1}, "string": "test"}""")
        ]

    def test_write_valid_yaml(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
            DataObjectFileFormat.YAML,
        )
        dof.write(TestData(string="test", nested=NestedTestData(integer=1)))
        assert mock_file.write.call_args_list == [
            mock.call("""nested:\n  integer: 1\nstring: test\n""")
        ]

    def test_read_valid_json(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
        )
        mock_file.read.return_value = (
            """{"string": "test", "nested": {"integer": 1}}"""
        )
        do = dof.read()
        assert do.string == "test"
        assert do.nested.integer == 1

    def test_read_valid_yaml(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
            DataObjectFileFormat.YAML,
        )
        mock_file.read.return_value = (
            """nested:\n  integer: 1\nstring: test\n"""
        )
        do = dof.read()
        assert do.string == "test"
        assert do.nested.integer == 1

    def test_read_invalid_data(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
        )
        mock_file.read.return_value = """{"nested": {"integer": 1}}"""
        with pytest.raises(IncorrectFieldTypeError):
            dof.read()

    def test_read_invalid_json(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
        )
        mock_file.read.return_value = """{"nested": {"""
        with pytest.raises(exceptions.InvalidFileFormatError):
            dof.read()

    def test_read_invalid_yaml(self):
        mock_file = MockUAFile()
        dof = DataObjectFile(
            TestData,
            mock_file,
            DataObjectFileFormat.YAML,
        )
        mock_file.read.return_value = """nested": {"""
        with pytest.raises(exceptions.InvalidFileFormatError):
            dof.read()
