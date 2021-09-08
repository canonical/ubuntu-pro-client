"""
Version determination functions

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""
import os.path

from uaclient import util

__VERSION__ = "27.3"
PACKAGED_VERSION = "@@PACKAGED_VERSION@@"
VERSION_TMPL = "{version}{feature_suffix}"


def get_version(_args=None, features={}):
    """Return the packaged version as a string

         Prefer the binary PACKAGED_VESION set by debian/rules to DEB_VERSION.
         If unavailable, check for a .git development environments:
           a. If run in our upstream repo `git describe` will gives a leading
              XX.Y so return the --long version to allow daily build recipes
              to count commit offset from upstream's XX.Y signed tag.
           b. If run in a git-ubuntu pkg repo, upstream tags aren't visible,
              parse the debian/changelog in that case
    """
    feature_suffix = ""
    for key, value in sorted(features.items()):
        feature_suffix += " {enabled}{name}".format(
            enabled="+" if value else "-", name=key
        )
    if not PACKAGED_VERSION.startswith("@@PACKAGED_VERSION"):
        return VERSION_TMPL.format(
            version=PACKAGED_VERSION, feature_suffix=feature_suffix
        )
    topdir = os.path.dirname(os.path.dirname(__file__))
    if os.path.exists(os.path.join(topdir, ".git")):
        cmd = ["git", "describe", "--abbrev=8", "--match=[0-9]*", "--long"]
        try:
            out, _ = util.subp(cmd)
            return out.strip() + feature_suffix
        except util.ProcessExecutionError:
            # Rely on debian/changelog because we are in a git-ubuntu or other
            # packaging repo
            cmd = ["dpkg-parsechangelog", "-S", "version"]
            out, _ = util.subp(cmd)
            return VERSION_TMPL.format(
                version=out.strip(), feature_suffix=feature_suffix
            )
    return VERSION_TMPL.format(
        version=__VERSION__, feature_suffix=feature_suffix
    )
