"""Load and query which releases each machine type is offered on.
"""

import os
import re
from typing import Any, Dict, FrozenSet, Mapping, Optional, Set  # noqa: F401

import yaml

DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "targets.yaml",
)

_MACHINE_TYPE_RE = re.compile(r"^[a-z0-9]+([.-][a-z0-9]+)*$")
_RELEASE_RE = re.compile(r"^[a-z]+$")


class ApplicabilityDataError(ValueError):
    """Raised when targets.yaml cannot be read or has an invalid entry."""


class UnknownMachineTypeError(KeyError):
    """Raised when a machine type is not a key in targets.yaml."""


class UnknownReleaseError(KeyError):
    """Raised when no machine type in targets.yaml lists the release."""


class TargetApplicability:
    """Which releases each machine type is offered on."""

    def __init__(self, offered: Mapping[str, Any]) -> None:
        self._offered = _validate(offered)  # type: Dict[str, FrozenSet[str]]
        releases = set()  # type: Set[str]
        for machine_releases in self._offered.values():
            releases.update(machine_releases)
        self._releases = frozenset(releases)

    @classmethod
    def from_file(cls, path: Optional[str] = None) -> "TargetApplicability":
        path = path or DEFAULT_DATA_PATH
        try:
            with open(path, encoding="utf-8") as stream:
                raw = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError) as e:
            raise ApplicabilityDataError("cannot read {}: {}".format(path, e))
        if not isinstance(raw, dict):
            raise ApplicabilityDataError(
                "{}: expected a mapping of machine type to releases".format(
                    path
                )
            )
        return cls(raw)

    @property
    def machine_types(self) -> FrozenSet[str]:
        return frozenset(self._offered)

    @property
    def releases(self) -> FrozenSet[str]:
        """Every release offered by at least one machine type."""
        return self._releases

    def offered_releases(self, machine_type: str) -> FrozenSet[str]:
        try:
            return self._offered[machine_type]
        except KeyError:
            raise UnknownMachineTypeError(machine_type)

    def is_applicable(self, release: str, machine_type: str) -> bool:
        """Return whether the release is offered on the machine type.

        A release that some other machine type lists, but this one does not,
        returns False. A machine type or release that no entry lists raises.
        """
        offered = self.offered_releases(machine_type)
        if release not in self._releases:
            raise UnknownReleaseError(release)
        return release in offered


def _validate(offered: Mapping[str, Any]) -> Dict[str, FrozenSet[str]]:
    if not offered:
        raise ApplicabilityDataError("no machine types are defined")
    validated = {}  # type: Dict[str, FrozenSet[str]]
    for machine_type, releases in offered.items():
        if not isinstance(machine_type, str) or not _MACHINE_TYPE_RE.match(
            machine_type
        ):
            raise ApplicabilityDataError(
                "invalid machine type name: {!r}".format(machine_type)
            )
        if not isinstance(releases, list) or not releases:
            raise ApplicabilityDataError(
                "{}: expected a non-empty list of releases".format(
                    machine_type
                )
            )
        seen = set()  # type: Set[str]
        for release in releases:
            if not isinstance(release, str) or not _RELEASE_RE.match(release):
                raise ApplicabilityDataError(
                    "{}: invalid release name: {!r}".format(
                        machine_type, release
                    )
                )
            if release in seen:
                raise ApplicabilityDataError(
                    "{}: duplicate release: {}".format(machine_type, release)
                )
            seen.add(release)
        validated[machine_type] = frozenset(seen)
    return validated
