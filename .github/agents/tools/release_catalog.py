#!/usr/bin/env python3
"""Tool 1: authoritative Ubuntu release catalog, backed by ``distro-info``.

This tool answers a single question for the rest of the feature-test
maintenance workflow: *what are the Ubuntu releases, in order, and what is
each release's support status right now?* It is the source of truth that
the coverage extractor (Tool 2) and the agent layer reason against.

Everything is derived from ``distro-info`` (the Ubuntu release database):

* chronological ordering and release membership -> ``distro-info --all -c``
* standard support (incl. devel)                -> ``distro-info --supported``
* ESM-supported stable releases                 -> ``--supported-esm``
* the current development release                -> ``distro-info --devel``
* per-release metadata (version, dates, LTS)     -> ``ubuntu.csv`` database

The I/O (subprocess + CSV read) is deliberately separated from the pure
catalog construction (:meth:`ReleaseCatalog.from_data`) so the logic is
testable without ``distro-info`` installed.

Usage::

    python3 tools/release_catalog.py            # human-readable table
    python3 tools/release_catalog.py --format json
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence

DISTRO_INFO = "distro-info"
UBUNTU_CSV = "/usr/share/distro-info/ubuntu.csv"

#: Statuses that count as "currently relevant" for gap analysis.
RELEVANT_STATUSES = ("devel", "supported", "esm")


@dataclass
class Release:
    series: str
    order: int
    version: str = ""
    is_lts: bool = False
    created: Optional[str] = None
    released: Optional[str] = None
    eol: Optional[str] = None
    eol_esm: Optional[str] = None
    supported: bool = False  # standard support (distro-info includes devel)
    supported_esm: bool = False
    devel: bool = False

    @property
    def status(self) -> str:
        """Coarse support status: devel > supported > esm > eol."""
        if self.devel:
            return "devel"
        if self.supported:
            return "supported"
        if self.supported_esm:
            return "esm"
        return "eol"

    @property
    def is_relevant(self) -> bool:
        return self.status in RELEVANT_STATUSES


class ReleaseCatalog:
    """An ordered, queryable collection of :class:`Release` records."""

    def __init__(self, releases: Sequence[Release]) -> None:
        self.ordered: List[Release] = sorted(releases, key=lambda r: r.order)
        self._by_series: Dict[str, Release] = {r.series: r for r in releases}

    # -- lookups ----------------------------------------------------------
    def get(self, series: str) -> Optional[Release]:
        return self._by_series.get(series)

    def known(self, series: str) -> bool:
        return series in self._by_series

    def order_of(self, series: str) -> Optional[int]:
        release = self._by_series.get(series)
        return release.order if release else None

    def between(self, low: int, high: int) -> List[Release]:
        """Releases with ``low < order < high`` (exclusive on both ends)."""
        return [r for r in self.ordered if low < r.order < high]

    def newer_than(self, order: int) -> List[Release]:
        return [r for r in self.ordered if r.order > order]

    def relevant(self) -> List[Release]:
        return [r for r in self.ordered if r.is_relevant]

    # -- constructors -----------------------------------------------------
    @classmethod
    def from_data(
        cls,
        codenames: Sequence[str],
        supported: Sequence[str],
        supported_esm: Sequence[str],
        devel: Sequence[str],
        metadata: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> "ReleaseCatalog":
        """Build a catalog from already-gathered ``distro-info`` data.

        ``codenames`` must be in chronological (oldest-first) order, as
        produced by ``distro-info --all -c``; that order is the catalog's
        canonical ordering. ``metadata`` maps a series codename to a row
        of the ``ubuntu.csv`` database.
        """
        metadata = metadata or {}
        supported_set = set(supported)
        esm_set = set(supported_esm)
        devel_set = set(devel)

        releases: List[Release] = []
        for order, series in enumerate(codenames):
            row = metadata.get(series, {})
            version = row.get("version", "")
            releases.append(
                Release(
                    series=series,
                    order=order,
                    version=version,
                    is_lts="LTS" in version,
                    created=row.get("created") or None,
                    released=row.get("release") or None,
                    eol=row.get("eol") or None,
                    eol_esm=row.get("eol-esm") or None,
                    supported=series in supported_set,
                    supported_esm=series in esm_set,
                    devel=series in devel_set,
                )
            )
        return cls(releases)

    @classmethod
    def from_distro_info(cls, csv_path: str = UBUNTU_CSV) -> "ReleaseCatalog":
        """Build a catalog by querying the ``distro-info`` binary."""
        return cls.from_data(
            codenames=run_distro_info(["--all", "-c"]),
            supported=run_distro_info(["--supported"]),
            supported_esm=run_distro_info(["--supported-esm"]),
            devel=run_distro_info(["--devel"]),
            metadata=load_csv_metadata(csv_path),
        )


# ---------------------------------------------------------------------------
# I/O helpers (kept thin and separate from the pure catalog logic)
# ---------------------------------------------------------------------------
def run_distro_info(args: List[str]) -> List[str]:
    """Return the non-empty output lines of ``distro-info <args>``."""
    try:
        output = subprocess.check_output(
            [DISTRO_INFO] + args, stderr=subprocess.STDOUT
        )
    except FileNotFoundError:
        raise SystemExit(
            "error: `distro-info` not found. Install the `distro-info` "
            "package (it ships the authoritative Ubuntu release database)."
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "error: `distro-info {}` failed:\n{}".format(
                " ".join(args), exc.output.decode("utf-8", "replace")
            )
        )
    lines = output.decode("utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def load_csv_metadata(csv_path: str) -> Dict[str, Dict[str, str]]:
    """Read the ``distro-info`` CSV database, keyed by series codename.

    Returns an empty mapping if the file is unavailable, so the catalog
    still builds (without version/date metadata) from the binary alone.
    """
    if not os.path.exists(csv_path):
        return {}
    metadata: Dict[str, Dict[str, str]] = {}
    with open(csv_path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            series = row.get("series")
            if series:
                metadata[series] = row
    return metadata


# ---------------------------------------------------------------------------
# Reporting / CLI
# ---------------------------------------------------------------------------
def render_table(catalog: ReleaseCatalog) -> str:
    header = "{:<10} {:<10} {:<10} {:<4} {:<12} {:<12}".format(
        "series", "version", "status", "lts", "release", "eol"
    )
    lines = [header, "-" * len(header)]
    for release in catalog.ordered:
        lines.append(
            "{:<10} {:<10} {:<10} {:<4} {:<12} {:<12}".format(
                release.series,
                release.version or "-",
                release.status,
                "yes" if release.is_lts else "-",
                release.released or "-",
                release.eol or "-",
            )
        )
    return "\n".join(lines)


def render_json(catalog: ReleaseCatalog) -> str:
    return json.dumps(
        [asdict(r) for r in catalog.ordered], indent=2, sort_keys=True
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="output format (default: table)",
    )
    parser.add_argument(
        "--csv-path",
        default=UBUNTU_CSV,
        help="path to the distro-info ubuntu.csv database",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    catalog = ReleaseCatalog.from_distro_info(args.csv_path)
    if args.format == "json":
        print(render_json(catalog))
    else:
        print(render_table(catalog))
    return 0


if __name__ == "__main__":
    sys.exit(main())
