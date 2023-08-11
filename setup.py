# Copyright (C) 2019 Canonical Ltd.
# This file is part of ubuntu-pro-client.  See LICENSE file for license.

import glob

import setuptools

from ubuntupro import defaults

NAME = "ubuntu-advantage-tools"

INSTALL_REQUIRES = open("requirements.txt").read().rstrip("\n").split("\n")


def split_link_deps(reqs_filename):
    """Read requirements reqs_filename and split into pkgs and links

    :return: list of package defs and link defs
    """
    pkgs = []
    links = []
    for line in open(reqs_filename).readlines():
        if line.startswith("git") or line.startswith("http"):
            links.append(line)
        else:
            pkgs.append(line)
    return pkgs, links


TEST_REQUIRES, TEST_LINKS = split_link_deps("test-requirements.txt")


def _get_data_files():
    return [
        ("/etc/ubuntu-advantage", ["uaclient.conf", "help_data.yaml"]),
        ("/etc/update-motd.d", glob.glob("update-motd.d/*")),
        ("/usr/lib/ubuntu-advantage", glob.glob("lib/[!_]*")),
        ("/usr/share/keyrings", glob.glob("keyrings/*")),
        (
            "/etc/update-manager/release-upgrades.d/",
            ["release-upgrades.d/ubuntu-advantage-upgrades.cfg"],
        ),
        ("/etc/apt/preferences.d", glob.glob("preferences.d/*")),
        (defaults.CONFIG_DEFAULTS["data_dir"], []),
        ("/lib/systemd/system", glob.glob("systemd/*")),
        (
            "/usr/share/apport/package-hooks",
            ["apport/source_ubuntu-advantage-tools.py"],
        ),
    ]


setuptools.setup(
    name=NAME,
    # This version does not matter, it is not used anywhere but in unit tests
    # AND IT IS OVER 8000
    version="8001",
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
    dependency_links=TEST_LINKS,
    extras_require=dict(test=TEST_REQUIRES),
    author="Ubuntu Server Team",
    author_email="ubuntu-server@lists.ubuntu.com",
    description=("Manage Ubuntu Pro support entitlements"),
    license="GPLv3",
    url="https://ubuntu.com/support",
    entry_points={
        "console_scripts": [
            "ubuntu-advantage=ubuntupro.cli:main",
            "ua=ubuntupro.cli:main",
        ]
    },
)
