"""
Client version related functions
"""
import os.path
from math import inf
from typing import Optional

from uaclient.apt import (
    get_apt_cache_time,
    get_pkg_candidate_version,
    version_compare,
)
from uaclient.defaults import CANDIDATE_CACHE_PATH, UAC_RUN_PATH
from uaclient.exceptions import ProcessExecutionError
from uaclient.system import subp

__VERSION__ = "29.4"
PACKAGED_VERSION = "@@PACKAGED_VERSION@@"


def get_version() -> str:
    """Return the packaged version as a string

    Prefer the binary PACKAGED_VESION set by debian/rules to DEB_VERSION.
    If unavailable, check for a .git development environments:
      a. If run in our upstream repo `git describe` will gives a leading
         XX.Y so return the --long version to allow daily build recipes
         to count commit offset from upstream's XX.Y signed tag.
      b. If run in a git-ubuntu pkg repo, upstream tags aren't visible,
         believe __VERSION__ is correct - there is and MUST always be a
         test to make sure it matches debian/changelog
    """
    if not PACKAGED_VERSION.startswith("@@PACKAGED_VERSION"):
        return PACKAGED_VERSION
    topdir = os.path.dirname(os.path.dirname(__file__))
    if os.path.exists(os.path.join(topdir, ".git")):
        cmd = ["git", "describe", "--abbrev=8", "--match=[0-9]*", "--long"]
        try:
            out, _ = subp(cmd)
            return out.strip()
        except ProcessExecutionError:
            pass
    return __VERSION__


def get_last_known_candidate() -> Optional[str]:
    # If we can't determine when the cache was updated for the last time,
    # We always assume it was as recent as possible - thus `inf`.
    last_apt_cache_update = get_apt_cache_time() or inf
    if (
        not os.path.exists(CANDIDATE_CACHE_PATH)
        or os.stat(CANDIDATE_CACHE_PATH).st_mtime < last_apt_cache_update
    ):
        try:
            candidate_version = get_pkg_candidate_version(
                "ubuntu-advantage-tools"
            )
            if candidate_version:
                os.makedirs(UAC_RUN_PATH, exist_ok=True)
                with open(CANDIDATE_CACHE_PATH, "w") as f:
                    f.write(candidate_version)
                return candidate_version
        except Exception:
            if candidate_version is not None:
                return candidate_version

    try:
        with open(CANDIDATE_CACHE_PATH, "r") as f:
            return f.read().strip()
    except Exception:
        pass

    return None


def check_for_new_version() -> Optional[str]:
    candidate = get_last_known_candidate()
    if candidate and version_compare(candidate, get_version()) > 0:
        return candidate
    return None
