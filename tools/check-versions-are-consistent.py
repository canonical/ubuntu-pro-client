import re
import subprocess
import sys

sys.path.insert(0, ".")

from uaclient.version import __VERSION__

python_version = __VERSION__
changelog_version = (
    subprocess.check_output(["dpkg-parsechangelog", "-S", "version"])
    .decode("utf-8")
    .strip()
)

# remove tilde and suffix of changelog_version if present
# typical version strings:
# GH: 32.3ubuntu1~1.gbp761c11~noble1 -> 32.3
# backports: 32.3~22.04 -> 32.3
# ppa test builds: 32.3~22.04~ppa1 -> 32.3
# devel: 1:1+devel -> 1:1+devel
#
m = re.match(r"((\d+:\d+\+devel)|\d+(\.\d+)?)", changelog_version)
if m:
    base_changelog_version = m.group()
else:
    base_changelog_version = None

if python_version != base_changelog_version:
    print(
        'version.py says "{}" but changelog says "{}"'.format(
            python_version, changelog_version
        ),
        file=sys.stderr,
    )
    sys.exit(1)
