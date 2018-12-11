import setuptools
import os

from uaclient import config

NAME = 'ubuntu-advantage-tools'


def get_version():
    major_minor, commitish  = config.get_version().rsplit('-', 1)
    return major_minor


_dir = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(_dir, 'requirements.txt')) as stream:
    INSTALL_REQUIRES = stream.readlines()

TEST_REQUIRES = [
    'coverage',
    'flake8',
    'pylint',
    'testtools',
]

setuptools.setup(
    name=NAME,
    version=get_version(),
    packages=setuptools.find_packages(),
    data_files=[],
    install_requires=INSTALL_REQUIRES,
    extras_require=dict(test=TEST_REQUIRES),
    author='Ubuntu Server Team',
    author_email='ubuntu-server@lists.ubuntu.com',
    description=('Manage Ubuntu Advantage support entitlements: esm, fips'
                 ' and livepatch'),
    license='gpl3',
    url='https://ubuntu.com/advantage',
    entry_points={'console_scripts': [
        u'ubuntu-advantage=uaclient.cli:main']}
)

