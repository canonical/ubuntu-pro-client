"""Tests related to uaclient.apt module."""

import glob
import mock
import os
import stat
import subprocess
from textwrap import dedent

import pytest

from uaclient.apt import (
    APT_KEYS_DIR,
    APT_AUTH_COMMENT,
    KEYRINGS_DIR,
    add_apt_auth_conf_entry,
    add_auth_apt_repo,
    add_ppa_pinning,
    clean_apt_files,
    find_apt_list_files,
    get_installed_packages,
    remove_apt_list_files,
    remove_auth_apt_repo,
    remove_repo_from_apt_auth_file,
    assert_valid_apt_credentials,
    run_apt_command,
)
from uaclient import apt, exceptions, util, status
from uaclient.entitlements.tests.test_repo import RepoTestEntitlement
from uaclient.entitlements.repo import RepoEntitlement
from uaclient.entitlements.base import UAEntitlement


POST_INSTALL_APT_CACHE_NO_UPDATES = """
-32768 https://esm.ubuntu.com/ubuntu/ {0}-updates/main amd64 Packages
     release v=14.04,o={1},a={0}-updates,n={0},l=UbuntuESM,c=main
     origin esm.ubuntu.com
"""


class TestAddPPAPinning:
    @mock.patch("uaclient.util.get_platform_info")
    def test_write_apt_pin_file_to_apt_preferences(self, m_platform, tmpdir):
        """Write proper apt pin file to specified apt_preference_file."""
        m_platform.return_value = {"series": "xenial"}
        pref_file = tmpdir.join("preffile").strpath
        assert None is add_ppa_pinning(
            pref_file,
            repo_url="http://fakerepo",
            origin="MYORIG",
            priority=1003,
        )
        expected_pref = dedent(
            """\
            Package: *
            Pin: release o=MYORIG, n=xenial
            Pin-Priority: 1003\n"""
        )
        assert expected_pref == util.load_file(pref_file)


class TestFindAptListFilesFromRepoSeries:
    @mock.patch("uaclient.util.subp")
    def test_find_all_apt_list_files_from_apt_config_key(self, m_subp, tmpdir):
        """Find all matching apt list files from apt-config dir."""
        m_subp.return_value = ("key='{}'".format(tmpdir.strpath), "")
        repo_url = "http://c.com/fips-updates/"
        _protocol, repo_path = repo_url.split("://")
        prefix = repo_path.rstrip("/").replace("/", "_")
        paths = sorted(
            [
                tmpdir.join(prefix + "_dists_nomatch").strpath,
                tmpdir.join(prefix + "_dists_xenial_InRelease").strpath,
                tmpdir.join(
                    prefix + "_dists_xenial_main_binary-amd64_Packages"
                ).strpath,
            ]
        )
        for path in paths:
            util.write_file(path, "")

        assert paths[1:] == find_apt_list_files(repo_url, "xenial")


class TestRemoveAptListFiles:
    @mock.patch("uaclient.util.subp")
    def test_remove_all_apt_list_files_from_apt_config_key(
        self, m_subp, tmpdir
    ):
        """Remove all matching apt list files from apt-config dir."""
        m_subp.return_value = ("key='{}'".format(tmpdir.strpath), "")
        repo_url = "http://c.com/fips-updates/"
        _protocol, repo_path = repo_url.split("://")
        prefix = repo_path.rstrip("/").replace("/", "_")
        nomatch_file = tmpdir.join(prefix + "_dists_nomatch").strpath
        paths = [
            nomatch_file,
            tmpdir.join(prefix + "_dists_xenial_InRelease").strpath,
            tmpdir.join(
                prefix + "_dists_xenial_main_binary-amd64_Packages"
            ).strpath,
        ]
        for path in paths:
            util.write_file(path, "")

        assert None is remove_apt_list_files(repo_url, "xenial")
        assert [nomatch_file] == glob.glob("{}/*".format(tmpdir.strpath))


class TestValidAptCredentials:
    @mock.patch("uaclient.util.subp")
    @mock.patch("os.path.exists", return_value=False)
    def test_passes_when_missing_apt_helper(self, m_exists, m_subp):
        """When apt-helper tool is absent perform no validation."""
        assert None is assert_valid_apt_credentials(
            repo_url="http://fakerepo", username="username", password="pass"
        )
        expected_calls = [mock.call("/usr/lib/apt/apt-helper")]
        assert expected_calls == m_exists.call_args_list
        assert 0 == m_subp.call_count

    @mock.patch("uaclient.apt.tempfile.TemporaryDirectory")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.os.path.exists", return_value=True)
    def test_passes_on_valid_creds(
        self, m_exists, m_subp, m_temporary_directory
    ):
        """Succeed when apt-helper succeeds in authenticating to repo."""
        m_temporary_directory.return_value.__enter__.return_value = (
            "/does/not/exist"
        )
        # Success apt-helper response
        m_subp.return_value = "Get:1 https://fakerepo\nFetched 285 B in 1s", ""

        assert None is assert_valid_apt_credentials(
            repo_url="http://fakerepo", username="user", password="pwd"
        )
        exists_calls = [mock.call("/usr/lib/apt/apt-helper")]
        assert exists_calls == m_exists.call_args_list
        expected_path = os.path.join(
            m_temporary_directory.return_value.__enter__.return_value,
            "apt-helper-output",
        )
        apt_helper_call = mock.call(
            [
                "/usr/lib/apt/apt-helper",
                "download-file",
                "http://user:pwd@fakerepo/ubuntu/pool/",
                expected_path,
            ],
            timeout=60,
        )
        assert [apt_helper_call] == m_subp.call_args_list

    @pytest.mark.parametrize(
        "exit_code,stderr,error_msg",
        (
            (
                1,
                "something broke",
                "Unexpected APT error. See /var/log/ubuntu-advantage.log",
            ),
            (
                100,
                "E: Failed to fetch ... HttpError401 on trusty",
                "Invalid APT credentials provided for http://fakerepo",
            ),
            (
                100,
                "E: Failed to fetch ... 401 Unauthorized on xenial",
                "Invalid APT credentials provided for http://fakerepo",
            ),
            (
                100,
                "E: Failed to fetch ... Connection timed out",
                "Timeout trying to access APT repository at http://fakerepo",
            ),
        ),
    )
    @mock.patch("uaclient.apt.tempfile.TemporaryDirectory")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.os.path.exists", return_value=True)
    def test_errors_on_process_execution_errors(
        self,
        m_exists,
        m_subp,
        m_temporary_directory,
        exit_code,
        stderr,
        error_msg,
    ):
        """Raise the appropriate user facing error from apt-helper failure."""
        m_temporary_directory.return_value.__enter__.return_value = (
            "/does/not/exist"
        )
        # Failure apt-helper response
        m_subp.side_effect = util.ProcessExecutionError(
            cmd="apt-helper ",
            exit_code=exit_code,
            stdout="Err:1...",
            stderr=stderr,
        )

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            assert_valid_apt_credentials(
                repo_url="http://fakerepo", username="user", password="pwd"
            )
        assert error_msg == str(excinfo.value)
        exists_calls = [mock.call("/usr/lib/apt/apt-helper")]
        assert exists_calls == m_exists.call_args_list
        expected_path = os.path.join(
            m_temporary_directory.return_value.__enter__.return_value,
            "apt-helper-output",
        )
        apt_helper_call = mock.call(
            [
                "/usr/lib/apt/apt-helper",
                "download-file",
                "http://user:pwd@fakerepo/ubuntu/pool/",
                expected_path,
            ],
            timeout=60,
        )
        assert [apt_helper_call] == m_subp.call_args_list

    @mock.patch("uaclient.apt.tempfile.TemporaryDirectory")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.os.path.exists", return_value=True)
    def test_errors_on_apt_helper_process_timeout(
        self, m_exists, m_subp, m_temporary_directory
    ):
        """Raise the appropriate user facing error from apt-helper timeout."""
        m_temporary_directory.return_value.__enter__.return_value = (
            "/does/not/exist"
        )
        # Failure apt-helper response
        m_subp.side_effect = subprocess.TimeoutExpired(
            "something timed out", timeout=1000000
        )
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            assert_valid_apt_credentials(
                repo_url="http://fakerepo", username="user", password="pwd"
            )
        error_msg = (
            "Cannot validate credentials for APT repo. Timeout"
            " after {} seconds trying to reach fakerepo.".format(
                apt.APT_HELPER_TIMEOUT
            )
        )
        assert error_msg == excinfo.value.msg
        exists_calls = [mock.call("/usr/lib/apt/apt-helper")]
        assert exists_calls == m_exists.call_args_list
        expected_path = os.path.join(
            m_temporary_directory.return_value.__enter__.return_value,
            "apt-helper-output",
        )
        apt_helper_call = mock.call(
            [
                "/usr/lib/apt/apt-helper",
                "download-file",
                "http://user:pwd@fakerepo/ubuntu/pool/",
                expected_path,
            ],
            timeout=apt.APT_HELPER_TIMEOUT,
        )
        assert [apt_helper_call] == m_subp.call_args_list


class TestAddAuthAptRepo:
    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_add_auth_apt_repo_writes_sources_file(
        self,
        m_platform,
        m_valid_creds,
        m_get_apt_auth_file,
        m_subp,
        m_gpg_export,
        tmpdir,
    ):
        """Write a properly configured sources file to repo_filename."""
        repo_file = tmpdir.join("repo.conf").strpath
        auth_file = tmpdir.join("auth.conf").strpath
        m_get_apt_auth_file.return_value = auth_file
        m_subp.return_value = "500 esm.canonical.com...", ""  # apt policy

        add_auth_apt_repo(
            repo_filename=repo_file,
            repo_url="http://fakerepo",
            credentials="mycreds",
            suites=("xenial",),
            keyring_file="keyring",
        )

        expected_content = (
            "deb http://fakerepo/ubuntu xenial main\n"
            "# deb-src http://fakerepo/ubuntu xenial main\n"
        )
        assert expected_content == util.load_file(repo_file)
        src_keyfile = os.path.join(KEYRINGS_DIR, "keyring")
        dest_keyfile = os.path.join(APT_KEYS_DIR, "keyring")
        gpg_export_calls = [mock.call(src_keyfile, dest_keyfile)]
        assert gpg_export_calls == m_gpg_export.call_args_list

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_add_auth_apt_repo_ignores_suites_not_matching_series(
        self,
        m_platform,
        m_valid_creds,
        m_get_apt_auth_file,
        m_subp,
        m_gpg_export,
        tmpdir,
    ):
        """Skip any apt suites that don't match the current series."""
        repo_file = tmpdir.join("repo.conf").strpath
        auth_file = tmpdir.join("auth.conf").strpath
        m_get_apt_auth_file.return_value = auth_file
        # apt policy with xenial-updates enabled
        stdout = dedent(
            """\
            500 http://archive.ubuntu.com/ubuntu/ xenial-updates/main amd64 \
                        Packages
                release v=16.04,o=Ubuntu,a=xenial-updates,n=xenial,l=Ubuntu\
                        ,c=main"""
        )
        m_subp.return_value = stdout, ""

        add_auth_apt_repo(
            repo_filename=repo_file,
            repo_url="http://fakerepo",
            credentials="mycreds",
            suites=("xenial-one", "xenial-updates", "trusty-gone"),
            keyring_file="keyring",
        )

        expected_content = dedent(
            """\
            deb http://fakerepo/ubuntu xenial-one main
            # deb-src http://fakerepo/ubuntu xenial-one main
            deb http://fakerepo/ubuntu xenial-updates main
            # deb-src http://fakerepo/ubuntu xenial-updates main
        """
        )
        assert expected_content == util.load_file(repo_file)

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_add_auth_apt_repo_comments_updates_suites_on_non_update_machine(
        self,
        m_platform,
        m_valid_creds,
        m_get_apt_auth_file,
        m_subp,
        m_gpg_export,
        tmpdir,
    ):
        """Skip any apt suites that don't match the current series."""
        repo_file = tmpdir.join("repo.conf").strpath
        auth_file = tmpdir.join("auth.conf").strpath
        m_get_apt_auth_file.return_value = auth_file
        # apt policy without xenial-updates enabled
        origin = "test-origin"
        m_subp.return_value = (
            POST_INSTALL_APT_CACHE_NO_UPDATES.format("xenial", origin),
            "",
        )

        add_auth_apt_repo(
            repo_filename=repo_file,
            repo_url="http://fakerepo",
            credentials="mycreds",
            suites=("xenial-one", "xenial-updates", "trusty-gone"),
            keyring_file="keyring",
        )

        expected_content = dedent(
            """\
            deb http://fakerepo/ubuntu xenial-one main
            # deb-src http://fakerepo/ubuntu xenial-one main
            # deb http://fakerepo/ubuntu xenial-updates main
            # deb-src http://fakerepo/ubuntu xenial-updates main
        """
        )
        assert expected_content == util.load_file(repo_file)

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_add_auth_apt_repo_writes_username_password_to_auth_file(
        self,
        m_platform,
        m_valid_creds,
        m_get_apt_auth_file,
        m_subp,
        m_gpg_export,
        tmpdir,
    ):
        """Write apt authentication file when credentials are user:pwd."""
        repo_file = tmpdir.join("repo.conf").strpath
        auth_file = tmpdir.join("auth.conf").strpath
        m_get_apt_auth_file.return_value = auth_file
        m_subp.return_value = "500 esm.canonical.com...", ""  # apt policy

        add_auth_apt_repo(
            repo_filename=repo_file,
            repo_url="http://fakerepo",
            credentials="user:password",
            suites=("xenial",),
            keyring_file="keyring",
        )

        expected_content = (
            "machine fakerepo/ login user password password"
            "{}\n".format(APT_AUTH_COMMENT)
        )
        assert expected_content == util.load_file(auth_file)

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_add_auth_apt_repo_writes_bearer_resource_token_to_auth_file(
        self,
        m_platform,
        m_valid_creds,
        m_get_apt_auth_file,
        m_subp,
        m_gpg_export,
        tmpdir,
    ):
        """Write apt authentication file when credentials are bearer token."""
        repo_file = tmpdir.join("repo.conf").strpath
        auth_file = tmpdir.join("auth.conf").strpath
        m_get_apt_auth_file.return_value = auth_file
        m_subp.return_value = "500 esm.canonical.com...", ""  # apt policy

        add_auth_apt_repo(
            repo_filename=repo_file,
            repo_url="http://fakerepo/",
            credentials="SOMELONGTOKEN",
            suites=("xenia",),
            keyring_file="keyring",
        )

        expected_content = (
            "machine fakerepo/ login bearer password"
            " SOMELONGTOKEN{}\n".format(APT_AUTH_COMMENT)
        )
        assert expected_content == util.load_file(auth_file)


class TestAddAptAuthConfEntry:
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_replaces_old_credentials_with_new(
        self, m_get_apt_auth_file, tmpdir
    ):
        """Replace old credentials for this repo_url on the same line."""
        auth_file = tmpdir.join("auth.conf").strpath
        util.write_file(
            auth_file,
            dedent(
                """\
            machine fakerepo1/ login me password password1
            machine fakerepo/ login old password oldpassword
            machine fakerepo2/ login other password otherpass
        """
            ),
        )

        m_get_apt_auth_file.return_value = auth_file

        add_apt_auth_conf_entry(
            login="newlogin", password="newpass", repo_url="http://fakerepo/"
        )

        content_template = dedent(
            """\
            machine fakerepo1/ login me password password1
            machine fakerepo/ login newlogin password newpass{}
            machine fakerepo2/ login other password otherpass
        """
        )
        expected_content = content_template.format(APT_AUTH_COMMENT)
        assert expected_content == util.load_file(auth_file)

    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_insert_repo_subroutes_before_existing_repo_basepath(
        self, m_get_apt_auth_file, tmpdir
    ):
        """Insert new repo_url before first matching url base path."""
        auth_file = tmpdir.join("auth.conf").strpath
        util.write_file(
            auth_file,
            dedent(
                """\
            machine fakerepo1/ login me password password1
            machine fakerepo/ login old password oldpassword
            machine fakerepo2/ login other password otherpass
        """
            ),
        )

        m_get_apt_auth_file.return_value = auth_file

        add_apt_auth_conf_entry(
            login="new",
            password="newpass",
            repo_url="http://fakerepo/subroute",
        )

        content_template = dedent(
            """\
            machine fakerepo1/ login me password password1
            machine fakerepo/subroute/ login new password newpass{}
            machine fakerepo/ login old password oldpassword
            machine fakerepo2/ login other password otherpass
        """
        )
        expected_content = content_template.format(APT_AUTH_COMMENT)
        assert expected_content == util.load_file(auth_file)


class TestCleanAptFiles:
    @pytest.fixture(params=[RepoEntitlement, UAEntitlement])
    def mock_apt_entitlement(self, request, tmpdir):
        # Set up our tmpdir with some fake list files
        entitlement_name = "test_ent"
        repo_tmpl = tmpdir.join("source-{name}").strpath
        pref_tmpl = tmpdir.join("pref-{name}").strpath

        class DummyRepo(request.param):
            name = entitlement_name
            repo_list_file_tmpl = repo_tmpl
            repo_pref_file_tmpl = pref_tmpl
            is_repo = request.param == RepoEntitlement

        for series in ["acidic", "base"]:
            source_name = repo_tmpl.format(name=entitlement_name)
            pref_name = pref_tmpl.format(name=entitlement_name)

            with open(source_name, "w") as f:
                f.write("")

            with open(pref_name, "w") as f:
                f.write("")

        return DummyRepo

    @mock.patch("uaclient.apt.os.unlink")
    def test_no_removals_for_no_repo_entitlements(self, m_os_unlink):
        m_entitlements = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASSES = [RepoTestEntitlement]

        clean_apt_files(_entitlements=m_entitlements)

        assert 0 == m_os_unlink.call_count

    def test_files_for_all_series_removed(self, mock_apt_entitlement, tmpdir):
        m_entitlements = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASSES = [mock_apt_entitlement]

        clean_apt_files(_entitlements=m_entitlements)

        if mock_apt_entitlement.is_repo:
            assert [] == tmpdir.listdir()
        else:
            assert sorted(
                [tmpdir.join("source-test_ent"), tmpdir.join("pref-test_ent")]
            ) == sorted(tmpdir.listdir())

    def test_other_files_not_removed(self, mock_apt_entitlement, tmpdir):
        other_filename = "other_file-acidic"
        tmpdir.join(other_filename).ensure()

        m_entitlements = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASSES = [mock_apt_entitlement]

        clean_apt_files(_entitlements=m_entitlements)

        if mock_apt_entitlement.is_repo:
            assert [tmpdir.join(other_filename)] == tmpdir.listdir()
        else:
            assert sorted(
                [
                    tmpdir.join("source-test_ent"),
                    tmpdir.join("pref-test_ent"),
                    tmpdir.join(other_filename),
                ]
            ) == sorted(tmpdir.listdir())


@pytest.fixture(params=(mock.sentinel.default, None, "some_string"))
def remove_auth_apt_repo_kwargs(request):
    """
    Parameterized fixture to generate all permutations of kwargs we need

    Note that this tests three states for keyring_file: using the default,
    explicitly passing None and explicitly passing a string.
    """
    keyring_file = request.param
    kwargs = {}
    if keyring_file != mock.sentinel.default:
        kwargs["keyring_file"] = keyring_file
    return kwargs


class TestRemoveAuthAptRepo:
    @mock.patch("uaclient.apt.util.subp")
    @mock.patch("uaclient.apt.remove_repo_from_apt_auth_file")
    @mock.patch("uaclient.apt.util.del_file")
    def test_repo_file_deleted(
        self, m_del_file, _mock, __mock, remove_auth_apt_repo_kwargs
    ):
        """Ensure that repo_filename is deleted, regardless of other params."""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs
        )

        assert mock.call(repo_filename) in m_del_file.call_args_list

    @mock.patch("uaclient.apt.util.subp")
    @mock.patch("uaclient.apt.util.del_file")
    @mock.patch("uaclient.apt.remove_repo_from_apt_auth_file")
    def test_remove_from_auth_file_called(
        self, m_remove_repo, _mock, __mock, remove_auth_apt_repo_kwargs
    ):
        """Ensure that remove_repo_from_apt_auth_file is called."""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs
        )

        assert mock.call(repo_url) in m_remove_repo.call_args_list

    @mock.patch("uaclient.apt.util.subp")
    @mock.patch("uaclient.apt.remove_repo_from_apt_auth_file")
    @mock.patch("uaclient.apt.util.del_file")
    def test_keyring_file_deleted_if_given(
        self, m_del_file, _mock, __mock, remove_auth_apt_repo_kwargs
    ):
        """We should always delete the keyring file if it is given"""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs
        )

        keyring_file = remove_auth_apt_repo_kwargs.get("keyring_file")
        if keyring_file:
            assert (
                mock.call(os.path.join(APT_KEYS_DIR, keyring_file))
                in m_del_file.call_args_list
            )
        else:
            assert mock.call(keyring_file) not in m_del_file.call_args_list


class TestRemoveRepoFromAptAuthFile:
    @mock.patch("uaclient.apt.os.unlink")
    @mock.patch("uaclient.apt.util.write_file")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_auth_file_doesnt_exist_means_we_dont_remove_or_write_it(
        self, m_get_apt_auth_file, m_write_file, m_unlink, tmpdir
    ):
        """If the auth file doesn't exist, we shouldn't do anything to it"""
        m_get_apt_auth_file.return_value = tmpdir.join("nonexistent").strpath

        remove_repo_from_apt_auth_file("http://url")

        assert 0 == m_write_file.call_count
        assert 0 == m_unlink.call_count

    @pytest.mark.parametrize("trailing_slash", (True, False))
    @pytest.mark.parametrize(
        "repo_url,auth_file_content",
        (
            ("http://url1", b""),
            ("http://url2", b"machine url2/ login trailing content"),
            ("http://url3", b"machine url3/ login"),
            ("http://url4", b"leading content machine url4/ login"),
            (
                "http://url4",
                b"leading content machine url4/ login trailing content",
            ),
        ),
    )
    @mock.patch("uaclient.apt.os.unlink")
    @mock.patch("uaclient.apt.util.write_file")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_file_removal(
        self,
        m_get_apt_auth_file,
        m_write_file,
        m_unlink,
        tmpdir,
        trailing_slash,
        repo_url,
        auth_file_content,
    ):
        """Check that auth file is rm'd if empty or contains just our line"""
        auth_file = tmpdir.join("auth_file")
        auth_file.write(auth_file_content, "wb")
        m_get_apt_auth_file.return_value = auth_file.strpath

        remove_repo_from_apt_auth_file(
            repo_url + ("" if not trailing_slash else "/")
        )

        assert 0 == m_write_file.call_count
        assert [mock.call(auth_file.strpath)] == m_unlink.call_args_list

    @pytest.mark.parametrize("trailing_slash", (True, False))
    @pytest.mark.parametrize(
        "repo_url,before_content,after_content",
        (
            (
                "http://url1",
                b"should not be changed",
                b"should not be changed",
            ),
            (
                "http://url1",
                b"line before\nmachine url1/ login",
                b"line before",
            ),
            ("http://url1", b"machine url1/ login\nline after", b"line after"),
            (
                "http://url1",
                b"line before\nmachine url1/ login\nline after",
                b"line before\nline after",
            ),
            (
                "http://url1",
                b"unicode \xe2\x98\x83\nmachine url1/ login",
                b"unicode \xe2\x98\x83",
            ),
        ),
    )
    @mock.patch("uaclient.apt.os.unlink")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_file_rewrite(
        self,
        m_get_apt_auth_file,
        m_unlink,
        tmpdir,
        repo_url,
        before_content,
        after_content,
        trailing_slash,
    ):
        """Check that auth file is rewritten to only exclude our line"""
        auth_file = tmpdir.join("auth_file")
        auth_file.write(before_content, "wb")
        m_get_apt_auth_file.return_value = auth_file.strpath

        remove_repo_from_apt_auth_file(
            repo_url + ("" if not trailing_slash else "/")
        )

        assert 0 == m_unlink.call_count
        assert 0o600 == stat.S_IMODE(os.lstat(auth_file.strpath).st_mode)
        assert after_content == auth_file.read("rb")


class TestRestoreCommentAptListFile:
    @pytest.mark.parametrize(
        "before,expected",
        (
            ("", ""),
            ("some other content", "some other content"),
            ("deb uncommented", "deb uncommented"),
            ("# deb-src comment", "# deb-src comment"),
            ("# deb comment", "deb comment"),
            (
                "deb uncommented\n# deb commented",
                "deb uncommented\ndeb commented",
            ),
            (
                "# deb commented\n# deb-src commented",
                "deb commented\n# deb-src commented",
            ),
            (
                "deb uncommented\n# deb-src commented\n"
                "# deb commented\n# deb-src commented",
                "deb uncommented\n# deb-src commented\n"
                "deb commented\n# deb-src commented",
            ),
        ),
    )
    def test_permutations(self, tmpdir, before, expected):
        list_file = tmpdir.join("list_file")
        list_file.write(before)

        apt.restore_commented_apt_list_file(list_file.strpath)

        assert expected == list_file.read()


class TestGetInstalledPackages:
    @mock.patch("uaclient.apt.util.subp", return_value=("", ""))
    def test_correct_command_called(self, m_subp):
        get_installed_packages()

        expected_call = mock.call(
            ["dpkg-query", "-W", "--showformat=${Package}\\n"]
        )
        assert [expected_call] == m_subp.call_args_list

    @mock.patch("uaclient.apt.util.subp", return_value=("", ""))
    def test_empty_output_means_empty_list(self, m_subp):
        assert [] == get_installed_packages()

    @mock.patch("uaclient.apt.util.subp", return_value=("a\nb\n", ""))
    def test_lines_are_split(self, m_subp):
        assert ["a", "b"] == get_installed_packages()

    @mock.patch("uaclient.apt.util.subp", return_value=("a\nb", ""))
    def test_assert_missing_eof_newline_works(self, m_subp):
        assert ["a", "b"] == get_installed_packages()


class TestRunAptCommand:
    @pytest.mark.parametrize(
        "error_list, output_list",
        (
            (
                [
                    "E: The repository 't1 404' does not have a Release.",
                    "W: Failed to fetch t1/dists/ 404 Not found.",
                    "E: The repository 't2 404' does not have a Release.\n",
                ],
                (
                    "APT update failed.",
                    (
                        "APT update failed to read APT config "
                        "for the following URLs:"
                    ),
                    "- t1",
                    "- t2",
                ),
            ),
            (
                ["E: The repository 't1 404' does not have a Release file."],
                (
                    "APT update failed.",
                    (
                        "APT update failed to read APT config "
                        "for the following URL:"
                    ),
                    "- t1",
                ),
            ),
            (
                [
                    "W: Failed to fetch t1/dists Not Found [IP: 127.0.0.1]\n",
                    "E: Some index files failed to download.\n",
                ],
                (
                    "APT update failed.",
                    (
                        "APT update failed to read APT config "
                        "for the following URL:"
                    ),
                    "- t1",
                ),
            ),
        ),
    )
    @mock.patch("uaclient.apt.util.subp")
    def test_run_apt_command_with_invalid_repositories(
        self, m_subp, error_list, output_list
    ):
        error_msg = "\n".join(error_list)

        m_subp.side_effect = util.ProcessExecutionError(
            cmd="apt update", stderr=error_msg
        )

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            run_apt_command(
                cmd=["apt", "update"],
                error_msg=status.MESSAGE_APT_UPDATE_FAILED,
            )

        expected_message = "\n".join(output_list) + "."
        assert expected_message == excinfo.value.msg
