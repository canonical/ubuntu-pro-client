import mock

from uaclient.api.u.pro.packages.updates.v1 import (
    PackageUpdatesResult,
    _updates,
)

M_PATH = "uaclient.api.u.pro.packages.updates.v1."


class TestPackagesUpdatesV1:
    @mock.patch(M_PATH + "get_ua_info")
    @mock.patch(M_PATH + "get_installed_packages_by_origin")
    @mock.patch(M_PATH + "filter_security_updates")
    @mock.patch(M_PATH + "create_updates_list")
    def test_package_updates(
        self, m_updates, m_filter, _m_packages, _m_ua_info, FakeConfig
    ):
        m_filter.return_value = {
            "esm-apps": ["update"],
            "esm-infra": ["update"] * 2,
            "standard-security": ["update"] * 3,
            "standard-updates": ["update"] * 4,
        }
        m_updates.return_value = [
            {
                "download_size": 123,
                "origin": "somewhere",
                "package": "pkg",
                "service_name": "service",
                "status": "status",
                "version": "version",
            }
        ]

        result = _updates(cfg=FakeConfig())

        assert isinstance(result, PackageUpdatesResult)

        assert result.summary.num_esm_apps_updates == 1
        assert result.summary.num_esm_infra_updates == 2
        assert result.summary.num_standard_security_updates == 3
        assert result.summary.num_standard_updates == 4
        assert result.summary.num_updates == 10

        assert len(result.updates) == 1
        assert result.updates[0].download_size == 123
        assert result.updates[0].origin == "somewhere"
        assert result.updates[0].package == "pkg"
        assert result.updates[0].provided_by == "service"
        assert result.updates[0].status == "status"
        assert result.updates[0].version == "version"
