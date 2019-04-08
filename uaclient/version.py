"""
Version determination functions

These are in their own file so they can be imported by setup.py before we have
any of our dependencies installed.
"""
import os.path
from subprocess import check_output


__VERSION__ = '19.2'
PACKAGED_VERSION = '@@PACKAGED_VERSION@@'


def get_version(_args=None):
    """Return the package version if set, otherwise return git describe."""
    if not PACKAGED_VERSION.startswith('@@PACKAGED_VERSION'):
        return PACKAGED_VERSION
    topdir = os.path.dirname(os.path.dirname(__file__))
    if os.path.exists(os.path.join(topdir, '.git')):
        cmd = ['git', 'describe', '--abbrev=8', '--match=[0-9]*', '--long']
        return check_output(cmd, universal_newlines=True).strip()
    return __VERSION__
