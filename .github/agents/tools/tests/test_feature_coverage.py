import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from feature_coverage import (  # noqa: E402
    ExampleTable,
    ScenarioSummary,
    discover_feature_files,
    parse_feature,
    parse_features,
    render_json,
    render_table,
)


def _write(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(textwrap.dedent(body).lstrip("\n"))
    return str(path)


OUTLINE_FEATURE = """
    @contract
    Feature: sample

      @wip
      Scenario Outline: does a thing
        Given a `<release>` `<machine_type>` machine
        Then it works

        Examples: ubuntu release
          | release | machine_type  |
          | xenial  | lxd-container |
          | xenial  | lxd-vm        |
          | jammy   | lxd-container |
    """

MULTI_EXAMPLES_FEATURE = """
    Feature: multi

      Scenario Outline: two blocks
        Given a `<release>` `<machine_type>` machine

        Examples: containers
          | release | machine_type  |
          | jammy   | lxd-container |

        Examples: vms
          | release | machine_type |
          | xenial  | lxd-vm       |
    """

LITERAL_FEATURE = """
    Feature: literal

      Scenario: fixed release
        Given a `xenial` `lxd-vm` machine with pro installed
        Then it works
    """

NON_MATRIX_FEATURE = """
    Feature: nonmatrix

      Scenario Outline: custom columns
        Given something with <param>

        Examples:
          | param |
          | a     |
          | b     |
    """


class TestParseFeature:
    def test_extracts_outline_coverage(self, tmp_path):
        path = _write(tmp_path, "outline.feature", OUTLINE_FEATURE)
        summaries = parse_feature(path)
        assert len(summaries) == 1
        summary = summaries[0]
        assert summary.is_outline
        assert summary.name == "does a thing"
        assert summary.coverage() == {
            ("xenial", "lxd-container"),
            ("xenial", "lxd-vm"),
            ("jammy", "lxd-container"),
        }

    def test_inherits_feature_and_scenario_tags(self, tmp_path):
        path = _write(tmp_path, "outline.feature", OUTLINE_FEATURE)
        summary = parse_feature(path)[0]
        assert summary.tags == ["contract", "wip"]

    def test_records_line_numbers(self, tmp_path):
        path = _write(tmp_path, "outline.feature", OUTLINE_FEATURE)
        summary = parse_feature(path)[0]
        assert summary.line == 5  # "Scenario Outline:" line (not the tag)
        assert summary.examples[0].name == "ubuntu release"
        assert summary.examples[0].headings == [
            "release",
            "machine_type",
        ]

    def test_ordered_coverage_preserves_file_order(self, tmp_path):
        path = _write(tmp_path, "outline.feature", OUTLINE_FEATURE)
        summary = parse_feature(path)[0]
        assert summary.ordered_coverage() == [
            ("xenial", "lxd-container"),
            ("xenial", "lxd-vm"),
            ("jammy", "lxd-container"),
        ]

    def test_multiple_examples_blocks(self, tmp_path):
        path = _write(tmp_path, "multi.feature", MULTI_EXAMPLES_FEATURE)
        summary = parse_feature(path)[0]
        assert len(summary.examples) == 2
        assert summary.coverage() == {
            ("jammy", "lxd-container"),
            ("xenial", "lxd-vm"),
        }

    def test_plain_scenario_has_no_coverage(self, tmp_path):
        # Plain scenarios have no Examples matrix, so they contribute no
        # coverage. (The suite converts single-machine tests to one-row
        # Scenario Outlines instead of hardcoding the machine.)
        path = _write(tmp_path, "literal.feature", LITERAL_FEATURE)
        summary = parse_feature(path)[0]
        assert summary.is_outline is False
        assert summary.examples == []
        assert summary.coverage() == set()

    def test_non_matrix_columns_yield_no_coverage(self, tmp_path):
        path = _write(tmp_path, "nonmatrix.feature", NON_MATRIX_FEATURE)
        summary = parse_feature(path)[0]
        assert summary.examples[0].headings == ["param"]
        assert summary.coverage() == set()


class TestDiscovery:
    def test_expands_dirs_and_dedupes(self, tmp_path):
        (tmp_path / "sub").mkdir()
        a = _write(tmp_path, "a.feature", OUTLINE_FEATURE)
        b = _write(tmp_path / "sub", "b.feature", LITERAL_FEATURE)
        (tmp_path / "ignore.txt").write_text("nope")
        found = discover_feature_files([str(tmp_path), a])
        assert found == sorted({a, b})

    def test_parse_features_over_directory(self, tmp_path):
        _write(tmp_path, "a.feature", OUTLINE_FEATURE)
        _write(tmp_path, "b.feature", LITERAL_FEATURE)
        summaries = parse_features([str(tmp_path)])
        names = {s.name for s in summaries}
        assert names == {"does a thing", "fixed release"}


class TestRendering:
    def _summary(self):
        return ScenarioSummary(
            feature_file="f.feature",
            feature_name="F",
            name="does a thing",
            line=4,
            is_outline=True,
            tags=["contract", "wip"],
            examples=[
                ExampleTable(
                    name="ubuntu release",
                    line=8,
                    headings=["release", "machine_type"],
                    rows=[
                        {"release": "xenial", "machine_type": "lxd-container"},
                        {"release": "xenial", "machine_type": "lxd-vm"},
                        {"release": "jammy", "machine_type": "lxd-container"},
                    ],
                )
            ],
        )

    def test_table_groups_by_release(self):
        out = render_table([self._summary()])
        assert "does a thing" in out
        assert "@contract @wip" in out
        assert "xenial" in out
        assert "lxd-container, lxd-vm" in out

    def test_json_includes_flattened_coverage(self):
        import json

        payload = json.loads(render_json([self._summary()]))
        assert payload[0]["coverage"] == [
            "jammy:lxd-container",
            "xenial:lxd-container",
            "xenial:lxd-vm",
        ]


class TestIntegrationRealFeatures:
    """Parses a real feature file from the repo, if present."""

    REAL = os.path.join("features", "cli", "status.feature")

    @pytest.mark.skipif(
        not os.path.exists(REAL), reason="real feature file not found"
    )
    def test_real_status_feature(self):
        summaries = parse_feature(self.REAL)
        assert summaries
        outlines = [s for s in summaries if s.is_outline]
        assert outlines
        # Every outline row should resolve to a release+machine_type pair.
        all_cells = set()
        for summary in outlines:
            all_cells |= summary.coverage()
        releases = {release for release, _mt in all_cells}
        assert "xenial" in releases
