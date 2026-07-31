#!/usr/bin/env python3
"""Tool 2: summarise the ``behave`` Examples coverage of feature tests.

Where Tool 1 (:mod:`release_catalog`) answers "what releases exist?", this
tool answers "what does each scenario actually run against?". It reads the
``*.feature`` files and, for every ``Scenario Outline``, extracts the
``Examples`` tables -- primarily the ``release`` x ``machine_type`` matrix
-- into a normalized, structured summary.

Parsing is delegated entirely to ``behave.parser`` (a development
dependency, see ``requirements.test.txt``). We do **not** hand-roll a
Gherkin parser and we do **not** run behave: ``parse_file`` only reads the
grammar, so there is no ``environment.py`` import, no step matching and no
scenario-outline expansion to unwind.

Usage (from the repo root)::

    python3 .github/agents/tools/feature_coverage.py features/lxd.feature
    python3 .github/agents/tools/feature_coverage.py --format json features/
"""

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from behave.model import ScenarioOutline
from behave.parser import parse_file


@dataclass
class ExampleTable:
    name: str
    line: int
    headings: List[str]
    rows: List[Dict[str, str]]

    @property
    def has_matrix_columns(self) -> bool:
        return "release" in self.headings and "machine_type" in self.headings


@dataclass
class ScenarioSummary:
    feature_file: str
    feature_name: str
    name: str
    line: int
    is_outline: bool
    tags: List[str] = field(default_factory=list)
    examples: List[ExampleTable] = field(default_factory=list)

    def ordered_coverage(self) -> List[Tuple[str, str]]:
        """(release, machine_type) pairs in file (appearance) order."""
        seen: Set[Tuple[str, str]] = set()
        ordered: List[Tuple[str, str]] = []
        for table in self.examples:
            if not table.has_matrix_columns:
                continue
            for row in table.rows:
                pair = (row.get("release"), row.get("machine_type"))
                if all(pair) and pair not in seen:
                    seen.add(pair)
                    ordered.append(pair)  # type: ignore[arg-type]
        return ordered

    def coverage(self) -> Set[Tuple[str, str]]:
        return set(self.ordered_coverage())


# ---------------------------------------------------------------------------
# Extraction (delegated to behave.parser)
# ---------------------------------------------------------------------------
def parse_feature(path: str) -> List[ScenarioSummary]:
    """Parse a single ``.feature`` file into scenario summaries."""
    feature = parse_file(path)
    if feature is None:
        return []

    feature_tags = [str(tag) for tag in feature.tags]
    summaries: List[ScenarioSummary] = []
    for scenario in feature.scenarios:
        is_outline = isinstance(scenario, ScenarioOutline)
        summaries.append(
            ScenarioSummary(
                feature_file=path,
                feature_name=feature.name or "",
                name=scenario.name or "",
                line=scenario.line,
                is_outline=is_outline,
                tags=feature_tags + [str(tag) for tag in scenario.tags],
                examples=_extract_examples(scenario),
            )
        )
    return summaries


def _extract_examples(scenario) -> List[ExampleTable]:
    tables: List[ExampleTable] = []
    for example in getattr(scenario, "examples", None) or []:
        table = example.table
        if table is None:
            continue
        headings = list(table.headings)
        rows = [
            dict(zip(headings, [str(cell) for cell in row.cells]))
            for row in table.rows
        ]
        tables.append(
            ExampleTable(
                name=example.name or "",
                line=example.line,
                headings=headings,
                rows=rows,
            )
        )
    return tables


def discover_feature_files(paths: Sequence[str]) -> List[str]:
    """Expand a mix of files and directories into a sorted file list."""
    found: List[str] = []
    for path in paths:
        if os.path.isdir(path):
            for root, _dirs, names in os.walk(path):
                for name in names:
                    if name.endswith(".feature"):
                        found.append(os.path.join(root, name))
        elif path.endswith(".feature"):
            found.append(path)
    return sorted(set(found))


def parse_features(paths: Sequence[str]) -> List[ScenarioSummary]:
    summaries: List[ScenarioSummary] = []
    for path in discover_feature_files(paths):
        summaries.extend(parse_feature(path))
    return summaries


# ---------------------------------------------------------------------------
# Reporting / CLI
# ---------------------------------------------------------------------------
def _group_by_release(
    coverage: Sequence[Tuple[str, str]]
) -> "List[Tuple[str, List[str]]]":
    grouped: Dict[str, List[str]] = {}
    order: List[str] = []
    for release, machine_type in coverage:
        if release not in grouped:
            grouped[release] = []
            order.append(release)
        if machine_type not in grouped[release]:
            grouped[release].append(machine_type)
    return [(release, grouped[release]) for release in order]


def render_table(summaries: Sequence[ScenarioSummary]) -> str:
    lines: List[str] = []
    current_file: Optional[str] = None
    for summary in summaries:
        if summary.feature_file != current_file:
            current_file = summary.feature_file
            lines.append("")
            lines.append(current_file)
        kind = "outline" if summary.is_outline else "scenario"
        lines.append(
            "  L{:<5} [{}] {}".format(summary.line, kind, summary.name)
        )
        if summary.tags:
            lines.append(
                "         tags: " + " ".join("@" + tag for tag in summary.tags)
            )
        coverage = _group_by_release(summary.ordered_coverage())
        if not coverage:
            lines.append("         (no release/machine_type examples)")
            continue
        for release, machine_types in coverage:
            lines.append(
                "         {:<10} {}".format(release, ", ".join(machine_types))
            )
    return "\n".join(lines).lstrip("\n")


def render_json(summaries: Sequence[ScenarioSummary]) -> str:
    payload = []
    for summary in summaries:
        data = asdict(summary)
        data["coverage"] = sorted(
            "{}:{}".format(release, machine_type)
            for release, machine_type in summary.coverage()
        )
        payload.append(data)
    return json.dumps(payload, indent=2, sort_keys=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["features"],
        help="feature files or directories (default: features)",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="output format (default: table)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    summaries = parse_features(args.paths)
    if args.format == "json":
        print(render_json(summaries))
    else:
        print(render_table(summaries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
