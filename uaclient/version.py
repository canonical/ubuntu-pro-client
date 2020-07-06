"""
Version determination functions

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""
import os.path
from uaclient import util


__VERSION__ = "25.0"
PACKAGED_VERSION = "@@PACKAGED_VERSION@@"
VERSION_TMPL = "{version}{overlay}"


def get_version(_args=None, machine_token_overlay_str=""):
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
        return VERSION_TMPL.format(
            version=PACKAGED_VERSION, overlay=machine_token_overlay_str
        )
    topdir = os.path.dirname(os.path.dirname(__file__))
    if os.path.exists(os.path.join(topdir, ".git")):
        cmd = ["git", "describe", "--abbrev=8", "--match=[0-9]*", "--long"]
        try:
            out, _ = util.subp(cmd)
            return out.strip()
        except util.ProcessExecutionError:
            # Rely on debian/changelog because we are in a git-ubuntu or other
            # packaging repo
            cmd = ["dpkg-parsechangelog", "-S", "version"]
            out, _ = util.subp(cmd)
            return VERSION_TMPL.format(
                version=out.strip(), overlay=machine_token_overlay_str
            )
    return VERSION_TMPL.format(
        version=__VERSION__, overlay=machine_token_overlay_str
    )
