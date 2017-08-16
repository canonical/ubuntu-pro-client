# Test helpers.

import os
from pathlib import Path
import subprocess
from collections import namedtuple

from fixtures import (
    TestWithFixtures,
    TempDir)

from fakes import (
    SNAP_LIVEPATCH_INSTALLED,
    LIVEPATCH_ENABLED)


ProcessResult = namedtuple('ProcessResult', ['returncode', 'stdout', 'stderr'])


class UbuntuAdvantageTest(TestWithFixtures):

    def setUp(self):
        super(UbuntuAdvantageTest, self).setUp()
        tempdir = self.useFixture(TempDir())
        self.repo_list = Path(tempdir.join('repo.list'))
        self.bin_dir = Path(tempdir.join('bin'))
        self.keyrings_dir = Path(tempdir.join('keyrings'))
        self.trusted_gpg_dir = Path(tempdir.join('trusted.gpg.d'))
        self.apt_method_https = self.bin_dir / 'apt-method-https'
        self.ca_certificates = self.bin_dir / 'update-ca-certificates'
        self.snapd = self.bin_dir / 'snapd'
        # setup directories and files
        self.bin_dir.mkdir()
        self.keyrings_dir.mkdir()
        self.trusted_gpg_dir.mkdir()
        (self.keyrings_dir / 'ubuntu-esm-keyring.gpg').write_text('GPG key')
        self.make_fake_binary('apt-get')
        self.make_fake_binary('apt-method-https')
        self.make_fake_binary('update-ca-certificates')
        self.make_fake_binary('id', command='echo 0')
        self.make_fake_binary('lsb_release', command='echo precise')
        self.make_fake_binary('snapd')
        # in our default setup the snap is installed and enabled
        self.make_fake_binary('snap', command=SNAP_LIVEPATCH_INSTALLED)
        self.make_fake_binary('canonical-livepatch', command=LIVEPATCH_ENABLED)
        self.make_fake_binary('uname', command='echo 4.4.0-89-generic')
        self.livepatch_token = '0123456789abcdef1234567890abcdef'

    def make_fake_binary(self, binary, command='true'):
        path = self.bin_dir / binary
        path.write_text('#!/bin/sh\n{}\n'.format(command))
        path.chmod(0o755)

    def script(self, *args):
        """Run the script."""
        command = ['./ubuntu-advantage']
        command.extend(args)
        path = os.pathsep.join([str(self.bin_dir), os.environ['PATH']])
        env = {
            'PATH': path,
            'REPO_LIST': str(self.repo_list),
            'KEYRINGS_DIR': str(self.keyrings_dir),
            'APT_KEYS_DIR': str(self.trusted_gpg_dir),
            'APT_METHOD_HTTPS': str(self.apt_method_https),
            'CA_CERTIFICATES': str(self.ca_certificates),
            'SNAPD': str(self.snapd)}
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
