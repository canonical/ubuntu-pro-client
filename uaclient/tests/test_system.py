import logging
import posix
import subprocess
import uuid

import mock
import pytest

from uaclient import exceptions, system

PRIVACY_POLICY_URL = (
    "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
)

OS_RELEASE_DISCO = """\
NAME="Ubuntu"
VERSION="19.04 (Disco Dingo)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu Disco Dingo (development branch)"
VERSION_ID="19.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="{}"
VERSION_CODENAME=disco
UBUNTU_CODENAME=disco
""".format(
    PRIVACY_POLICY_URL
)

OS_RELEASE_BIONIC = """\
NAME="Ubuntu"
VERSION="18.04.1 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04.1 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="{}"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic
""".format(
    PRIVACY_POLICY_URL
)

OS_RELEASE_XENIAL = """\
NAME="Ubuntu"
VERSION="16.04.5 LTS (Xenial Xerus)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 16.04.5 LTS"
VERSION_ID="16.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
VERSION_CODENAME=xenial
UBUNTU_CODENAME=xenial
"""


class TestIsLTS:
    @pytest.mark.parametrize(
        "series, supported_esm, expected",
        (
            ("xenial", "xenial\nbionic\nfocal", True),
            ("groovy", "xenial\nbionic\nfocal", False),
        ),
    )
    @mock.patch("uaclient.system.subp")
    def test_is_lts_if_distro_info_supported_esm(
        self, subp, series, supported_esm, expected
    ):
        subp.return_value = supported_esm, ""
        # Use __wrapped__ to avoid hitting the lru_cached value across tests
        assert expected is system.is_lts.__wrapped__(series)
        assert [
            mock.call(["/usr/bin/ubuntu-distro-info", "--supported-esm"])
        ] == subp.call_args_list


class TestIsActiveESM:
    @pytest.mark.parametrize(
        "series, is_lts, days_until_esm,expected",
        (
            ("xenial", True, 1, False),
            ("xenial", True, 0, True),
            ("bionic", True, 1, False),
            ("bionic", True, 0, True),
            ("focal", True, 1, False),
            ("focal", True, 0, True),
            ("groovy", False, 0, False),
        ),
    )
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.system.is_lts")
    def test_true_when_supported_esm_release_and_active(
        self, util_is_lts, subp, series, is_lts, days_until_esm, expected
    ):
        """Return True when series is --suported-esm and days until esm < 1."""
        util_is_lts.return_value = is_lts
        subp.return_value = str(days_until_esm), ""

        # Use __wrapped__ to avoid hitting the lru_cached value across tests
        calls = []
        if is_lts:
            calls.append(
                mock.call(
                    [
                        "/usr/bin/ubuntu-distro-info",
                        "--series",
                        series,
                        "-yeol",
                    ]
                )
            )
        assert expected is system.is_active_esm.__wrapped__(series)
        assert calls == subp.call_args_list


class TestIsContainer:
    @mock.patch("uaclient.system.subp")
    def test_true_systemd_detect_virt_success(self, m_subp):
        """Return True when systemd-detect virt exits success."""
        system.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            "",
            "",
        ]
        assert True is system.is_container()
        # Second call for lru_cache test
        system.is_container()
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list

    @mock.patch("uaclient.system.subp")
    def test_true_on_run_container_type(self, m_subp, tmpdir):
        """Return True when /run/container_type exists."""
        system.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            OSError("No systemd-detect-virt utility"),
        ]
        tmpdir.join("container_type").write("")

        assert True is system.is_container(run_path=tmpdir.strpath)
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list

    @mock.patch("uaclient.system.subp")
    def test_true_on_run_systemd_container(self, m_subp, tmpdir):
        """Return True when /run/systemd/container exists."""
        system.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            OSError("No systemd-detect-virt utility"),
        ]
        tmpdir.join("systemd/container").write("", ensure=True)

        assert True is system.is_container(run_path=tmpdir.strpath)
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list

    @mock.patch("uaclient.system.subp")
    def test_false_on_non_sytemd_detect_virt_and_no_runfiles(
        self, m_subp, tmpdir
    ):
        """Return False when sytemd-detect-virt erros and no /run/* files."""
        system.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            OSError("No systemd-detect-virt utility"),
        ]
        tmpdir.join("systemd/container").write("", ensure=True)

        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.return_value = False
            assert False is system.is_container(run_path=tmpdir.strpath)
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list
        exists_calls = [
            mock.call(tmpdir.join("container_type").strpath),
            mock.call(tmpdir.join("systemd/container").strpath),
        ]
        assert exists_calls == m_exists.call_args_list

    @mock.patch("uaclient.system.subp")
    def test_false_on_chroot_system(self, m_subp):
        system.is_container.cache_clear()
        m_subp.return_value = ("", "")
        assert False is system.is_container()

        calls = [mock.call(["ischroot"])]
        assert calls == m_subp.call_args_list


class TestParseOSRelease:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_parse_os_release(self, caplog_text, tmpdir):
        """parse_os_release returns a dict of values from /etc/os-release."""
        release_file = tmpdir.join("os-release")
        release_file.write(OS_RELEASE_XENIAL)
        expected = {
            "BUG_REPORT_URL": "http://bugs.launchpad.net/ubuntu/",
            "HOME_URL": "http://www.ubuntu.com/",
            "ID": "ubuntu",
            "ID_LIKE": "debian",
            "NAME": "Ubuntu",
            "PRETTY_NAME": "Ubuntu 16.04.5 LTS",
            "SUPPORT_URL": "http://help.ubuntu.com/",
            "UBUNTU_CODENAME": "xenial",
            "VERSION": "16.04.5 LTS (Xenial Xerus)",
            "VERSION_CODENAME": "xenial",
            "VERSION_ID": "16.04",
        }
        assert expected == system.parse_os_release(release_file.strpath)
        # Add a 2nd call for lru_cache test
        system.parse_os_release(release_file.strpath)

        os_release_reads = len(
            [
                line
                for line in caplog_text().splitlines()
                if "os-release" in line
            ]
        )
        assert (
            1 == os_release_reads
        ), "lru_cache expected 1 read but found {}".format(os_release_reads)


class TestGetPlatformInfo:
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.system.parse_os_release")
    def test_get_platform_info_error_no_version(self, m_parse, m_subp):
        """get_platform_info errors when it cannot parse os-release."""
        m_parse.return_value = {"VERSION": "junk"}
        with pytest.raises(RuntimeError) as excinfo:
            # Use __wrapped__ to avoid hitting the
            # lru_cached value across tests
            system.get_platform_info.__wrapped__()
        expected_msg = (
            "Could not parse /etc/os-release VERSION: junk (modified to junk)"
        )
        assert expected_msg == str(excinfo.value)

    @pytest.mark.parametrize(
        "series,release,version,os_release_content",
        [
            ("xenial", "16.04", "16.04 LTS (Xenial Xerus)", OS_RELEASE_XENIAL),
            (
                "bionic",
                "18.04",
                "18.04 LTS (Bionic Beaver)",
                OS_RELEASE_BIONIC,
            ),
            ("disco", "19.04", "19.04 (Disco Dingo)", OS_RELEASE_DISCO),
        ],
    )
    def test_get_platform_info_with_version(
        self, series, release, version, os_release_content, tmpdir
    ):
        release_file = tmpdir.join("os-release")
        release_file.write(os_release_content)
        parse_dict = system.parse_os_release(release_file.strpath)

        expected = {
            "arch": "arm64",
            "distribution": "Ubuntu",
            "kernel": "kernel-ver",
            "release": release,
            "series": series,
            "type": "Linux",
            "version": version,
        }

        with mock.patch("uaclient.system.parse_os_release") as m_parse:
            with mock.patch("uaclient.util.os.uname") as m_uname:
                with mock.patch("uaclient.system.subp") as m_subp:
                    m_parse.return_value = parse_dict
                    # (sysname, nodename, release, version, machine)
                    m_uname.return_value = posix.uname_result(
                        ("", "", "kernel-ver", "", "aarch64")
                    )
                    m_subp.return_value = ("arm64\n", "")
                    # Use __wrapped__ to avoid hitting the
                    # lru_cached value across tests
                    assert expected == system.get_platform_info.__wrapped__()


class TestGetMachineId:
    def test_get_machine_id_from_config(self, FakeConfig):
        cfg = FakeConfig.for_attached_machine()
        value = system.get_machine_id(cfg)
        assert "test_machine_id" == value

    def test_get_machine_id_from_etc_machine_id(self, FakeConfig, tmpdir):
        """Presence of /etc/machine-id is returned if it exists."""
        etc_machine_id = tmpdir.join("etc-machine-id")
        assert "/etc/machine-id" == system.ETC_MACHINE_ID
        etc_machine_id.write("etc-machine-id")
        cfg = FakeConfig()
        with mock.patch(
            "uaclient.system.ETC_MACHINE_ID", etc_machine_id.strpath
        ):
            value = system.get_machine_id(cfg)
            # Test lru_cache caches /etc/machine-id from first read
            etc_machine_id.write("does-not-change")
            cached_value = system.get_machine_id(cfg)
            assert value == cached_value
        assert "etc-machine-id" == value

    def test_get_machine_id_from_var_lib_dbus_machine_id(
        self, FakeConfig, tmpdir
    ):
        """fallback to /var/lib/dbus/machine-id"""
        etc_machine_id = tmpdir.join("etc-machine-id")
        dbus_machine_id = tmpdir.join("dbus-machine-id")
        assert "/var/lib/dbus/machine-id" == system.DBUS_MACHINE_ID
        dbus_machine_id.write("dbus-machine-id")
        cfg = FakeConfig()
        with mock.patch(
            "uaclient.system.DBUS_MACHINE_ID", dbus_machine_id.strpath
        ):
            with mock.patch(
                "uaclient.system.ETC_MACHINE_ID", etc_machine_id.strpath
            ):
                value = system.get_machine_id(cfg)
        assert "dbus-machine-id" == value

    def test_get_machine_id_uses_machine_id_from_data_dir(
        self, FakeConfig, tmpdir
    ):
        """When no machine-id is found, use machine-id from data_dir."""
        data_machine_id = tmpdir.mkdir("private").join("machine-id")
        data_machine_id.write("data-machine-id")

        cfg = FakeConfig()

        def fake_exists(path):
            return bool(path == data_machine_id.strpath)

        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.side_effect = fake_exists
            value = system.get_machine_id(cfg)
        assert "data-machine-id" == value

    def test_get_machine_id_create_machine_id_in_data_dir(
        self, FakeConfig, tmpdir
    ):
        """When no machine-id is found, create one in data_dir using uuid4."""
        data_machine_id = tmpdir.mkdir("private").join("machine-id")

        cfg = FakeConfig()
        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            with mock.patch("uaclient.system.uuid.uuid4") as m_uuid4:
                m_exists.return_value = False
                m_uuid4.return_value = uuid.UUID(
                    "0123456789abcdef0123456789abcdef"
                )
                value = system.get_machine_id(cfg)
        assert "01234567-89ab-cdef-0123-456789abcdef" == value
        assert "01234567-89ab-cdef-0123-456789abcdef" == data_machine_id.read()

    @pytest.mark.parametrize("empty_value", ["", "\n"])
    def test_fallback_used_if_all_other_files_are_empty(
        self, FakeConfig, tmpdir, empty_value
    ):
        data_machine_id = tmpdir.mkdir("private").join("machine-id")
        cfg = FakeConfig().for_attached_machine(
            machine_token={"some": "thing"},
        )
        # Need to initialize the property with a noop,
        # so load_file is not called after mocked
        cfg.machine_token
        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.return_value = True
            with mock.patch(
                "uaclient.system.load_file", return_value=empty_value
            ):
                with mock.patch("uaclient.system.uuid.uuid4") as m_uuid4:
                    m_uuid4.return_value = uuid.UUID(
                        "0123456789abcdef0123456789abcdef"
                    )
                    value = system.get_machine_id(cfg)
        assert "01234567-89ab-cdef-0123-456789abcdef" == value
        assert "01234567-89ab-cdef-0123-456789abcdef" == data_machine_id.read()


class TestShouldReboot:
    @pytest.mark.parametrize("path_exists", ((True), (False)))
    @mock.patch("os.path.exists")
    def test_should_reboot_when_no_installed_pkgs_provided(
        self, m_path, path_exists
    ):
        m_path.return_value = path_exists
        assert path_exists == system.should_reboot()
        assert 1 == m_path.call_count

    @mock.patch("os.path.exists")
    @mock.patch("uaclient.system.load_file")
    def test_should_reboot_when_no_reboot_required_pkgs_exist(
        self, m_load_file, m_path
    ):
        installed_pkgs = set(["test"])
        m_path.return_value = True
        m_load_file.side_effect = FileNotFoundError()

        assert system.should_reboot(installed_pkgs)
        assert 1 == m_path.call_count
        assert 1 == m_load_file.call_count

    @pytest.mark.parametrize(
        "installed_pkgs,installed_pkgs_regex,reboot_required_pkgs,"
        "expected_ret",
        (
            (set(["a", "b", "c"]), None, "", False),
            (set(["a", "b", "c"]), None, "a", True),
            (set(["a", "b", "c"]), None, "a\ne", True),
            (set(["a", "b", "c"]), None, "d\ne", False),
            (set(["a", "b", "c"]), set(["t.."]), "a\ne", True),
            (set(["a", "b", "c"]), set(["t.."]), "one\ntwo", True),
            (None, set(["^t..$"]), "one\ntwo", True),
            (None, set(["^t..$"]), "one\nthree", False),
            (None, None, "a\ne", True),
        ),
    )
    @mock.patch("os.path.exists")
    @mock.patch("uaclient.system.load_file")
    def test_should_reboot_when_reboot_required_pkgs_exist(
        self,
        m_load_file,
        m_path,
        installed_pkgs,
        installed_pkgs_regex,
        reboot_required_pkgs,
        expected_ret,
    ):
        m_path.return_value = True
        m_load_file.return_value = reboot_required_pkgs
        assert expected_ret == system.should_reboot(
            installed_pkgs=installed_pkgs,
            installed_pkgs_regex=installed_pkgs_regex,
        )


class TestSubp:
    def test_raise_error_on_timeout(self, _subp):
        """When cmd exceeds the timeout raises a TimeoutExpired error."""
        with mock.patch("uaclient.system._subp", side_effect=_subp):
            with pytest.raises(subprocess.TimeoutExpired) as excinfo:
                system.subp(["sleep", "2"], timeout=0)
        msg = "Command '[b'sleep', b'2']' timed out after 0 seconds"
        assert msg == str(excinfo.value)

    @mock.patch("uaclient.util.time.sleep")
    def test_default_do_not_retry_on_failure_return_code(self, m_sleep, _subp):
        """When no retry_sleeps are specified, do not retry failures."""
        with mock.patch("uaclient.system._subp", side_effect=_subp):
            with pytest.raises(exceptions.ProcessExecutionError) as excinfo:
                system.subp(["ls", "--bogus"])

        assert 2 == excinfo.value.exit_code
        assert "" == excinfo.value.stdout
        assert 0 == m_sleep.call_count  # no retries

    @mock.patch("uaclient.util.time.sleep")
    def test_no_error_on_accepted_return_codes(self, m_sleep, _subp):
        """When rcs list includes the exit code, do not raise an error."""
        with mock.patch("uaclient.system._subp", side_effect=_subp):
            out, _ = system.subp(["ls", "--bogus"], rcs=[2])

        assert "" == out
        assert 0 == m_sleep.call_count  # no retries

    @mock.patch("uaclient.util.time.sleep")
    def test_retry_with_specified_sleeps_on_error(self, m_sleep, _subp):
        """When retry_sleeps given, use defined sleeps between each retry."""
        with mock.patch("uaclient.system._subp", side_effect=_subp):
            with pytest.raises(exceptions.ProcessExecutionError) as excinfo:
                system.subp(["ls", "--bogus"], retry_sleeps=[1, 3, 0.4])

        expected_error = "Failed running command 'ls --bogus' [exit(2)]"
        assert expected_error in str(excinfo.value)
        expected_sleeps = [mock.call(1), mock.call(3), mock.call(0.4)]
        assert expected_sleeps == m_sleep.call_args_list

    @mock.patch("uaclient.util.time.sleep")
    def test_retry_doesnt_consume_retry_sleeps(self, m_sleep, _subp):
        """When retry_sleeps given, use defined sleeps between each retry."""
        sleeps = [1, 3, 0.4]
        expected_sleeps = sleeps.copy()
        with mock.patch("uaclient.system._subp", side_effect=_subp):
            with pytest.raises(exceptions.ProcessExecutionError):
                system.subp(["ls", "--bogus"], retry_sleeps=sleeps)

        assert expected_sleeps == sleeps

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.system._subp")
    @mock.patch("uaclient.util.time.sleep")
    def test_retry_logs_remaining_retries(self, m_sleep, m_subp, caplog_text):
        """When retry_sleeps given, use defined sleeps between each retry."""
        sleeps = [1, 3, 0.4]
        m_subp.side_effect = exceptions.ProcessExecutionError(
            "Funky apt %d error"
        )
        with pytest.raises(exceptions.ProcessExecutionError):
            system.subp(["apt", "dostuff"], retry_sleeps=sleeps)

        logs = caplog_text()
        expected_logs = [
            "'Funky apt %d error'. Retrying 3 more times.",
            "'Funky apt %d error'. Retrying 2 more times.",
            "'Funky apt %d error'. Retrying 1 more times.",
        ]
        for log in expected_logs:
            assert log in logs

    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @pytest.mark.parametrize("capture", [True, False])
    @mock.patch("uaclient.system._subp")
    def test_log_subp_fails_stdout_stderr_capture_toggle(
        self, m_subp, capture, caplog_text
    ):
        """When subp fails, capture the logs in stdout/stderr"""
        out = "Tried downloading file"
        err = "Network error"
        m_subp.side_effect = exceptions.ProcessExecutionError(
            "Serious apt error", stdout=out, stderr=err
        )
        with pytest.raises(exceptions.ProcessExecutionError):
            system.subp(["apt", "nothing"], capture=capture)

        logs = caplog_text()
        expected_logs = ["Stderr: {}".format(err), "Stdout: {}".format(out)]
        for log in expected_logs:
            if capture:
                assert log in logs
            else:
                assert log not in logs
