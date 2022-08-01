import os.path

import mock
import pytest

from uaclient.version import (
    check_for_new_version,
    get_last_known_candidate,
    get_version,
)


@mock.patch("uaclient.version.subp")
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


class TestGetLastKnownCandidate:
    @mock.patch("builtins.open", mock.mock_open(read_data="1.2.3"))
    @mock.patch("os.stat")
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("uaclient.version.get_apt_cache_time", return_value=2)
    def test_get_known_candidate_from_cache(
        self, _m_apt_cache_time, _m_exists, m_stat
    ):
        m_stat.return_value.st_mtime = 1
        assert "1.2.3" == get_last_known_candidate()

    @mock.patch("builtins.open")
    @mock.patch("os.stat")
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("uaclient.version.get_apt_cache_time", return_value=2)
    def test_cant_open_cache_file(
        self, _m_apt_cache_time, _m_exists, m_stat, m_open
    ):
        m_stat.return_value.st_mtime = 1
        m_open.side_effect = OSError()
        assert None is get_last_known_candidate()

    @mock.patch("uaclient.version.get_apt_cache_policy_for_package")
    @mock.patch("os.path.exists", return_value=False)
    def test_create_cache_before_returning(self, _m_exists, m_policy):
        m_policy.return_value = """
            Installed: 1.1.2
            Candidate: 1.2.3
            Version table:
        """
        with mock.patch("builtins.open", mock.mock_open()) as m_open:
            get_last_known_candidate()
            assert m_open.return_value.write.call_args_list == [
                mock.call("1.2.3")
            ]

    @mock.patch("builtins.open")
    @mock.patch("uaclient.version.get_apt_cache_policy_for_package")
    @mock.patch("os.path.exists", return_value=False)
    def test_problem_updating_file(self, _m_exists, m_policy, m_open):
        m_policy.return_value = """
            Installed: 1.1.2
            Candidate: 1.2.3
            Version table:
        """
        m_open.side_effect = OSError()
        assert None is get_last_known_candidate()


class TestCheckForNewVersion:
    @pytest.mark.parametrize("compare_return", (True, False))
    @mock.patch("uaclient.version.compare_versions")
    @mock.patch("uaclient.version.get_last_known_candidate")
    def test_check_for_new_version(
        self, m_candidate, m_compare, compare_return
    ):
        m_compare.return_value = compare_return
        if compare_return:
            assert m_candidate.return_value == check_for_new_version()
        else:
            assert None is check_for_new_version()
