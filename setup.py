# Copyright (C) 2019 Canonical Ltd.
# This file is part of ubuntu-advantage-client.  See LICENSE file for license.

import glob
import setuptools
import sys

from uaclient import defaults, util, version

NAME = 'ubuntu-advantage-tools'

INSTALL_REQUIRES = open('requirements.txt').read().rstrip('\n').split('\n')
TEST_REQUIRES = open('test-requirements.txt').read().rstrip('\n').split('\n')


def _get_version():
    major_minor = version.get_version().split('-')[0]
    changelog = util.load_file('./debian/changelog').split('\n')[0].split(' ')[1]
    changelog_version = changelog.replace('(', '').replace(')', '')
    if major_minor != changelog_version:
        print('Version mismatch\n\td/changelog: %s\n\tversion.py: %s' %
              (changelog_version, major_minor))
        sys.exit(1)
    return major_minor


setuptools.setup(
    name=NAME,
    version=_get_version(),
    packages=setuptools.find_packages(
        exclude=['*.testing', 'tests.*', '*.tests', 'tests']
    ),
    data_files=[
        ('/etc/apt/apt.conf.d', ['apt.conf.d/51ubuntu-advantage-esm']),
        ('/etc/ubuntu-advantage', ['uaclient.conf']),
        ('/usr/share/keyrings', glob.glob('keyrings/*')),
        (defaults.CONFIG_DEFAULTS['data_dir'], [])
    ],
    install_requires=INSTALL_REQUIRES,
    extras_require=dict(test=TEST_REQUIRES),
    author='Ubuntu Server Team',
    author_email='ubuntu-server@lists.ubuntu.com',
    description=('Manage Ubuntu Advantage support entitlements'),
    license='GPLv3',
    url='https://ubuntu.com/support',
    entry_points={
        'console_scripts': [
            'ubuntu-advantage=uaclient.cli:main',
            'ua=uaclient.cli:main'
        ]
    }
)
