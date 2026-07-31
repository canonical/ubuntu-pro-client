import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import release_catalog  # noqa: E402
from release_catalog import (  # noqa: E402
    Release,
    ReleaseCatalog,
    load_csv_metadata,
)

# A small, chronologically-ordered sample mirroring distro-info output.
CODENAMES = [
    "xenial",
    "bionic",
    "focal",
    "jammy",
    "noble",
    "questing",
    "resolute",
    "stonking",
]
SUPPORTED = ["jammy", "noble", "resolute", "stonking"]
SUPPORTED_ESM = ["bionic", "focal", "jammy", "noble", "resolute"]
DEVEL = ["stonking"]

METADATA = {
    "xenial": {
        "version": "16.04 LTS",
        "created": "2015-10-22",
        "release": "2016-04-21",
        "eol": "2021-04-30",
        "eol-esm": "2026-04-23",
    },
    "resolute": {
        "version": "26.04 LTS",
        "created": "2025-10-09",
        "release": "2026-04-23",
        "eol": "2031-05-29",
        "eol-esm": "2036-04-23",
    },
    "stonking": {
        "version": "26.10",
        "created": "2026-04-24",
        "release": "2026-10-15",
        "eol": "2027-07-15",
    },
}


@pytest.fixture
def catalog():
    return ReleaseCatalog.from_data(
        CODENAMES, SUPPORTED, SUPPORTED_ESM, DEVEL, METADATA
    )


class TestFromData:
    def test_preserves_chronological_order(self, catalog):
        assert [r.series for r in catalog.ordered] == CODENAMES

    def test_order_index_matches_position(self, catalog):
        assert catalog.order_of("xenial") == 0
        assert catalog.order_of("stonking") == 7

    def test_status_derivation(self, catalog):
        # xenial: not supported, not esm (esm eol is past) -> eol
        assert catalog.get("xenial").status == "eol"
        assert catalog.get("bionic").status == "esm"
        assert catalog.get("jammy").status == "supported"
        assert catalog.get("resolute").status == "supported"
        assert catalog.get("stonking").status == "devel"

    def test_lts_detection(self, catalog):
        assert catalog.get("resolute").is_lts is True
        assert catalog.get("stonking").is_lts is False

    def test_dates_from_metadata(self, catalog):
        resolute = catalog.get("resolute")
        assert resolute.released == "2026-04-23"
        assert resolute.eol_esm == "2036-04-23"

    def test_missing_metadata_leaves_dates_none(self, catalog):
        # jammy has no metadata row in the sample.
        jammy = catalog.get("jammy")
        assert jammy.version == ""
        assert jammy.released is None
        assert jammy.is_lts is False

    def test_empty_metadata_is_optional(self):
        catalog = ReleaseCatalog.from_data(
            CODENAMES, SUPPORTED, SUPPORTED_ESM, DEVEL
        )
        assert catalog.get("resolute").version == ""
        assert catalog.get("stonking").status == "devel"


class TestLookups:
    def test_known(self, catalog):
        assert catalog.known("noble") is True
        assert catalog.known("warty") is False

    def test_order_of_unknown_is_none(self, catalog):
        assert catalog.order_of("warty") is None

    def test_between_is_exclusive(self, catalog):
        series = [r.series for r in catalog.between(0, 6)]
        assert series == ["bionic", "focal", "jammy", "noble", "questing"]

    def test_newer_than(self, catalog):
        assert [r.series for r in catalog.newer_than(6)] == ["stonking"]

    def test_relevant_excludes_eol(self, catalog):
        relevant = [r.series for r in catalog.relevant()]
        assert "xenial" not in relevant  # eol
        assert "questing" not in relevant  # eol
        assert relevant == [
            "bionic",
            "focal",
            "jammy",
            "noble",
            "resolute",
            "stonking",
        ]


class TestLoadCsvMetadata:
    def test_reads_and_keys_by_series(self, tmp_path):
        csv_file = tmp_path / "ubuntu.csv"
        csv_file.write_text(
            "version,codename,series,created,release,eol,"
            "eol-server,eol-esm\n"
            "26.04 LTS,Resolute Raccoon,resolute,2025-10-09,"
            "2026-04-23,2031-05-29,2031-05-29,2036-04-23\n"
        )
        metadata = load_csv_metadata(str(csv_file))
        assert set(metadata) == {"resolute"}
        assert metadata["resolute"]["version"] == "26.04 LTS"
        assert metadata["resolute"]["eol-esm"] == "2036-04-23"

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_csv_metadata(str(tmp_path / "nope.csv")) == {}


class TestFromDistroInfo:
    def test_wires_distro_info_queries(self, monkeypatch):
        calls = []
        responses = {
            ("--all", "-c"): CODENAMES,
            ("--supported",): SUPPORTED,
            ("--supported-esm",): SUPPORTED_ESM,
            ("--devel",): DEVEL,
        }

        def fake_run(args):
            calls.append(tuple(args))
            return list(responses[tuple(args)])

        monkeypatch.setattr(release_catalog, "run_distro_info", fake_run)
        monkeypatch.setattr(
            release_catalog, "load_csv_metadata", lambda path: METADATA
        )

        catalog = ReleaseCatalog.from_distro_info()

        assert ("--all", "-c") in calls
        assert ("--supported-esm",) in calls
        assert [r.series for r in catalog.ordered] == CODENAMES
        assert catalog.get("stonking").status == "devel"


class TestStatusProperty:
    def test_priority_ordering(self):
        # A devel release is also reported as supported by distro-info;
        # devel must win.
        release = Release(
            "x", 0, supported=True, supported_esm=True, devel=True
        )
        assert release.status == "devel"

    def test_esm_only(self):
        assert Release("x", 0, supported_esm=True).status == "esm"

    def test_eol_when_no_flags(self):
        assert Release("x", 0).status == "eol"


@pytest.mark.skipif(
    shutil.which("distro-info") is None,
    reason="distro-info is not installed",
)
class TestIntegrationRealDistroInfo:
    """Exercises the real ``distro-info`` binary end to end.

    Assertions are intentionally date- and machine-independent so the
    test stays stable as releases come and go.
    """

    @pytest.fixture(scope="class")
    def catalog(self):
        return ReleaseCatalog.from_distro_info()

    def test_catalog_is_non_empty(self, catalog):
        assert catalog.ordered

    def test_well_known_releases_present_and_ordered(self, catalog):
        for series in ("xenial", "bionic", "focal", "jammy", "noble"):
            assert catalog.known(series)
        # Ordering is chronological.
        assert (
            catalog.order_of("xenial")
            < catalog.order_of("bionic")
            < catalog.order_of("focal")
        )

    def test_lts_detection_against_real_data(self, catalog):
        assert catalog.get("bionic").is_lts is True

    def test_devel_is_a_subset_of_supported(self, catalog):
        for release in catalog.ordered:
            if release.devel:
                assert release.supported

    def test_has_at_least_one_supported_release(self, catalog):
        assert any(r.status == "supported" for r in catalog.ordered)

    def test_metadata_is_populated_when_csv_present(self, catalog):
        # If the CSV database exists, at least one release should carry a
        # version string parsed from it.
        if os.path.exists(release_catalog.UBUNTU_CSV):
            assert any(r.version for r in catalog.ordered)
