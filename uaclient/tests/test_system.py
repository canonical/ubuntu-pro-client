import datetime
import logging
import os
import subprocess
import textwrap
import uuid

import mock
import pytest

from uaclient import apt, exceptions, messages, system


class TestGetKernelInfo:
    @pytest.mark.parametrize(
        [
            "uname_machine",
            "uname_release",
            "proc_version_signature_side_effect",
            "build_date",
            "expected",
        ],
        (
            (
                "x86_64",
                "5.14.0-1024-oem",
                "Ubuntu 5.14.0-1024.26-oem 5.15.100",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="5.14.0-1024-oem",
                    proc_version_signature_version="5.14.0-1024.26-oem",
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=5,
                    minor=14,
                    patch=0,
                    abi="1024",
                    flavor="oem",
                ),
            ),
            (
                "aarch64",
                "5.14.0-1024-oem",
                "Ubuntu 5.14.0-1024.26-oem 5.15.100",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="aarch64",
                    uname_release="5.14.0-1024-oem",
                    proc_version_signature_version="5.14.0-1024.26-oem",
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=5,
                    minor=14,
                    patch=0,
                    abi="1024",
                    flavor="oem",
                ),
            ),
            (
                "x86_64",
                "4.4.0-21-generic",
                "Ubuntu 4.4.0-21.37-generic 4.15.100",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="4.4.0-21-generic",
                    proc_version_signature_version="4.4.0-21.37-generic",
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=4,
                    minor=4,
                    patch=0,
                    abi="21",
                    flavor="generic",
                ),
            ),
            (
                "x86_64",
                "5.4.0-52-generic",
                "Ubuntu 5.4.0-52.37-generic 5.15.100",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="5.4.0-52-generic",
                    proc_version_signature_version="5.4.0-52.37-generic",
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=5,
                    minor=4,
                    patch=0,
                    abi="52",
                    flavor="generic",
                ),
            ),
            (
                "x86_64",
                "5.4.0-52-generic",
                "Ubuntu 5.4.0-52.37~20.04-generic 5.15.100",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="5.4.0-52-generic",
                    proc_version_signature_version="5.4.0-52.37~20.04-generic",
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=5,
                    minor=4,
                    patch=0,
                    abi="52",
                    flavor="generic",
                ),
            ),
            (
                "x86_64",
                "5.4.0-52-generic",
                Exception(),
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="5.4.0-52-generic",
                    proc_version_signature_version=None,
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=5,
                    minor=4,
                    patch=0,
                    abi="52",
                    flavor="generic",
                ),
            ),
            (
                "x86_64",
                "5.4.0-1021-aws-fips",
                "Ubuntu 5.4.0-1021.21+fips2-aws-fips 5.4.44",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="5.4.0-1021-aws-fips",
                    proc_version_signature_version="5.4.0-1021.21+fips2-aws-fips",  # noqa: E501
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=5,
                    minor=4,
                    patch=0,
                    abi="1021",
                    flavor="aws-fips",
                ),
            ),
            (
                "x86_64",
                "4.4.0-1017-fips",
                "Ubuntu 4.4.0-1017.22~recert1-fips 4.4.185",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="4.4.0-1017-fips",
                    proc_version_signature_version="4.4.0-1017.22~recert1-fips",  # noqa: E501
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=4,
                    minor=4,
                    patch=0,
                    abi="1017",
                    flavor="fips",
                ),
            ),
            (
                "x86_64",
                "4.4.0-1017.something.invalid-fips",
                "Ubuntu 4.4.0-1017.22~recert1-fips 4.4.185",
                datetime.datetime(2023, 4, 6, 7, 48, 48),
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="4.4.0-1017.something.invalid-fips",
                    proc_version_signature_version="4.4.0-1017.22~recert1-fips",  # noqa: E501
                    build_date=datetime.datetime(2023, 4, 6, 7, 48, 48),
                    major=None,
                    minor=None,
                    patch=None,
                    abi=None,
                    flavor=None,
                ),
            ),
            (
                "x86_64",
                "4.4.0-1017.something.invalid-fips",
                "Ubuntu 4.4.0-1017.22~recert1-fips 4.4.185",
                None,
                system.KernelInfo(
                    uname_machine_arch="x86_64",
                    uname_release="4.4.0-1017.something.invalid-fips",
                    proc_version_signature_version="4.4.0-1017.22~recert1-fips",  # noqa: E501
                    build_date=None,
                    major=None,
                    minor=None,
                    patch=None,
                    abi=None,
                    flavor=None,
                ),
            ),
        ),
    )
    @mock.patch("uaclient.system._get_kernel_build_date")
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.system.os.uname")
    def test_get_kernel_info(
        self,
        m_uname,
        m_load_file,
        m_get_kernel_build_date,
        uname_machine,
        uname_release,
        proc_version_signature_side_effect,
        build_date,
        expected,
    ):
        m_uname.return_value = mock.MagicMock(
            release=uname_release, machine=uname_machine
        )
        m_load_file.side_effect = [proc_version_signature_side_effect]
        m_get_kernel_build_date.return_value = build_date
        assert system.get_kernel_info.__wrapped__() == expected

    @pytest.mark.parametrize(
        [
            "uname_result",
            "changelog_timestamp",
            "expected",
        ],
        [
            (
                os.uname_result(
                    [
                        "",
                        "",
                        "",
                        "#20-Ubuntu SMP PREEMPT_DYNAMIC Thu Apr  6 07:48:48 UTC 2023",  # noqa: E501
                        "",
                    ]
                ),
                mock.sentinel.changelog_timestamp,
                datetime.datetime(
                    2023, 4, 6, 7, 48, 48, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                os.uname_result(
                    [
                        "",
                        "",
                        "",
                        "#33~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC Mon Jan 30 17:03:34 UTC 2",  # noqa: E501
                        "",
                    ]
                ),
                mock.sentinel.changelog_timestamp,
                mock.sentinel.changelog_timestamp,
            ),
            (
                os.uname_result(["", "", "", "corrupted", ""]),
                mock.sentinel.changelog_timestamp,
                mock.sentinel.changelog_timestamp,
            ),
        ],
    )
    @mock.patch("uaclient.system._get_kernel_changelog_timestamp")
    def test_get_kernel_build_date(
        self,
        m_get_kernel_changelog_timestamp,
        uname_result,
        changelog_timestamp,
        expected,
    ):
        m_get_kernel_changelog_timestamp.return_value = changelog_timestamp
        assert expected == system._get_kernel_build_date(uname_result)

    @pytest.mark.parametrize(
        [
            "uname_result",
            "is_container",
            "stat_result",
            "expected_stat_call_args",
            "expected",
        ],
        [
            (
                None,
                True,
                None,
                [],
                None,
            ),
            (
                os.uname_result(["", "", "version-here", "", ""]),
                False,
                Exception(),
                [
                    mock.call(
                        "/usr/share/doc/linux-image-version-here/changelog.Debian.gz"  # noqa: E501
                    )
                ],
                None,
            ),
            (
                os.uname_result(["", "", "version-here", "", ""]),
                False,
                [os.stat_result([0, 0, 0, 0, 0, 0, 0, 0, 1680762951, 0])],
                [
                    mock.call(
                        "/usr/share/doc/linux-image-version-here/changelog.Debian.gz"  # noqa: E501
                    )
                ],
                datetime.datetime(
                    2023, 4, 6, 6, 35, 51, tzinfo=datetime.timezone.utc
                ),
            ),
        ],
    )
    @mock.patch("os.stat")
    @mock.patch("uaclient.system.is_container")
    def test_get_kernel_changelog_timestamp(
        self,
        m_is_container,
        m_os_stat,
        uname_result,
        is_container,
        stat_result,
        expected_stat_call_args,
        expected,
    ):
        m_is_container.return_value = is_container
        m_os_stat.side_effect = stat_result
        assert expected == system._get_kernel_changelog_timestamp(uname_result)
        assert expected_stat_call_args == m_os_stat.call_args_list


class TestGetDpkgArch:
    @pytest.mark.parametrize(
        "stdout, expected",
        (
            (
                "amd64",
                "amd64",
            ),
            (
                "arm64\n",
                "arm64",
            ),
            (
                "   arm64    \n",
                "arm64",
            ),
        ),
    )
    @mock.patch("uaclient.system.subp")
    def test_get_dpkg_arch(self, m_subp, stdout, expected):
        m_subp.return_value = (stdout, "")
        assert system.get_dpkg_arch.__wrapped__() == expected
        assert m_subp.call_args_list == [
            mock.call(["dpkg", "--print-architecture"])
        ]


class TestGetVirtType:
    @pytest.mark.parametrize(
        [
            "subp_side_effect",
            "load_file_side_effect",
            "expected",
        ],
        [
            ([("", "")], None, ""),
            ([("lxc\n", "")], None, "lxc"),
            ([("lxc\n", "anything")], None, "lxc"),
            (
                exceptions.ProcessExecutionError(cmd="", stdout="", stderr=""),
                [""],
                "",
            ),
            (
                exceptions.ProcessExecutionError(cmd="", stdout="", stderr=""),
                ["line\nline\nlinedockerline\nline"],
                "docker",
            ),
            (
                exceptions.ProcessExecutionError(cmd="", stdout="", stderr=""),
                ["line\nline\nlinebuildkitline\nline"],
                "docker",
            ),
            (
                exceptions.ProcessExecutionError(cmd="", stdout="", stderr=""),
                ["line\nline\nlinebuildahline\nline"],
                "podman",
            ),
            (
                exceptions.ProcessExecutionError(cmd="", stdout="", stderr=""),
                ["line\nline\nline\nline"],
                "",
            ),
            (
                exceptions.ProcessExecutionError(cmd="", stdout="", stderr=""),
                FileNotFoundError(),
                "",
            ),
        ],
    )
    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.system.subp")
    def test_get_virt_type(
        self,
        m_subp,
        m_load_file,
        subp_side_effect,
        load_file_side_effect,
        expected,
    ):
        m_subp.side_effect = subp_side_effect
        m_load_file.side_effect = load_file_side_effect
        assert expected == system.get_virt_type.__wrapped__()


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


class TestIsSupported:
    @pytest.mark.parametrize(
        "series,expected", (("sup1", True), ("unsup", False))
    )
    @mock.patch("uaclient.system.subp")
    def test_return_supported_series(self, subp, series, expected):
        subp.return_value = "sup1\nsup2\nsup3", ""
        assert expected is system.is_supported.__wrapped__(series)
        assert [
            mock.call(["/usr/bin/ubuntu-distro-info", "--supported"])
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


class TestIsDesktop:
    @pytest.mark.parametrize(
        ["installed_packages", "expected"],
        [
            ([], False),
            (
                [
                    apt.InstalledAptPackage(
                        name="not-desktop", version="", arch=""
                    ),
                    apt.InstalledAptPackage(
                        name="desktop-not-ubuntu", version="", arch=""
                    ),
                ],
                False,
            ),
            (
                [
                    apt.InstalledAptPackage(
                        name="not-desktop", version="", arch=""
                    ),
                    apt.InstalledAptPackage(
                        name="ubuntu-desktop", version="", arch=""
                    ),
                ],
                True,
            ),
            (
                [
                    apt.InstalledAptPackage(
                        name="not-desktop", version="", arch=""
                    ),
                    apt.InstalledAptPackage(
                        name="ubuntu-desktop-minimal", version="", arch=""
                    ),
                ],
                True,
            ),
            (
                [
                    apt.InstalledAptPackage(
                        name="not-desktop", version="", arch=""
                    ),
                    apt.InstalledAptPackage(
                        name="kubuntu-desktop", version="", arch=""
                    ),
                ],
                True,
            ),
            (
                [
                    apt.InstalledAptPackage(
                        name="not-desktop", version="", arch=""
                    ),
                    apt.InstalledAptPackage(
                        name="xubuntu-desktop", version="", arch=""
                    ),
                ],
                True,
            ),
            (
                [
                    apt.InstalledAptPackage(
                        name="not-desktop", version="", arch=""
                    ),
                    apt.InstalledAptPackage(
                        name="lubuntu-desktop", version="", arch=""
                    ),
                ],
                True,
            ),
        ],
    )
    @mock.patch("uaclient.apt.get_installed_packages")
    def test_true_systemd_detect_virt_success(
        self,
        m_installed_packages,
        installed_packages,
        expected,
    ):
        m_installed_packages.return_value = installed_packages
        assert expected == system.is_desktop.__wrapped__()


class TestParseOSRelease:
    @pytest.mark.parametrize(
        "content, expected",
        (
            (
                """\
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
""",
                {
                    "NAME": "Ubuntu",
                    "VERSION": "16.04.5 LTS (Xenial Xerus)",
                    "ID": "ubuntu",
                    "ID_LIKE": "debian",
                    "PRETTY_NAME": "Ubuntu 16.04.5 LTS",
                    "VERSION_ID": "16.04",
                    "HOME_URL": "http://www.ubuntu.com/",
                    "SUPPORT_URL": "http://help.ubuntu.com/",
                    "BUG_REPORT_URL": "http://bugs.launchpad.net/ubuntu/",
                    "VERSION_CODENAME": "xenial",
                    "UBUNTU_CODENAME": "xenial",
                },
            ),
            (
                """\
NAME="Ubuntu"
VERSION="18.04.1 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04.1 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic
""",
                {
                    "NAME": "Ubuntu",
                    "VERSION": "18.04.1 LTS (Bionic Beaver)",
                    "ID": "ubuntu",
                    "ID_LIKE": "debian",
                    "PRETTY_NAME": "Ubuntu 18.04.1 LTS",
                    "VERSION_ID": "18.04",
                    "HOME_URL": "https://www.ubuntu.com/",
                    "SUPPORT_URL": "https://help.ubuntu.com/",
                    "BUG_REPORT_URL": "https://bugs.launchpad.net/ubuntu/",
                    "PRIVACY_POLICY_URL": "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy",  # noqa: E501
                    "VERSION_CODENAME": "bionic",
                    "UBUNTU_CODENAME": "bionic",
                },
            ),
            (
                """\
PRETTY_NAME="Ubuntu 22.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.1 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
""",
                {
                    "PRETTY_NAME": "Ubuntu 22.04.1 LTS",
                    "NAME": "Ubuntu",
                    "VERSION_ID": "22.04",
                    "VERSION": "22.04.1 LTS (Jammy Jellyfish)",
                    "VERSION_CODENAME": "jammy",
                    "ID": "ubuntu",
                    "ID_LIKE": "debian",
                    "HOME_URL": "https://www.ubuntu.com/",
                    "SUPPORT_URL": "https://help.ubuntu.com/",
                    "BUG_REPORT_URL": "https://bugs.launchpad.net/ubuntu/",
                    "PRIVACY_POLICY_URL": "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy",  # noqa: E501
                    "UBUNTU_CODENAME": "jammy",
                },
            ),
            (
                """\
PRETTY_NAME="Ubuntu Kinetic Kudu (development branch)"
NAME="Ubuntu"
VERSION_ID="22.10"
VERSION="22.10 (Kinetic Kudu)"
VERSION_CODENAME=kinetic
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=kinetic
LOGO=ubuntu-logo
""",
                {
                    "PRETTY_NAME": "Ubuntu Kinetic Kudu (development branch)",
                    "NAME": "Ubuntu",
                    "VERSION_ID": "22.10",
                    "VERSION": "22.10 (Kinetic Kudu)",
                    "VERSION_CODENAME": "kinetic",
                    "ID": "ubuntu",
                    "ID_LIKE": "debian",
                    "HOME_URL": "https://www.ubuntu.com/",
                    "SUPPORT_URL": "https://help.ubuntu.com/",
                    "BUG_REPORT_URL": "https://bugs.launchpad.net/ubuntu/",
                    "PRIVACY_POLICY_URL": "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy",  # noqa: E501
                    "UBUNTU_CODENAME": "kinetic",
                    "LOGO": "ubuntu-logo",
                },
            ),
        ),
    )
    @mock.patch("uaclient.system.load_file")
    def test_parse_os_release(self, m_load_file, content, expected):
        """_parse_os_release returns a dict of values from /etc/os-release."""
        m_load_file.return_value = content
        assert expected == system._parse_os_release.__wrapped__()
        assert m_load_file.call_args_list == [mock.call("/etc/os-release")]


@mock.patch("uaclient.system.load_file")
class TestGetDistroInfo:
    content = """\
version,codename,series,created,release,eol,eol-server,eol-esm
16.04 LTS,Xenial Xerus,xenial,2015-10-22,2016-04-21,2021-04-21,2021-04-21,2024-04-23
20.04 LTS,Focal Fossa,focal,2019-10-17,2020-04-23,2025-04-23,2025-04-23,2030-04-23
22.10,Kinetic Kudu,kinetic,2022-04-21,2022-10-20,2023-07-20
"""  # noqa: E501

    def test_get_distro_info(self, m_load_file):
        m_load_file.return_value = self.content

        xenial_di = system.get_distro_info.__wrapped__("xenial")
        assert 4 == xenial_di.eol.month
        assert 2021 == xenial_di.eol.year
        assert 4 == xenial_di.eol_esm.month
        assert 2026 == xenial_di.eol_esm.year

        focal_di = system.get_distro_info.__wrapped__("focal")
        assert 4 == focal_di.eol.month
        assert 2025 == focal_di.eol.year
        assert 4 == focal_di.eol_esm.month
        assert 2030 == focal_di.eol_esm.year

        kinetic_di = system.get_distro_info.__wrapped__("kinetic")
        assert 7 == kinetic_di.eol.month
        assert 2023 == kinetic_di.eol.year
        assert 7 == kinetic_di.eol_esm.month
        assert 2023 == kinetic_di.eol_esm.year

        with pytest.raises(exceptions.UbuntuProError) as excinfo:
            system.get_distro_info.__wrapped__("nonexistent")
        assert (
            messages.E_MISSING_SERIES_IN_DISTRO_INFO_FILE.format(
                series="nonexistent"
            )
            == excinfo.value.named_msg
        )

    def test_no_csv_file(self, m_load_file):
        m_load_file.side_effect = FileNotFoundError

        with pytest.raises(exceptions.UbuntuProError) as excinfo:
            system.get_distro_info.__wrapped__("focal")
        assert messages.E_MISSING_DISTRO_INFO_FILE == excinfo.value.named_msg


class TestGetReleaseInfo:
    @pytest.mark.parametrize(
        ["version", "expected_exception"],
        (
            (
                "junk",
                exceptions.ParsingErrorOnOSReleaseFile,
            ),
            (
                "22.04 LTS",
                exceptions.MissingSeriesOnOSReleaseFile,
            ),
        ),
    )
    @mock.patch("uaclient.system._parse_os_release")
    def test_get_release_info_error(
        self, m_parse_os_release, version, expected_exception
    ):
        """get_release_info errors when it cannot parse os-release."""
        m_parse_os_release.return_value = {"VERSION": version}
        with pytest.raises(expected_exception):
            # Use __wrapped__ to avoid hitting the
            # lru_cached value across tests
            system.get_release_info.__wrapped__()

    @pytest.mark.parametrize(
        ["os_release", "expected"],
        [
            (
                {
                    "NAME": "Ubuntu",
                    "VERSION": "16.04.5 LTS (Xenial Xerus)",
                },
                system.ReleaseInfo(
                    distribution="Ubuntu",
                    release="16.04",
                    series="xenial",
                    pretty_version="16.04 LTS (Xenial Xerus)",
                ),
            ),
            (
                {
                    "NAME": "Ubuntu",
                    "VERSION": "18.04.1 LTS (Bionic Beaver)",
                },
                system.ReleaseInfo(
                    distribution="Ubuntu",
                    release="18.04",
                    series="bionic",
                    pretty_version="18.04 LTS (Bionic Beaver)",
                ),
            ),
            (
                {
                    "NAME": "Ubuntu",
                    "VERSION": "22.04.1 LTS (Jammy Jellyfish)",
                },
                system.ReleaseInfo(
                    distribution="Ubuntu",
                    release="22.04",
                    series="jammy",
                    pretty_version="22.04 LTS (Jammy Jellyfish)",
                ),
            ),
            (
                {
                    "NAME": "Ubuntu",
                    "VERSION": "22.10 (Kinetic Kudu)",
                },
                system.ReleaseInfo(
                    distribution="Ubuntu",
                    release="22.10",
                    series="kinetic",
                    pretty_version="22.10 (Kinetic Kudu)",
                ),
            ),
            (
                {
                    "NAME": "Ubuntu",
                    "VERSION": "22.04 LTS",
                    "VERSION_CODENAME": "Jammy",
                },
                system.ReleaseInfo(
                    distribution="Ubuntu",
                    release="22.04",
                    series="jammy",
                    pretty_version="22.04 LTS",
                ),
            ),
            (
                {
                    "NAME": "Ubuntu",
                    "VERSION": "CORRUPTED",
                    "VERSION_CODENAME": "Jammy",
                    "VERSION_ID": "22.04",
                },
                system.ReleaseInfo(
                    distribution="Ubuntu",
                    release="22.04",
                    series="jammy",
                    pretty_version="CORRUPTED",
                ),
            ),
        ],
    )
    @mock.patch("uaclient.system.get_kernel_info")
    @mock.patch("uaclient.system.get_dpkg_arch")
    @mock.patch("uaclient.system._parse_os_release")
    @mock.patch("uaclient.system.get_virt_type")
    def test_get_release_info_with_version(
        self,
        m_get_virt_type,
        m_parse_os_release,
        m_get_dpkg_arch,
        m_get_kernel_info,
        os_release,
        expected,
    ):
        m_parse_os_release.return_value = os_release
        assert expected == system.get_release_info.__wrapped__()


@mock.patch("uaclient.files.state_files.machine_id_file.write")
class TestGetMachineId:
    def test_get_machine_id_from_config(
        self, _m_machine_id_file_write, FakeConfig
    ):
        cfg = FakeConfig.for_attached_machine()
        value = system.get_machine_id(cfg)
        assert "test_machine_id" == value

    @mock.patch("uaclient.files.state_files.machine_id_file.read")
    def test_get_machine_id_from_etc_machine_id(
        self,
        m_machine_id_file_read,
        _m_machine_id_file_write,
        FakeConfig,
        tmpdir,
    ):
        """Presence of /etc/machine-id is returned if it exists."""
        etc_machine_id = tmpdir.join("etc-machine-id")
        m_machine_id_file_read.return_value = None
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

    @mock.patch("uaclient.files.state_files.machine_id_file.read")
    def test_get_machine_id_from_var_lib_dbus_machine_id(
        self,
        m_machine_id_file_read,
        _m_machine_id_file_write,
        FakeConfig,
        tmpdir,
    ):
        """fallback to /var/lib/dbus/machine-id"""
        m_machine_id_file_read.return_value = None
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

    @mock.patch("uaclient.files.state_files.machine_id_file.read")
    def test_get_machine_id_uses_machine_id_from_data_dir(
        self, m_machine_id_file_read, _m_machine_id_file_write, FakeConfig
    ):
        cfg = FakeConfig()
        m_machine_id_file_read.return_value = "data-machine-id"

        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.return_value = False
            value = system.get_machine_id(cfg)
        assert "data-machine-id" == value

    @mock.patch("uaclient.files.state_files.machine_id_file.read")
    def test_get_machine_id_create_machine_id_in_data_dir(
        self, m_machine_id_file_read, m_machine_id_file_write, FakeConfig
    ):
        """When no machine-id is found, create one in data_dir using uuid4."""

        cfg = FakeConfig()
        m_machine_id_file_read.return_value = None
        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            with mock.patch("uaclient.system.uuid.uuid4") as m_uuid4:
                m_exists.return_value = False
                m_uuid4.return_value = uuid.UUID(
                    "0123456789abcdef0123456789abcdef"
                )
                value = system.get_machine_id(cfg)

        assert "01234567-89ab-cdef-0123-456789abcdef" == value
        assert [
            mock.call("01234567-89ab-cdef-0123-456789abcdef")
        ] == m_machine_id_file_write.call_args_list

    @pytest.mark.parametrize("empty_value", ["", "\n"])
    @mock.patch("uaclient.files.state_files.machine_id_file.read")
    def test_fallback_used_if_all_other_files_are_empty(
        self,
        m_machine_id_file_read,
        m_machine_id_file_write,
        FakeConfig,
        empty_value,
    ):
        m_machine_id_file_read.return_value = None
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
        assert [
            mock.call("01234567-89ab-cdef-0123-456789abcdef")
        ] == m_machine_id_file_write.call_args_list


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


class TestWriteFile:
    @mock.patch("os.unlink")
    @mock.patch("os.rename")
    @mock.patch("os.makedirs")
    @mock.patch("os.chmod")
    @mock.patch("tempfile.NamedTemporaryFile")
    def test_delete_tempfile_on_error(
        self,
        m_NamedTemporaryFile,
        m_chmod,
        m_makedirs,
        m_rename,
        m_unlink,
    ):
        test_tmpfile = mock.MagicMock()
        test_tmpfile.name = "test_tmpfile"
        m_NamedTemporaryFile.return_value = test_tmpfile

        m_rename.side_effect = Exception()

        with pytest.raises(Exception):
            system.write_file("test", "test")

        assert [mock.call("test_tmpfile")] == m_unlink.call_args_list


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
            "Invalid command specified 'Funky apt %d error'.",
            "Retrying 3 more times.",
            "Invalid command specified 'Funky apt %d error'.",
            "Retrying 2 more times.",
            "Invalid command specified 'Funky apt %d error'.",
            "Retrying 1 more times.",
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

    @pytest.mark.parametrize(
        [
            "override_env_vars",
            "os_environ",
            "expected_env_arg",
        ],
        (
            (None, {}, None),
            (None, {"test": "val"}, None),
            ({}, {"test": "val"}, None),
            ({"set": "new"}, {"test": "val"}, {"test": "val", "set": "new"}),
            (
                {"set": "new", "test": "newval"},
                {"test": "val"},
                {"test": "newval", "set": "new"},
            ),
        ),
    )
    @mock.patch("subprocess.Popen")
    def test_subp_uses_environment_variables(
        self,
        m_popen,
        override_env_vars,
        os_environ,
        expected_env_arg,
        _subp,
    ):
        mock_process = mock.MagicMock(returncode=0)
        mock_process.communicate.return_value = (b"", b"")
        m_popen.return_value = mock_process

        with mock.patch("os.environ", os_environ):
            _subp(["apt", "nothing"], override_env_vars=override_env_vars)

        assert [
            mock.call(
                [b"apt", b"nothing"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=expected_env_arg,
            )
        ] == m_popen.call_args_list

    @mock.patch("subprocess.Popen")
    def test_subp_no_pipe_stdouterr(
        self,
        m_popen,
        _subp,
    ):
        mock_process = mock.MagicMock(returncode=0)
        mock_process.communicate.return_value = (b"", b"")
        m_popen.return_value = mock_process

        _subp(["fake"], pipe_stdouterr=False)

        assert [
            mock.call(
                [b"fake"],
                stdout=None,
                stderr=None,
                env=None,
            )
        ] == m_popen.call_args_list


class TestIsSystemdServiceActive:
    @pytest.mark.parametrize(
        [
            "subp_side_effect",
            "expected_return",
        ],
        (
            (None, True),
            (exceptions.ProcessExecutionError("test"), False),
        ),
    )
    @mock.patch("uaclient.system.subp")
    def test_is_systemd_unit_active(
        self,
        m_subp,
        subp_side_effect,
        expected_return,
    ):
        m_subp.side_effect = subp_side_effect
        assert expected_return == system.is_systemd_unit_active("test")


class TestGetCpuInfo:
    @pytest.mark.parametrize(
        "cpuinfo,vendor_id,model,stepping",
        (
            (
                textwrap.dedent(
                    """
                processor       : 6
                vendor_id       : GenuineIntel
                cpu family      : 6
                model           : 142
                model name      : Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz
                stepping        : 10

                processor       : 7
                vendor_id       : GenuineIntel
                cpu family      : 6
                model           : 142
                model name      : Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz
                stepping        : 10"""
                ),
                "intel",
                142,
                10,
            ),
            (
                textwrap.dedent(
                    """
                processor       : 6
                vendor_id       : test
                cpu family      : 6
                model           : 148
                model name      : Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz
                stepping        : 12

                processor       : 7
                vendor_id       : GenuineIntel
                cpu family      : 6
                model           : 142
                model name      : Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz
                stepping        : 10"""
                ),
                "test",
                148,
                12,
            ),
            (
                textwrap.dedent(
                    """
                processor       : 6
                cpu family      : 6
                model name      : Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz

                processor       : 7
                cpu family      : 6
                model name      : Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz"""
                ),
                "",
                None,
                None,
            ),
        ),
    )
    @mock.patch("uaclient.system.load_file")
    def test_get_cpu_vendor(
        self, m_load_file, cpuinfo, vendor_id, model, stepping
    ):
        m_load_file.return_value = cpuinfo
        assert vendor_id == system.get_cpu_info.__wrapped__().vendor_id
        assert model == system.get_cpu_info.__wrapped__().model
        assert stepping == system.get_cpu_info.__wrapped__().stepping


class TestGetUserCacheDir:
    @pytest.mark.parametrize(
        [
            "is_root",
            "xdg_cache_home",
            "expanduser_result",
            "expected",
        ],
        (
            (True, None, None, "/run/ubuntu-advantage"),
            (False, None, "/home/user", "/home/user/.cache/ubuntu-pro"),
            (False, "/something", "/home/user", "/something/ubuntu-pro"),
        ),
    )
    @mock.patch("os.path.expanduser")
    @mock.patch("os.environ.get")
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_get_user_cache_dir(
        self,
        m_we_are_currently_root,
        m_environ_get,
        m_expanduser,
        is_root,
        xdg_cache_home,
        expanduser_result,
        expected,
    ):
        m_we_are_currently_root.return_value = is_root
        m_environ_get.return_value = xdg_cache_home
        m_expanduser.return_value = expanduser_result
        assert expected == system.get_user_cache_dir()


class TestGetRebootRequiredPkgs:
    @mock.patch("uaclient.system.load_file")
    def test_when_no_reboot_required_file_is_found(self, m_load_file):
        m_load_file.side_effect = FileNotFoundError()
        assert system.get_reboot_required_pkgs() is None

    @pytest.mark.parametrize(
        "reboot_required_pkgs,expected_standard_pkgs,expected_kernel_pkgs",
        (
            ("", [], []),
            ("pkg1\npkg2", ["pkg1", "pkg2"], []),
            (
                "pkg1\nlinux-image-pkg\npkg2\nlinux-base-pkg",
                ["pkg1", "pkg2"],
                ["linux-base-pkg", "linux-image-pkg"],
            ),
            (
                "linux-image-pkg\nlinux-base-pkg",
                [],
                ["linux-base-pkg", "linux-image-pkg"],
            ),
        ),
    )
    @mock.patch("uaclient.system.load_file")
    def test_reboot_required_pkgs(
        self,
        m_load_file,
        reboot_required_pkgs,
        expected_standard_pkgs,
        expected_kernel_pkgs,
    ):
        m_load_file.return_value = reboot_required_pkgs
        reboot_required_pkgs = system.get_reboot_required_pkgs()

        assert reboot_required_pkgs is not None
        assert expected_standard_pkgs == reboot_required_pkgs.standard_packages
        assert expected_kernel_pkgs == reboot_required_pkgs.kernel_packages


@mock.patch("uaclient.system.util.we_are_currently_root")
class TestGetInstalledUbuntuKernels:
    def test_non_root_user_raises_error(self, m_is_root):
        m_is_root.return_value = False

        with pytest.raises(RuntimeError) as e:
            system.get_installed_ubuntu_kernels()

        assert "needs to be executed as root" in e.value.args[0]

    @pytest.mark.parametrize(
        "installed,files_in_boot,valid_file,expected_return",
        (
            (
                ["linux-image-4.4.0-1020-kvm", "other_package"],
                ["/boot/vmlinuz-4.4.0-1020-kvm"],
                True,
                ["4.4.0-1020-kvm"],
            ),
            (
                ["linux-image-4.4.0-1020-kvm", "other_package"],
                ["/boot/vmlinux-4.4.0-1020-kvm"],
                True,
                ["4.4.0-1020-kvm"],
            ),
            (
                [
                    "linux-image-5.4.0-39-generic",
                    "linux-image-4.15.0-118-generic",
                    "other package",
                ],
                [
                    "/boot/vmlinuz-5.4.0-39-generic",
                    "/boot/vmlinuz-4.15.0-118-generic",
                ],
                True,
                ["5.4.0-39-generic", "4.15.0-118-generic"],
            ),
            (
                ["some package", "other_package"],
                ["/boot/vmlinuz-4.4.0-1020-kvm"],
                True,
                [],
            ),
            (
                ["linux-image-4.4.0-1020-kvm", "other_package"],
                [],
                True,
                [],
            ),
            (
                ["linux-image-4.4.0-1020-kvm", "other_package"],
                ["/boot/vmlinuz-4.4.0-1020-kvm"],
                False,
                [],
            ),
            (
                ["linux-image-5.8.0-63-generic", "linux-image-5.6.0-1056-oem"],
                [
                    "/boot/vmlinuz-5.6.0-1056-oem",
                    "/boot/vmlinuz-5.4.0-77-generic",
                ],
                True,
                ["5.6.0-1056-oem"],
            ),
        ),
    )
    @mock.patch("uaclient.system.subp")
    @mock.patch("uaclient.system.glob.glob")
    @mock.patch("uaclient.apt.get_installed_packages_names")
    def test_only_valid_packages_returned(
        self,
        m_package_names,
        m_glob,
        m_subp,
        m_is_root,
        installed,
        files_in_boot,
        valid_file,
        expected_return,
    ):
        m_is_root.return_value = True
        m_package_names.return_value = installed
        m_glob.return_value = files_in_boot
        m_subp.return_value = (
            ("Some Linux kernel here", False)
            if valid_file
            else ("no good", False)
        )

        assert expected_return == system.get_installed_ubuntu_kernels()
