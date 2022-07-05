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
base_changelog_version = changelog_version.split("~")[0]

if python_version != base_changelog_version:
    print(
        'version.py says "{}" but changelog says "{}"'.format(
            python_version, changelog_version
        ),
        file=sys.stderr,
    )
    sys.exit(1)
