import mock
import pytest

from uaclient import exceptions, gpg
from uaclient.testing import helpers


class TestExportGPGKey:
    @pytest.mark.parametrize(
        ["source_exists", "expected_raises"],
        [
            (True, helpers.does_not_raise()),
            (False, pytest.raises(exceptions.GPGKeyNotFound)),
        ],
    )
    @mock.patch("uaclient.gpg.shutil.copy")
    @mock.patch("uaclient.gpg.os.chmod")
    @mock.patch("uaclient.gpg.os.path.exists")
    def test_export_gpg_key(
        self,
        m_exists,
        m_chmod,
        m_copy,
        source_exists,
        expected_raises,
    ):
        m_exists.return_value = source_exists
        with expected_raises:
            gpg.export_gpg_key(mock.sentinel.source, mock.sentinel.dest)
            assert m_copy.call_args_list == [
                mock.call(mock.sentinel.source, mock.sentinel.dest)
            ]
            assert m_chmod.call_args_list == [
                mock.call(mock.sentinel.dest, 0o644)
            ]
