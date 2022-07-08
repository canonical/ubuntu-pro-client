"""
Version determination functions

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""
import os.path

from uaclient import exceptions, util

__VERSION__ = "27.9"
PACKAGED_VERSION = "@@PACKAGED_VERSION@@"


def get_version():
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
            out, _ = util.subp(cmd)
            return out.strip()
        except exceptions.ProcessExecutionError:
            pass
    return __VERSION__
