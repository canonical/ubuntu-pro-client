import mock

from uaclient import apt
from uaclient.api.u.security.package_manifest.v1 import _package_manifest
from uaclient.snap import SnapPackage

M_PATH = "uaclient.api.u.security.package_manifest.v1"


@mock.patch("uaclient.snap.get_snap_info")
@mock.patch("uaclient.snap.system.subp")
@mock.patch(M_PATH + ".apt.get_installed_packages")
class TestPackageInstalledV1:
    def test_snap_packages_added(
        self, m_installed_apt_pkgs, m_sys_subp, m_get_snap_info, FakeConfig
    ):
        m_installed_apt_pkgs.return_value = []
        m_sys_subp.return_value = (
            "Name  Version Rev Tracking Publisher Notes\n"
            "helloworld 6.0.16 126 latest/stable dev1 -\n"
            "bare 1.0 5 latest/stable canonical** base\n"
            "canonical-livepatch 10.2.3 146 latest/stable canonical** -\n"
        ), ""
        m_get_snap_info.side_effect = [
            SnapPackage(
                "helloworld",
                "6.0.16",
                "126",
                "latest/stable",
                "dev1",
            ),
            SnapPackage(
                "bare",
                "1.0",
                "5",
                "latest/stable",
                "canonical**",
            ),
            SnapPackage(
                "canonical-livepatch",
                "10.2.3",
                "146",
                "latest/stable",
                "canonical**",
            ),
        ]
        result = _package_manifest(FakeConfig())
        assert (
            "snap:helloworld\tlatest/stable\t126\n"
            + "snap:bare\tlatest/stable\t5\n"
            + "snap:canonical-livepatch\tlatest/stable\t146\n"
            == result.manifest_data
        )

    def test_apt_packages_added(
        self, m_installed_apt_pkgs, m_sys_subp, m_get_snap_info, FakeConfig
    ):
        m_sys_subp.return_value = "", ""
        apt_pkgs = [
            apt.InstalledAptPackage(name="one", arch="all", version="4:1.0.2"),
            apt.InstalledAptPackage(name="two", arch="amd64", version="0.1.1"),
        ]
        m_installed_apt_pkgs.return_value = apt_pkgs
        result = _package_manifest(FakeConfig())
        assert "one\t4:1.0.2\ntwo:amd64\t0.1.1\n" == result.manifest_data

    def test_apt_snap_packages_added(
        self, m_installed_apt_pkgs, m_sys_subp, m_get_snap_info, FakeConfig
    ):
        apt_pkgs = [
            apt.InstalledAptPackage(name="one", arch="all", version="4:1.0.2"),
            apt.InstalledAptPackage(name="two", arch="amd64", version="0.1.1"),
        ]
        m_sys_subp.return_value = (
            "Name  Version Rev Tracking Publisher Notes\n"
            "helloworld 6.0.16 126 latest/stable dev1 -\n"
            "bare 1.0 5 latest/stable canonical** base\n"
            "canonical-livepatch 10.2.3 146 latest/stable canonical** -\n"
        ), ""
        m_get_snap_info.side_effect = [
            SnapPackage(
                "helloworld",
                "6.0.16",
                "126",
                "latest/stable",
                "dev1",
            ),
            SnapPackage(
                "bare",
                "1.0",
                "5",
                "latest/stable",
                "canonical**",
            ),
            SnapPackage(
                "canonical-livepatch",
                "10.2.3",
                "146",
                "latest/stable",
                "canonical**",
            ),
        ]
        m_installed_apt_pkgs.return_value = apt_pkgs
        result = _package_manifest(FakeConfig())
        assert (
            "one\t4:1.0.2\ntwo:amd64\t0.1.1\n"
            + "snap:helloworld\tlatest/stable\t126\n"
            + "snap:bare\tlatest/stable\t5\n"
            + "snap:canonical-livepatch\tlatest/stable\t146\n"
            == result.manifest_data
        )
