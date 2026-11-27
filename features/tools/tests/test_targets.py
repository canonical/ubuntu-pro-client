import pytest

from features.tools.targets import (
    ApplicabilityDataError,
    TargetApplicability,
    UnknownMachineTypeError,
    UnknownReleaseError,
)

# Neither machine type is offered on a contiguous run of releases.
DISCONTINUOUS = {
    "alpha": ["bionic", "jammy", "noble"],
    "beta": ["jammy", "noble", "oracular"],
}


class TestQuery:
    @pytest.mark.parametrize(
        "release,machine_type,expected",
        (
            ("bionic", "alpha", True),
            ("jammy", "alpha", True),
            ("oracular", "alpha", False),
            ("bionic", "beta", False),
            ("oracular", "beta", True),
        ),
    )
    def test_known_pair(self, release, machine_type, expected):
        data = TargetApplicability(DISCONTINUOUS)
        assert expected is data.is_applicable(release, machine_type)

    def test_gap_in_availability(self):
        data = TargetApplicability(
            {"alpha": ["bionic", "noble"], "beta": ["jammy"]}
        )
        assert not data.is_applicable("jammy", "alpha")
        assert data.is_applicable("noble", "alpha")

    def test_unknown_machine_type_raises(self):
        data = TargetApplicability(DISCONTINUOUS)
        with pytest.raises(UnknownMachineTypeError):
            data.is_applicable("jammy", "gamma")

    def test_unknown_release_raises(self):
        data = TargetApplicability(DISCONTINUOUS)
        with pytest.raises(UnknownReleaseError):
            data.is_applicable("warty", "alpha")

    def test_known_sets(self):
        data = TargetApplicability(DISCONTINUOUS)
        assert frozenset(["alpha", "beta"]) == data.machine_types
        assert (
            frozenset(["bionic", "jammy", "noble", "oracular"])
            == data.releases
        )


class TestValidation:
    @pytest.mark.parametrize(
        "raw",
        (
            {},
            {"alpha": []},
            {"alpha": "jammy"},
            {"alpha": None},
            {"alpha": ["jammy", "jammy"]},
            {"alpha": ["Jammy"]},
            {"alpha": [22]},
            {"Alpha": ["jammy"]},
            {1: ["jammy"]},
        ),
    )
    def test_malformed_data_rejected(self, raw):
        with pytest.raises(ApplicabilityDataError):
            TargetApplicability(raw)

    @pytest.mark.parametrize("content", ("- jammy\n", "", "alpha: [a\n"))
    def test_malformed_file_rejected(self, content, tmpdir):
        path = tmpdir.join("targets.yaml")
        path.write(content)
        with pytest.raises(ApplicabilityDataError):
            TargetApplicability.from_file(str(path))

    def test_missing_file_rejected(self, tmpdir):
        with pytest.raises(ApplicabilityDataError):
            TargetApplicability.from_file(str(tmpdir.join("nope.yaml")))


class TestRepositoryData:
    def test_current_machine_types(self):
        data = TargetApplicability.from_file()
        assert (
            frozenset(
                [
                    "lxd-container",
                    "lxd-vm",
                    "aws.generic",
                    "aws.pro",
                    "aws.pro-fips",
                    "azure.generic",
                    "azure.pro",
                    "azure.pro-fips",
                    "gcp.generic",
                    "gcp.pro",
                    "gcp.pro-fips",
                    "wsl",
                ]
            )
            == data.machine_types
        )

    @pytest.mark.parametrize(
        "release,machine_type,expected",
        (
            ("noble", "lxd-vm", True),
            ("resolute", "aws.pro-fips", False),
            ("focal", "aws.pro-fips", True),
            ("jammy", "gcp.pro-fips", True),
            ("questing", "lxd-vm", True),
            ("questing", "aws.pro", False),
            ("bionic", "wsl", False),
            ("noble", "wsl", True),
            ("jammy", "wsl", True),
        ),
    )
    def test_current_pairs(self, release, machine_type, expected):
        data = TargetApplicability.from_file()
        assert expected is data.is_applicable(release, machine_type)
