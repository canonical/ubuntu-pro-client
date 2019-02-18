import glob
import setuptools
import subprocess
import os

from uaclient import config
from uaclient.util import subp

NAME = 'ubuntu-advantage-tools'


def get_version():
    parts = config.get_version().split('-')
    if len(parts) == 1:
       return parts[0]
    major_minor, _subrev, _commitish = parts
    return major_minor


_dir = os.path.dirname(os.path.realpath(__name__))


requirements, _err = subp(['./dev/read-dependencies'])
INSTALL_REQUIRES =requirements.rstrip('\n').split('\n')

TEST_REQUIRES = [
    'coverage',
    'flake8',
    'nose',
    'pylint',
    'testtools',
]

setuptools.setup(
    name=NAME,
    version=get_version(),
    packages=setuptools.find_packages(exclude=['*.testing', 'tests.*', '*.tests', 'tests']),
    data_files=[('/etc/ubuntu-advantage', ['uaclient.conf']),
                ('/etc/apt/apt.conf.d', glob.glob('apt.conf.d/*')),
                ('/etc/update-motd.d', glob.glob('update-motd.d/*')),
                ('/usr/lib/ubuntu-advantage', glob.glob('lib/*')),
                ('/usr/share/keyrings', glob.glob('keyrings/*')),
                (config.CONFIG_DEFAULTS['data_dir'], [])],
    install_requires=INSTALL_REQUIRES,
    extras_require=dict(test=TEST_REQUIRES),
    author='Ubuntu Server Team',
    author_email='ubuntu-server@lists.ubuntu.com',
    description=('Manage Ubuntu Advantage support entitlements: esm, fips'
                 ' and livepatch'),
    license='GPLv3',
    url='https://ubuntu.com/advantage',
    entry_points={'console_scripts': ['ubuntu-advantage=uaclient.cli:main',
                                      'ua=uaclient.cli:main']}
)

