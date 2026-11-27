import pytest

from features.machine_types import MachineType
from features.tools.targets import (
    ApplicabilityDataError,
    TargetApplicability,
    UnknownMachineTypeError,
    UnknownReleaseError,
)

# "skips-focal" is offered on the releases either side of focal, but not on
# focal itself.
OFFERED = {
    "all-lts": ["bionic", "focal", "jammy", "noble"],
    "skips-focal": ["bionic", "jammy", "noble"],
    "newest-only": ["noble", "oracular"],
}


@pytest.fixture
def data():
    return TargetApplicability(OFFERED)


@pytest.fixture(scope="module")
def real_data():
    return TargetApplicability.from_file()


class TestIsApplicable:
    @pytest.mark.parametrize(
        "release,machine_type,expected",
        (
            ("focal", "all-lts", True),
            ("focal", "skips-focal", False),
            ("noble", "skips-focal", True),
            ("bionic", "newest-only", False),
            ("oracular", "newest-only", True),
            ("oracular", "all-lts", False),
        ),
    )
    def test_known_pair(self, data, release, machine_type, expected):
        assert expected == data.is_applicable(release, machine_type)

    def test_unknown_machine_type_raises(self, data):
        with pytest.raises(UnknownMachineTypeError, match="unlisted"):
            data.is_applicable("jammy", "unlisted")

    def test_unknown_release_raises(self, data):
        with pytest.raises(UnknownReleaseError, match="warty"):
            data.is_applicable("warty", "skips-focal")

    def test_unknown_machine_type_reported_before_unknown_release(self, data):
        with pytest.raises(UnknownMachineTypeError):
            data.is_applicable("warty", "unlisted")


class TestOfferedData:
    def test_offered_releases(self, data):
        assert frozenset(["noble", "oracular"]) == data.offered_releases(
            "newest-only"
        )

    def test_offered_releases_of_unknown_machine_type_raises(self, data):
        with pytest.raises(UnknownMachineTypeError, match="unlisted"):
            data.offered_releases("unlisted")

    def test_machine_types(self, data):
        assert (
            frozenset(["all-lts", "skips-focal", "newest-only"])
            == data.machine_types
        )

    def test_releases_are_those_of_any_machine_type(self, data):
        assert (
            frozenset(["bionic", "focal", "jammy", "noble", "oracular"])
            == data.releases
        )


class TestValidation:
    @pytest.mark.parametrize(
        "raw,message",
        (
            pytest.param({}, "no machine types", id="empty"),
            pytest.param({"wsl": []}, "non-empty list", id="empty-list"),
            pytest.param({"wsl": "jammy"}, "non-empty list", id="string"),
            pytest.param({"wsl": None}, "non-empty list", id="none"),
            pytest.param({"wsl": ("jammy",)}, "non-empty list", id="tuple"),
            pytest.param(
                {"wsl": ["jammy", "jammy"]}, "duplicate release", id="dup"
            ),
            pytest.param(
                {"wsl": ["Jammy"]}, "invalid release name", id="capitalised"
            ),
            pytest.param(
                {"wsl": ["jammy-2"]}, "invalid release name", id="digit"
            ),
            pytest.param({"wsl": [""]}, "invalid release name", id="blank"),
            pytest.param(
                {"wsl": [22]}, "invalid release name", id="non-string-release"
            ),
            pytest.param(
                {"Wsl": ["jammy"]}, "invalid machine type", id="uppercase"
            ),
            pytest.param(
                {"a..b": ["jammy"]}, "invalid machine type", id="double-dot"
            ),
            pytest.param(
                {"-a": ["jammy"]}, "invalid machine type", id="leading-dash"
            ),
            pytest.param(
                {"": ["jammy"]}, "invalid machine type", id="blank-name"
            ),
            pytest.param(
                {1: ["jammy"]}, "invalid machine type", id="non-string-name"
            ),
        ),
    )
    def test_malformed_data_rejected(self, raw, message):
        with pytest.raises(ApplicabilityDataError, match=message):
            TargetApplicability(raw)

    def test_dotted_and_dashed_machine_types_accepted(self):
        data = TargetApplicability(
            {"aws.pro-fips": ["jammy"], "lxd-vm": ["noble"]}
        )
        assert frozenset(["aws.pro-fips", "lxd-vm"]) == data.machine_types


class TestFromFile:
    def test_valid_file(self, tmpdir):
        path = tmpdir.join("targets.yaml")
        path.write("wsl:\n  - jammy\n  - noble\n")
        data = TargetApplicability.from_file(str(path))
        assert frozenset(["jammy", "noble"]) == data.offered_releases("wsl")

    @pytest.mark.parametrize(
        "content",
        (
            pytest.param("- jammy\n", id="list"),
            pytest.param("", id="empty-file"),
            pytest.param("wsl: [a\n", id="invalid-yaml"),
        ),
    )
    def test_malformed_file_rejected(self, content, tmpdir):
        path = tmpdir.join("targets.yaml")
        path.write(content)
        with pytest.raises(ApplicabilityDataError, match="targets.yaml"):
            TargetApplicability.from_file(str(path))

    def test_invalid_entry_in_file_rejected(self, tmpdir):
        path = tmpdir.join("targets.yaml")
        path.write("wsl: jammy\n")
        with pytest.raises(ApplicabilityDataError, match="non-empty list"):
            TargetApplicability.from_file(str(path))

    def test_missing_file_rejected(self, tmpdir):
        path = str(tmpdir.join("nope.yaml"))
        with pytest.raises(ApplicabilityDataError, match="nope.yaml"):
            TargetApplicability.from_file(path)


class TestRepositoryData:
    def test_machine_types_match_enum(self, real_data):
        assert {m.value for m in MachineType} == real_data.machine_types

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
    def test_current_pairs(self, real_data, release, machine_type, expected):
        assert expected == real_data.is_applicable(release, machine_type)
