import mock

import pytest

import os.path

from uaclient import util
from uaclient.version import get_version


@mock.patch("uaclient.util.subp")
class TestGetVersion:

    @pytest.mark.parametrize(
        "features,suffix", (({}, ""), ({"on": True}, " +on"))
    )
    @mock.patch("uaclient.version.os.path.exists", return_value=True)
    def test_get_version_returns_packaged_version(
        self, m_exists, m_subp, features, suffix
    ):
        with mock.patch("uaclient.version.PACKAGED_VERSION", "24.1~18.04.1"):
            assert "24.1~18.04.1" + suffix == get_version(features=features)
        assert 0 == m_subp.call_count

    @mock.patch("uaclient.version.PACKAGED_VERSION", "@@PACKAGED_VERSION")
    @mock.patch("uaclient.version.os.path.exists", return_value=True)
    def test_get_version_returns_matching_git_describe_long(
        self, m_exists, m_subp
    ):
        m_subp.return_value = ("24.1-5-g12345678", "")
        assert "24.1-5-g12345678" == get_version()
        assert [
            mock.call(
                ["git", "describe", "--abbrev=8", "--match=[0-9]*", "--long"]
            )
        ] == m_subp.call_args_list
        top_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        top_dir_git = os.path.join(top_dir, ".git")
        assert [mock.call(top_dir_git)] == m_exists.call_args_list

    @mock.patch("uaclient.version.PACKAGED_VERSION", "@@PACKAGED_VERSION")
    @mock.patch("uaclient.version.os.path.exists", return_value=True)
    def test_returns_dpkg_parsechangelog_on_git_ubuntu_pkg_branch(
        self, m_exists, m_subp
    ):
        """Call dpkg-parsechangelog if git describe fails to --match=[0-9]*"""

        def fake_subp(cmd):
            if cmd[0] == "git":
                # Not matching tag on git-ubuntu pkg branches
                raise util.ProcessExecutionError(
                    "fatal: No names found, cannot describe anything."
                )
            if cmd[0] == "dpkg-parsechangelog":
                return ("24.1\n", "")
            assert False, "Unexpected subp cmd {}".format(cmd)

        m_subp.side_effect = fake_subp

        assert "24.1" == get_version()
        expected_calls = [
            mock.call(
                ["git", "describe", "--abbrev=8", "--match=[0-9]*", "--long"]
            ),
            mock.call(["dpkg-parsechangelog", "-S", "version"]),
        ]
        assert expected_calls == m_subp.call_args_list
        top_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        top_dir_git = os.path.join(top_dir, ".git")
        assert [mock.call(top_dir_git)] == m_exists.call_args_list
