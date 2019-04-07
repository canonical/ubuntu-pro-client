# Copyright (C) 2019 Canonical Ltd.
# This file is part of ubuntu-advantage-client.  See LICENSE file for license.

import glob
import setuptools

from uaclient import defaults, version

NAME = 'ubuntu-advantage-tools'

INSTALL_REQUIRES = open('requirements.txt').read().rstrip('\n').split('\n')
TEST_REQUIRES = open('test-requirements.txt').read().rstrip('\n').split('\n')


def _get_version():
    parts = version.get_version().split('-')
    if len(parts) == 1:
        return parts[0]
    major_minor, _subrev, _commitish = parts
    return major_minor


setuptools.setup(
    name=NAME,
    version=_get_version(),
    packages=setuptools.find_packages(
        exclude=['*.testing', 'tests.*', '*.tests', 'tests']
    ),
    data_files=[
        ('/etc/ubuntu-advantage', ['uaclient.conf']),
        ('/usr/share/keyrings', glob.glob('debian/keyrings/*')),
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
