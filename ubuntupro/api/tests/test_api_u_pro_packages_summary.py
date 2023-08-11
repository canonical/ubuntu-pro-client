import mock

from ubuntupro.api.u.pro.packages.summary.v1 import (
    PackageSummaryResult,
    _summary,
)

M_PATH = "ubuntupro.api.u.pro.packages.summary.v1."


@mock.patch(M_PATH + "get_installed_packages_by_origin")
class TestPackagesSummaryV1:
    def test_package_summary(self, m_packages, FakeConfig):
        m_packages.return_value = {
            "all": ["pkg"],
            "esm-apps": ["pkg"] * 2,
            "esm-infra": ["pkg"] * 3,
            "main": ["pkg"] * 4,
            "multiverse": ["pkg"] * 5,
            "restricted": ["pkg"] * 6,
            "third-party": ["pkg"] * 7,
            "universe": ["pkg"] * 8,
            "unknown": ["pkg"] * 9,
        }

        result = _summary(cfg=FakeConfig())

        assert isinstance(result, PackageSummaryResult)
        assert result.summary.num_installed_packages == 1
        assert result.summary.num_esm_apps_packages == 2
        assert result.summary.num_esm_infra_packages == 3
        assert result.summary.num_main_packages == 4
        assert result.summary.num_multiverse_packages == 5
        assert result.summary.num_restricted_packages == 6
        assert result.summary.num_third_party_packages == 7
        assert result.summary.num_universe_packages == 8
        assert result.summary.num_unknown_packages == 9
