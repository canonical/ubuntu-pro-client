# Copyright (C) 2019 Canonical Ltd.
# This file is part of ubuntu-advantage-client.  See LICENSE file for license.

import glob
import setuptools

from uaclient import defaults, util, version

NAME = "ubuntu-advantage-tools"

INSTALL_REQUIRES = open("requirements.txt").read().rstrip("\n").split("\n")
TEST_REQUIRES = open("test-requirements.txt").read().rstrip("\n").split("\n")


def _get_version():
    parts = version.get_version().split("-")
    if len(parts) == 1:
        return parts[0]
    major_minor, _subrev, _commitish = parts
    return major_minor


def _get_data_files():
    data_files = [
        ("/etc/ubuntu-advantage", ["uaclient.conf"]),
        ("/usr/share/keyrings", glob.glob("keyrings/*")),
        (defaults.CONFIG_DEFAULTS["data_dir"], []),
    ]
    rel_major, _rel_minor = util.get_platform_info()["release"].split(".", 1)
    if rel_major == "14":
        data_files.append(
            ("/etc/apt/apt.conf.d", ["apt.conf.d/51ubuntu-advantage-esm"])
        )
        data_files.append(("/etc/init", glob.glob("upstart/*")))
    else:
        data_files.append(("/lib/systemd/system", glob.glob("systemd/*")))
    return data_files


setuptools.setup(
    name=NAME,
    version=_get_version(),
    packages=setuptools.find_packages(
        exclude=[
            "*.testing",
            "tests.*",
            "*.tests",
            "tests",
            "features",
            "features.*",
        ]
    ),
    data_files=_get_data_files(),
    install_requires=INSTALL_REQUIRES,
    extras_require=dict(test=TEST_REQUIRES),
    author="Ubuntu Server Team",
    author_email="ubuntu-server@lists.ubuntu.com",
    description=("Manage Ubuntu Advantage support entitlements"),
    license="GPLv3",
    url="https://ubuntu.com/support",
    entry_points={
        "console_scripts": [
            "ubuntu-advantage=uaclient.cli:main",
            "ua=uaclient.cli:main",
        ]
    },
)
