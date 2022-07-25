import os

import mock
import pytest

from uaclient import exceptions, system
from uaclient.data_types import (
    DataObject,
    Field,
    IncorrectFieldTypeError,
    IntDataValue,
    StringDataValue,
)
from uaclient.files import (
    DataObjectFile,
    DataObjectFileFormat,
    MachineTokenFile,
    UAFile,
)


class MockUAFile:
    def __init__(self):
        self.write = mock.MagicMock()
        self.read = mock.MagicMock()
        self.delete = mock.MagicMock()
        self.path = mock.MagicMock()


class TestUAFile:
    def test_read_write(self, tmpdir):
        file_name = "temp_file"
        file = UAFile(file_name, tmpdir.strpath, False)
        content = "dummy file words"
        file.write(content)
        path = os.path.join(tmpdir.strpath, file_name)
        res = system.load_file(path)
        assert res == file.read()
        assert res == content


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


class TestMachineTokenFile:
    def test_deleting(self, tmpdir):
        token_file = MachineTokenFile(
            directory=tmpdir.strpath,
        )
        token = {"machineTokenInfo": {"machineId": "random-id"}}
        token_file.write(token)
        assert token_file.machine_token == token
        token_file.delete()
        assert token_file.machine_token is None

    def test_public_file_filtering(self, tmpdir):
        # root access of machine token file
        token_file = MachineTokenFile(
            directory=tmpdir.strpath,
        )
        token = {
            "machineTokenInfo": {"machineId": "random-id"},
            "machineToken": "token",
        }
        token_file.write(token)
        root_token = token_file.machine_token
        assert token == root_token
        # non root access of machine token file
        token_file = MachineTokenFile(
            directory=tmpdir.strpath, root_mode=False
        )
        nonroot_token = token_file.machine_token
        assert root_token != nonroot_token
        machine_token = nonroot_token.get("machineToken", None)
        assert machine_token is None
