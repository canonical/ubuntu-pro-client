import os

import pytest

from uaclient.files import MachineTokenFile, UAFile


class TestUAFile:
    @pytest.mark.parametrize("private", (False, True))
    def test_default_file_details(self, m_private, tmpdir):
        file = UAFile(root_directory=tmpdir.strpath, private=m_private)
        assert 1 == 1


class TestMachineTokenFile:
    def test_basic(self):
        assert 1 == 1
