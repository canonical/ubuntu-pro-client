# Test helpers.

import os
import sys
from pathlib import Path
import subprocess
from collections import namedtuple

from fixtures import (
    TestWithFixtures,
    TempDir)

from fakes import (
    SNAP_LIVEPATCH_INSTALLED,
    SNAP_LIVEPATCH_NOT_INSTALLED,
    LIVEPATCH_ENABLED,
    LIVEPATCH_DISABLED)

ProcessResult = namedtuple('ProcessResult', ['returncode', 'stdout', 'stderr'])


if sys.version_info < (3, 5):
    # Python 3,4 doesn't provide methods to read/write Paths directly

    def _read(self):
        with self.open() as fd:
            return fd.read()

    def _write(self, text):
        with self.open('w') as fd:
            fd.write(text)

    Path.read_text = _read
    Path.write_text = _write
    del(_read)
    del(_write)


class UbuntuAdvantageTest(TestWithFixtures):

    SERIES = None
    KERNEL_VERSION = None
    ARCH = None

    def setUp(self):
        super(UbuntuAdvantageTest, self).setUp()
        self.tempdir = self.useFixture(TempDir())
        self.repo_list = Path(self.tempdir.join('repo.list'))
        self.boot_cfg = Path(self.tempdir.join('boot.cfg'))
        self.fstab = Path(self.tempdir.join('fstab'))
        self.fips_enabled_file = Path(self.tempdir.join('fips_enabled_file'))
        self.bin_dir = Path(self.tempdir.join('bin'))
        self.etc_dir = Path(self.tempdir.join('etc'))
        self.keyrings_dir = Path(self.tempdir.join('keyrings'))
        self.trusted_gpg_dir = Path(self.tempdir.join('trusted.gpg.d'))
        self.apt_auth_file = Path(self.tempdir.join('auth.conf'))
        self.apt_method_https = self.bin_dir / 'apt-method-https'
        self.ca_certificates = self.bin_dir / 'update-ca-certificates'
        self.snapd = self.bin_dir / 'snapd'
        # setup directories and files
        self.bin_dir.mkdir()
        self.keyrings_dir.mkdir()
        self.etc_dir.mkdir()
        self.fstab.write_text('')
        self.trusted_gpg_dir.mkdir()
        (self.keyrings_dir / 'ubuntu-esm-keyring.gpg').write_text('GPG key')
        (self.keyrings_dir / 'ubuntu-esm-v2-keyring.gpg').write_text(
            'GPG key trusty')
        (self.keyrings_dir / 'ubuntu-fips-keyring.gpg').write_text('GPG key')
        self.make_fake_binary('apt-get')
        self.make_fake_binary('apt-method-https')
        self.make_fake_binary('update-ca-certificates')
        self.make_fake_binary('id', command='echo 0')
        self.make_fake_binary('snapd')
        self.make_fake_binary('update-grub')
        self.make_fake_binary('zipl')

    def make_fake_binary(self, binary, command='true'):
        """Create a script to fake a binary in path."""
        path = self.bin_dir / binary
        path.write_text('#!/bin/sh\n{}\n'.format(command))
        path.chmod(0o755)

    def read_file(self, path):
        """Return the content of a file with path relative to the test dir."""
        with open(self.tempdir.join(path)) as fh:
            return fh.read()

    def script(self, *args):
        """Run the script."""
        command = ['./ubuntu-advantage']
        command.extend(args)
        path = os.pathsep.join([str(self.bin_dir), os.environ['PATH']])
        env = {
            'PATH': path,
            'FSTAB': str(self.fstab),
            'REPO_LIST': str(self.repo_list),
            'FIPS_REPO_LIST': str(self.repo_list),
            'FIPS_BOOT_CFG': str(self.boot_cfg),
            'FIPS_BOOT_CFG_DIR': str(self.etc_dir),
            'FIPS_ENABLED_FILE': str(self.fips_enabled_file),
            'KEYRINGS_DIR': str(self.keyrings_dir),
            'APT_AUTH_FILE': str(self.apt_auth_file),
            'APT_KEYS_DIR': str(self.trusted_gpg_dir),
            'APT_METHOD_HTTPS': str(self.apt_method_https),
            'CA_CERTIFICATES': str(self.ca_certificates),
            'SNAPD': str(self.snapd)}
        if self.SERIES:
            env['SERIES'] = self.SERIES
        if self.KERNEL_VERSION:
            env['KERNEL_VERSION'] = self.KERNEL_VERSION
        if self.ARCH:
            env['ARCH'] = self.ARCH
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        process.wait()
        result = ProcessResult(
            process.returncode,
            process.stdout.read().decode('utf-8'),
            process.stderr.read().decode('utf-8'))
        process.stdout.close()
        process.stderr.close()
        return result

    def setup_livepatch(self, installed=None, enabled=None):
        """Setup livepatch-related fakes."""
        if installed is not None:
            command = (
                SNAP_LIVEPATCH_INSTALLED if installed
                else SNAP_LIVEPATCH_NOT_INSTALLED)
            self.make_fake_binary('snap', command=command)
        if enabled is not None:
            command = LIVEPATCH_ENABLED if enabled else LIVEPATCH_DISABLED
            self.make_fake_binary('canonical-livepatch', command=command)
