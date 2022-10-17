"""
Version determination functions

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""
import os.path
import re
from math import inf
from typing import Optional

from uaclient.apt import (
    compare_versions,
    get_apt_cache_policy_for_package,
    get_apt_cache_time,
)
from uaclient.defaults import CANDIDATE_CACHE_PATH, UAC_RUN_PATH
from uaclient.exceptions import ProcessExecutionError
from uaclient.system import subp

__VERSION__ = "28.0"
PACKAGED_VERSION = "@@PACKAGED_VERSION@@"

CANDIDATE_REGEX = r"Candidate: (?P<candidate>.*?)\n"


def get_version() -> str:
    """Return the packaged version as a string

    Prefer the binary PACKAGED_VESION set by debian/rules to DEB_VERSION.
    If unavailable, check for a .git development environments:
      a. If run in our upstream repo `git describe` will gives a leading
         XX.Y so return the --long version to allow daily build recipes
         to count commit offset from upstream's XX.Y signed tag.
      b. If run in a git-ubuntu pkg repo, upstream tags aren't visible,
         parse the debian/changelog in that case
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
        candidate_version = None
        try:
            policy = get_apt_cache_policy_for_package("ubuntu-advantage-tools")
            match = re.search(CANDIDATE_REGEX, policy)
            if match:
                candidate_version = match.group("candidate")
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
    if candidate and compare_versions(candidate, get_version(), "gt"):
        return candidate
    return None
