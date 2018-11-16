"""Test helpers."""

import os
import sys
from pathlib import Path
import subprocess
from collections import namedtuple

from fixtures import (
    TestWithFixtures,
    TempDir,
)

from fakes import (
    SNAP_LIVEPATCH_INSTALLED,
    SNAP_LIVEPATCH_NOT_INSTALLED,
    LIVEPATCH_ENABLED,
    LIVEPATCH_DISABLED,
    ESM_ENABLED,
    ESM_DISABLED,
)

ProcessResult = namedtuple('ProcessResult', ['returncode', 'stdout', 'stderr'])


if sys.version_info < (3, 5):
    # Python 3.4 doesn't provide methods to read/write Paths directly

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
    SCRIPT = './ubuntu-advantage'

    def setUp(self):
        super(UbuntuAdvantageTest, self).setUp()
        self.tempdir = self.useFixture(TempDir())
        self.boot_cfg = Path(self.tempdir.join('boot.cfg'))
        self.fstab = Path(self.tempdir.join('fstab'))
        self.cpuinfo = Path(self.tempdir.join('cpuinfo'))
        self.esm_repo_list = Path(self.tempdir.join('esm-repo.list'))
        self.fips_repo_list = Path(self.tempdir.join('fips-repo.list'))
        self.fips_updates_repo_list = Path(
            self.tempdir.join('fips-updates-repo.list'))
        self.cc_repo_list = Path(self.tempdir.join('cc-repo.list'))
        self.cisaudit_repo_list = Path(self.tempdir.join('cisaudit-repo.list'))
        self.fips_repo_preferences = Path(
            self.tempdir.join('preferences-fips'))
        self.fips_updates_repo_preferences = Path(
            self.tempdir.join('preferences-fips-updates'))
        self.fips_enabled_file = Path(self.tempdir.join('fips_enabled_file'))
        self.bin_dir = Path(self.tempdir.join('bin'))
        self.etc_dir = Path(self.tempdir.join('etc'))
        self.keyrings_dir = Path(self.tempdir.join('keyrings'))
        self.trusted_gpg_dir = Path(self.tempdir.join('trusted.gpg.d'))
        self.apt_auth_file = Path(self.tempdir.join('auth.conf'))
        self.apt_method_https = self.bin_dir / 'apt-method-https'
        self.ca_certificates = self.bin_dir / 'update-ca-certificates'
        self.snapd = self.bin_dir / 'snapd'
        self.apt_helper = self.bin_dir / 'apt-helper'
        self.ua_status_cache = Path(self.tempdir.join('ua-status-cache'))
        # setup directories and files
        self.bin_dir.mkdir()
        self.keyrings_dir.mkdir()
        self.etc_dir.mkdir()
        self.fstab.write_text('')
        self.trusted_gpg_dir.mkdir()
        (self.keyrings_dir / 'ubuntu-esm-keyring.gpg').write_text('GPG key')
        (self.keyrings_dir / 'ubuntu-fips-keyring.gpg').write_text('GPG key')
        (self.keyrings_dir / 'ubuntu-fips-updates-keyring.gpg').write_text(
            'GPG key')
        (self.keyrings_dir / 'ubuntu-cc-keyring.gpg').write_text('GPG key')
        (self.keyrings_dir /
            'ubuntu-securitybenchmarks-keyring.gpg').write_text('GPG key')
        self.cpuinfo.write_text('flags\t\t: fpu apic')
        self.make_fake_binary('apt-get')
        self.make_fake_binary('apt-helper')
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

    def script(self, *args, env_update=None):
        """Run the specified script."""
        command = [self.SCRIPT]
        command.extend(args)
        path = os.pathsep.join([str(self.bin_dir), os.environ['PATH']])
        env = {
            'UA': './ubuntu-advantage',
            'UA_STATUS_CACHE': str(self.ua_status_cache),
            'PATH': path,
            'FSTAB': str(self.fstab),
            'CPUINFO': str(self.cpuinfo),
            'ESM_REPO_LIST': str(self.esm_repo_list),
            'FIPS_REPO_LIST': str(self.fips_repo_list),
            'FIPS_UPDATES_REPO_LIST': str(self.fips_updates_repo_list),
            'CC_PROVISIONING_REPO_LIST': str(self.cc_repo_list),
            'CISAUDIT_REPO_LIST': str(self.cisaudit_repo_list),
            'FIPS_BOOT_CFG': str(self.boot_cfg),
            'FIPS_BOOT_CFG_DIR': str(self.etc_dir),
            'FIPS_ENABLED_FILE': str(self.fips_enabled_file),
            'FIPS_REPO_PREFERENCES': str(self.fips_repo_preferences),
            'FIPS_UPDATES_REPO_PREFERENCES': str(
                self.fips_updates_repo_preferences),
            'KEYRINGS_DIR': str(self.keyrings_dir),
            'APT_HELPER': str(self.apt_helper),
            'APT_AUTH_FILE': str(self.apt_auth_file),
            'APT_KEYS_DIR': str(self.trusted_gpg_dir),
            'APT_METHOD_HTTPS': str(self.apt_method_https),
            'CA_CERTIFICATES': str(self.ca_certificates),
            'SNAPD': str(self.snapd)}
        if env_update:
            env.update(env_update)
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

    def setup_livepatch(self, installed=False, enabled=None,
                        livepatch_command=None):
        """Setup livepatch-related fakes."""
        command = (
            SNAP_LIVEPATCH_INSTALLED if installed
            else SNAP_LIVEPATCH_NOT_INSTALLED)
        self.make_fake_binary('snap', command=command)
        if enabled is not None:
            if livepatch_command is not None:
                command = livepatch_command
            else:
                command = LIVEPATCH_ENABLED if enabled else LIVEPATCH_DISABLED
            self.make_fake_binary('canonical-livepatch', command=command)

    def setup_esm(self, enabled=False):
        """Setup the ESM repository."""
        command = ESM_ENABLED if enabled else ESM_DISABLED
        self.make_fake_binary('apt-cache', command=command)

    def setup_fips(self, enabled=None):
        """Setup FIPS."""
        if enabled is None:
            return
        self.make_fake_binary('dpkg-query')
        self.fips_enabled_file.write_text('1' if enabled else '0')

    def setup_cc(self, enabled=False):
        """Setup the CC repository."""
        self.make_fake_binary(
            'dpkg-query', command='[ $2 != ubuntu-commoncriteria ]')

    def setup_cisaudit(self, enabled=False):
        """Setup the CISAudit repository."""
        if enabled is True:
            self.make_fake_binary(
                'dpkg-query', command='[ $2 = ubuntu-cisbenchmark-16.04 ]')
        else:
            self.make_fake_binary(
                'dpkg-query', command='[ $2 != ubuntu-cisbenchmark-16.04 ]')
