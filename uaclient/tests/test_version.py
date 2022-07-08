import os.path

import mock

from uaclient.version import get_version


@mock.patch("uaclient.util.subp")
class TestGetVersion:
    @mock.patch("uaclient.version.os.path.exists", return_value=True)
    def test_get_version_returns_packaged_version(self, m_exists, m_subp):
        with mock.patch("uaclient.version.PACKAGED_VERSION", "24.1~18.04.1"):
            assert "24.1~18.04.1" == get_version()
        assert 0 == m_subp.call_count

    @mock.patch("uaclient.version.os.path.exists", return_value=True)
    def test_get_version_returns_matching_git_describe_long(
        self, m_exists, m_subp
    ):
        m_subp.return_value = ("24.1-5-g12345678", "")
        with mock.patch(
            "uaclient.version.PACKAGED_VERSION", "@@PACKAGED_VERSION"
        ):
            assert "24.1-5-g12345678" == get_version()
        assert [
            mock.call(
                ["git", "describe", "--abbrev=8", "--match=[0-9]*", "--long"]
            )
        ] == m_subp.call_args_list
        top_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        top_dir_git = os.path.join(top_dir, ".git")
        assert [mock.call(top_dir_git)] == m_exists.call_args_list
