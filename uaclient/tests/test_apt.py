"""Tests related to uaclient.apt module."""

import glob
import os
import stat
import subprocess
from textwrap import dedent

import mock
import pytest

from uaclient import exceptions, messages, system
from uaclient.apt import (
    APT_AUTH_COMMENT,
    APT_CONFIG_GLOBAL_PROXY_HTTP,
    APT_CONFIG_GLOBAL_PROXY_HTTPS,
    APT_HELPER_TIMEOUT,
    APT_KEYS_DIR,
    APT_PROXY_CONF_FILE,
    APT_RETRIES,
    KEYRINGS_DIR,
    PreserveAptCfg,
    add_apt_auth_conf_entry,
    add_auth_apt_repo,
    add_ppa_pinning,
    assert_valid_apt_credentials,
    clean_apt_files,
    compare_versions,
    find_apt_list_files,
    get_apt_cache_policy,
    get_apt_cache_time,
    get_apt_config_values,
    get_installed_packages_names,
    is_installed,
    remove_apt_list_files,
    remove_auth_apt_repo,
    remove_repo_from_apt_auth_file,
    run_apt_update_command,
    setup_apt_proxy,
    update_esm_caches,
)
from uaclient.entitlements.base import UAEntitlement
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.entitlements.repo import RepoEntitlement
from uaclient.entitlements.tests.test_repo import RepoTestEntitlement

POST_INSTALL_APT_CACHE_NO_UPDATES = """
-32768 https://esm.ubuntu.com/ubuntu/ {0}-updates/main amd64 Packages
     release v=14.04,o={1},a={0}-updates,n={0},l=UbuntuESM,c=main
     origin esm.ubuntu.com
"""

APT_LIST_RETURN_STRING = """\
"Listing... Done
a/release, now 1.2+3 arch123 [i,a]
b/release-updates, now 1.2+3 arch123 [i,a]
"""


class TestAddPPAPinning:
    @mock.patch("uaclient.system.get_release_info")
    def test_write_apt_pin_file_to_apt_preferences(
        self, m_get_release_info, tmpdir
    ):
        """Write proper apt pin file to specified apt_preference_file."""
        m_get_release_info.return_value = mock.MagicMock(series="xenial")
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
            Pin: release o=MYORIG
            Pin-Priority: 1003\n"""
        )
        assert expected_pref == system.load_file(pref_file)


class TestFindAptListFilesFromRepoSeries:
    @mock.patch("uaclient.system.subp")
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
            system.write_file(path, "")

        assert paths[1:] == find_apt_list_files(repo_url, "xenial")


class TestRemoveAptListFiles:
    @mock.patch("uaclient.system.subp")
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
            system.write_file(path, "")

        assert None is remove_apt_list_files(repo_url, "xenial")
        assert [nomatch_file] == glob.glob("{}/*".format(tmpdir.strpath))


class TestValidAptCredentials:
    @mock.patch("uaclient.system.subp")
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
    @mock.patch("uaclient.system.subp")
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
            retry_sleeps=APT_RETRIES,
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
                "E: Failed to fetch ... HttpError401 on xenial",
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
    @mock.patch("uaclient.system.subp")
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
        m_subp.side_effect = exceptions.ProcessExecutionError(
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
            retry_sleeps=APT_RETRIES,
        )
        assert [apt_helper_call] == m_subp.call_args_list

    @mock.patch("uaclient.apt.tempfile.TemporaryDirectory")
    @mock.patch("uaclient.system.subp")
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
                APT_HELPER_TIMEOUT
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
            timeout=APT_HELPER_TIMEOUT,
            retry_sleeps=APT_RETRIES,
        )
        assert [apt_helper_call] == m_subp.call_args_list


class TestAddAuthAptRepo:
    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    def test_add_auth_apt_repo_writes_sources_file(
        self,
        m_get_release_info,
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
        assert expected_content == system.load_file(repo_file)
        src_keyfile = os.path.join(KEYRINGS_DIR, "keyring")
        dest_keyfile = os.path.join(APT_KEYS_DIR, "keyring")
        gpg_export_calls = [mock.call(src_keyfile, dest_keyfile)]
        assert gpg_export_calls == m_gpg_export.call_args_list

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    def test_add_auth_apt_repo_ignores_suites_not_matching_series(
        self,
        m_get_release_info,
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
        assert expected_content == system.load_file(repo_file)

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    def test_add_auth_apt_repo_comments_updates_suites_on_non_update_machine(
        self,
        m_get_release_info,
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
        assert expected_content == system.load_file(repo_file)

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    def test_add_auth_apt_repo_writes_username_password_to_auth_file(
        self,
        m_get_release_info,
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
        assert expected_content == system.load_file(auth_file)

    @mock.patch("uaclient.apt.gpg.export_gpg_key")
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    @mock.patch("uaclient.apt.assert_valid_apt_credentials")
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    def test_add_auth_apt_repo_writes_bearer_resource_token_to_auth_file(
        self,
        m_get_release_info,
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
        assert expected_content == system.load_file(auth_file)


class TestAddAptAuthConfEntry:
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_replaces_old_credentials_with_new(
        self, m_get_apt_auth_file, tmpdir
    ):
        """Replace old credentials for this repo_url on the same line."""
        auth_file = tmpdir.join("auth.conf").strpath
        system.write_file(
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
        assert expected_content == system.load_file(auth_file)

    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_insert_repo_subroutes_before_existing_repo_basepath(
        self, m_get_apt_auth_file, tmpdir
    ):
        """Insert new repo_url before first matching url base path."""
        auth_file = tmpdir.join("auth.conf").strpath
        system.write_file(
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
        assert expected_content == system.load_file(auth_file)


class TestCleanAptFiles:
    @pytest.fixture(params=[RepoEntitlement, UAEntitlement])
    def mock_apt_entitlement(self, request, tmpdir):
        # Set up our tmpdir with some fake list files
        entitlement_name = "test_ent"
        repo_tmpl = tmpdir.join("source-{name}").strpath
        pref_tmpl = tmpdir.join("pref-{name}").strpath

        class TestRepo(request.param):
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

        return TestRepo

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("uaclient.system.ensure_file_absent")
    def test_removals_for_repo_entitlements(
        self, m_ensure_file_absent, _m_path_exists
    ):
        m_entitlements = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASSES = [RepoTestEntitlement]

        clean_apt_files(_entitlements=m_entitlements)

        assert 2 == m_ensure_file_absent.call_count

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
    @mock.patch("uaclient.apt.system.subp")
    @mock.patch("uaclient.apt.remove_repo_from_apt_auth_file")
    @mock.patch("uaclient.apt.system.ensure_file_absent")
    def test_repo_file_deleted(
        self, m_ensure_file_absent, _mock, __mock, remove_auth_apt_repo_kwargs
    ):
        """Ensure that repo_filename is deleted, regardless of other params."""
        repo_filename, repo_url = mock.sentinel.filename, mock.sentinel.url

        remove_auth_apt_repo(
            repo_filename, repo_url, **remove_auth_apt_repo_kwargs
        )

        assert mock.call(repo_filename) in m_ensure_file_absent.call_args_list

    @mock.patch("uaclient.apt.system.subp")
    @mock.patch("uaclient.apt.system.ensure_file_absent")
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

    @mock.patch("uaclient.apt.system.subp")
    @mock.patch("uaclient.apt.remove_repo_from_apt_auth_file")
    @mock.patch("uaclient.apt.system.ensure_file_absent")
    def test_keyring_file_deleted_if_given(
        self, m_ensure_file_absent, _mock, __mock, remove_auth_apt_repo_kwargs
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
                in m_ensure_file_absent.call_args_list
            )
        else:
            assert (
                mock.call(keyring_file)
                not in m_ensure_file_absent.call_args_list
            )


class TestRemoveRepoFromAptAuthFile:
    @mock.patch("uaclient.system.ensure_file_absent")
    @mock.patch("uaclient.apt.system.write_file")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_auth_file_doesnt_exist_means_we_dont_remove_or_write_it(
        self, m_get_apt_auth_file, m_write_file, m_ensure_file_absent, tmpdir
    ):
        """If the auth file doesn't exist, we shouldn't do anything to it"""
        m_get_apt_auth_file.return_value = tmpdir.join("nonexistent").strpath

        remove_repo_from_apt_auth_file("http://url")

        assert 0 == m_write_file.call_count
        assert 0 == m_ensure_file_absent.call_count

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
    @mock.patch("uaclient.system.ensure_file_absent")
    @mock.patch("uaclient.apt.system.write_file")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_file_removal(
        self,
        m_get_apt_auth_file,
        m_write_file,
        m_ensure_file_absent,
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
        assert [
            mock.call(auth_file.strpath)
        ] == m_ensure_file_absent.call_args_list

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
    @mock.patch("uaclient.system.ensure_file_absent")
    @mock.patch("uaclient.apt.get_apt_auth_file_from_apt_config")
    def test_file_rewrite(
        self,
        m_get_apt_auth_file,
        m_ensure_file_absent,
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

        assert 0 == m_ensure_file_absent.call_count
        assert 0o600 == stat.S_IMODE(os.lstat(auth_file.strpath).st_mode)
        assert after_content == auth_file.read("rb")


class TestGetInstalledPackages:
    @mock.patch("uaclient.apt.system.subp", return_value=("", ""))
    def test_correct_command_called(self, m_subp):
        get_installed_packages_names()

        expected_call = mock.call(["apt", "list", "--installed"])
        assert [expected_call] == m_subp.call_args_list

    @mock.patch(
        "uaclient.apt.system.subp", return_value=("Listing... Done\n", "")
    )
    def test_empty_output_means_empty_list(self, m_subp):
        assert [] == get_installed_packages_names()

    @pytest.mark.parametrize(
        "apt_list_return",
        (APT_LIST_RETURN_STRING, APT_LIST_RETURN_STRING[:-1]),
    )
    @mock.patch("uaclient.apt.system.subp")
    def test_lines_are_split(self, m_subp, apt_list_return):
        m_subp.return_value = apt_list_return, ""
        assert ["a", "b"] == get_installed_packages_names()


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
    @mock.patch("uaclient.apt.system.subp")
    def test_run_apt_command_with_invalid_repositories(
        self, m_subp, error_list, output_list
    ):
        error_msg = "\n".join(error_list)

        m_subp.side_effect = exceptions.ProcessExecutionError(
            cmd="apt update", stderr=error_msg
        )

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            run_apt_update_command()

        expected_message = "\n".join(output_list) + "."
        assert expected_message == excinfo.value.msg

    @mock.patch("uaclient.apt.system.subp")
    def test_run_update_command_clean_apt_cache_policy_cache(self, m_subp):
        m_subp.side_effect = [
            ("policy1", ""),
            ("update", ""),
            ("policy2", ""),
        ]

        assert "policy1" == get_apt_cache_policy()
        # Confirming that caching is happening
        assert "policy1" == get_apt_cache_policy()

        run_apt_update_command()

        # Confirm cache was cleared
        assert "policy2" == get_apt_cache_policy()
        get_apt_cache_policy.cache_clear()

    @mock.patch("uaclient.apt.system.subp")
    def test_failed_run_update_command_clean_apt_cache_policy_cache(
        self, m_subp
    ):
        m_subp.side_effect = [
            ("policy1", ""),
            exceptions.UserFacingError("test"),
            ("policy2", ""),
        ]

        assert "policy1" == get_apt_cache_policy()
        # Confirming that caching is happening
        assert "policy1" == get_apt_cache_policy()

        with pytest.raises(exceptions.UserFacingError):
            run_apt_update_command()

        # Confirm cache was cleared
        assert "policy2" == get_apt_cache_policy()
        get_apt_cache_policy.cache_clear()


class TestAptProxyConfig:
    @pytest.mark.parametrize(
        "kwargs, expected_remove_calls, expected_write_calls, expected_out",
        [
            ({}, [mock.call(APT_PROXY_CONF_FILE)], [], ""),
            (
                {"http_proxy": "mock_http_proxy"},
                [],
                [
                    mock.call(
                        APT_PROXY_CONF_FILE,
                        messages.APT_PROXY_CONFIG_HEADER
                        + APT_CONFIG_GLOBAL_PROXY_HTTP.format(
                            proxy_url="mock_http_proxy"
                        ),
                    )
                ],
                messages.SETTING_SERVICE_PROXY_SCOPE.format(scope="global"),
            ),
            (
                {"https_proxy": "mock_https_proxy"},
                [],
                [
                    mock.call(
                        APT_PROXY_CONF_FILE,
                        messages.APT_PROXY_CONFIG_HEADER
                        + APT_CONFIG_GLOBAL_PROXY_HTTPS.format(
                            proxy_url="mock_https_proxy"
                        ),
                    )
                ],
                messages.SETTING_SERVICE_PROXY_SCOPE.format(scope="global"),
            ),
            (
                {
                    "http_proxy": "mock_http_proxy",
                    "https_proxy": "mock_https_proxy",
                },
                [],
                [
                    mock.call(
                        APT_PROXY_CONF_FILE,
                        messages.APT_PROXY_CONFIG_HEADER
                        + APT_CONFIG_GLOBAL_PROXY_HTTP.format(
                            proxy_url="mock_http_proxy"
                        )
                        + APT_CONFIG_GLOBAL_PROXY_HTTPS.format(
                            proxy_url="mock_https_proxy"
                        ),
                    )
                ],
                messages.SETTING_SERVICE_PROXY_SCOPE.format(scope="global"),
            ),
        ],
    )
    @mock.patch("uaclient.system.write_file")
    @mock.patch("uaclient.system.ensure_file_absent")
    def test_setup_apt_proxy_config(
        self,
        m_ensure_file_absent,
        m_util_write_file,
        kwargs,
        expected_remove_calls,
        expected_write_calls,
        expected_out,
        capsys,
        event,
    ):
        setup_apt_proxy(**kwargs)
        assert expected_remove_calls == m_ensure_file_absent.call_args_list
        assert expected_write_calls == m_util_write_file.call_args_list
        out, err = capsys.readouterr()
        assert expected_out == out.strip()
        assert "" == err


class TestAptIsInstalled:
    @pytest.mark.parametrize(
        "expected,installed_pkgs",
        (
            (True, ("foo", "test", "bar")),
            (False, ("foo", "bar")),
        ),
    )
    @mock.patch("uaclient.apt.get_installed_packages_names")
    def test_is_installed_pkgs(
        self, m_get_installed_pkgs, expected, installed_pkgs
    ):
        m_get_installed_pkgs.return_value = installed_pkgs
        assert expected == is_installed("test")


class TestCompareVersion:
    @pytest.mark.parametrize(
        "ver1,ver2,relation,expected_result",
        (
            ("1.0", "2.0", "le", True),
            ("1.0", "2.0", "gt", False),
            ("2.0", "2.0", "lt", False),
            ("2.0", "2.0", "eq", True),
            ("2.0", "2.0", "gt", False),
            ("2.1~18.04.1", "2.1", "le", True),
            ("2.1", "2.1~18.04.1", "le", False),
            ("2.10", "2.9", "ge", True),
            ("2.10", "2.9", "lt", False),
        ),
    )
    def test_compare_versions(
        self, ver1, ver2, relation, expected_result, _subp
    ):
        """compare_versions returns True when the comparison is accurate."""
        with mock.patch("uaclient.system._subp", side_effect=_subp):
            assert expected_result is compare_versions(ver1, ver2, relation)


class TestAptCache:
    @pytest.mark.parametrize(
        "file_exists,expected", ((True, 1.23), (False, None))
    )
    @mock.patch("os.stat")
    @mock.patch("os.path.exists")
    def test_get_apt_cache_time(self, m_exists, m_stat, file_exists, expected):
        m_stat.return_value.st_mtime = 1.23
        m_exists.return_value = file_exists
        assert expected == get_apt_cache_time()

    @pytest.mark.parametrize(
        "is_lts,cache_call_list",
        ((True, [mock.call()]), (False, [])),
    )
    @pytest.mark.parametrize(
        "apps_status", (ApplicationStatus.ENABLED, ApplicationStatus.DISABLED)
    )
    @pytest.mark.parametrize(
        "infra_status", (ApplicationStatus.ENABLED, ApplicationStatus.DISABLED)
    )
    @pytest.mark.parametrize("is_esm", (True, False))
    @pytest.mark.parametrize("can_enable_infra", ("yes", "no"))
    @pytest.mark.parametrize("can_enable_apps", ("yes", "no"))
    @mock.patch("uaclient.entitlements.esm.ESMAppsEntitlement")
    @mock.patch("uaclient.entitlements.esm.ESMInfraEntitlement")
    @mock.patch("uaclient.apt.system.is_current_series_lts")
    @mock.patch("uaclient.apt.system.is_current_series_active_esm")
    @mock.patch("uaclient.apt.get_esm_cache")
    @mock.patch("uaclient.actions.status")
    @mock.patch("apt_pkg.config")
    @mock.patch("apt_pkg.init_config")
    def test_update_esm_caches_based_on_lts(
        self,
        _m_apt_pkg_init_config,
        _m_apt_pkg_config,
        m_status,
        m_esm_cache,
        m_is_esm,
        m_is_lts,
        m_infra_entitlement,
        m_apps_entitlement,
        is_lts,
        cache_call_list,
        apps_status,
        infra_status,
        is_esm,
        can_enable_infra,
        can_enable_apps,
        FakeConfig,
    ):
        m_status.return_value = (
            {
                "services": [
                    {"name": "esm-apps", "available": can_enable_apps},
                    {"name": "esm-infra", "available": can_enable_infra},
                ]
            },
            0,
        )

        m_is_esm.return_value = is_esm
        m_is_lts.return_value = is_lts

        m_infra = mock.MagicMock()
        m_apps = mock.MagicMock()

        m_infra.application_status.return_value = (
            infra_status,
            "",
        )

        m_apps.application_status.return_value = (
            apps_status,
            "",
        )

        m_infra_entitlement.return_value = m_infra
        m_apps_entitlement.return_value = m_apps

        infra_setup_repo_count = 0
        apps_setup_repo_count = 0
        infra_disable_repo_count = 0
        apps_disable_repo_count = 0
        status_count = 0
        status_cache_args_list = []

        if is_lts:
            status_count = 1
            status_cache_args_list = [mock.call("status-cache")]
            if (
                apps_status == ApplicationStatus.DISABLED
                and can_enable_apps == "yes"
            ):
                apps_setup_repo_count = 1
            else:
                apps_disable_repo_count = 1

            if (
                infra_status == ApplicationStatus.DISABLED
                and is_esm
                and can_enable_infra == "yes"
            ):
                infra_setup_repo_count = 1
            elif is_esm:
                infra_disable_repo_count = 1

        cfg = FakeConfig()
        with mock.patch.object(cfg, "read_cache", return_value=None):
            update_esm_caches(cfg)
            assert cfg.read_cache.call_args_list == status_cache_args_list

        assert m_esm_cache.call_args_list == cache_call_list
        assert (
            m_infra.setup_local_esm_repo.call_count == infra_setup_repo_count
        )
        assert m_apps.setup_local_esm_repo.call_count == apps_setup_repo_count
        assert (
            m_infra.disable_local_esm_repo.call_count
            == infra_disable_repo_count
        )
        assert (
            m_apps.disable_local_esm_repo.call_count == apps_disable_repo_count
        )
        assert m_status.call_count == status_count


class TestGetAptConfigValues:
    @mock.patch("uaclient.apt._get_apt_config")
    def test_apt_config_values(
        self,
        m_get_apt_config,
    ):
        m_dict = mock.MagicMock()
        m_get_apt_config.return_value = m_dict

        m_dict.get.side_effect = ["", "foo", "bar", ""]
        m_dict.value_list.side_effect = [
            "",
            ["test1", "test2"],
        ]

        expected_return = {
            "val1": None,
            "val2": "foo",
            "val3": "bar",
            "val4": ["test1", "test2"],
        }

        assert expected_return == get_apt_config_values(
            ["val1", "val2", "val3", "val4"]
        )


class TestPreserveAptCfg:
    def test_apt_config_is_preserved(
        self,
        apt_pkg,
    ):
        class AptDict(dict):
            def set(self, key, value):
                super().__setitem__(key, value)

        apt_cfg = AptDict()
        apt_cfg["test"] = 1
        apt_cfg["test1"] = [1, 2, 3]
        apt_cfg["test2"] = {"foo": "bar"}

        type(apt_pkg).config = mock.PropertyMock(return_value=apt_cfg)

        def apt_func():
            apt_cfg["test"] = 3
            apt_cfg["test1"] = [3, 2, 1]
            apt_cfg["test2"] = {"foo": "test"}
            return apt_cfg

        with PreserveAptCfg(apt_func):
            pass

        assert 1 == apt_cfg["test"]
        assert [1, 2, 3] == apt_cfg["test1"]
        assert {"foo": "bar"} == apt_cfg["test2"]
