import os

from uaclient import util
from uaclient.files import MachineTokenFile, UAFile


class TestUAFile:
    def test_read_write(self, tmpdir):
        file_name = "temp_file"
        file = UAFile(file_name, tmpdir.strpath, False)
        content = "dummy file words"
        file.write(content)
        path = os.path.join(tmpdir.strpath, file_name)
        res = util.load_file(path)
        assert res == file.read()
        assert res == content


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
