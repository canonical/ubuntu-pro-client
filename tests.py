import os
from pathlib import Path
import subprocess
from collections import namedtuple

from fixtures import TestWithFixtures, TempDir


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
        # setup directories and files
        self.bin_dir.mkdir()
        self.keyrings_dir.mkdir()
        self.trusted_gpg_dir.mkdir()
        (self.keyrings_dir / 'ubuntu-esm-keyring.gpg').write_text('GPG key')
        self.make_fake_binary('apt-get')
        self.make_fake_binary('apt-method-https')
        self.make_fake_binary('id', command='echo 0')

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
            'APT_METHOD_HTTPS': str(self.apt_method_https)}
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

    def test_run_not_as_root(self):
        """The script must be run as root."""
        self.make_fake_binary('id', command='echo 100')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(2, process.returncode)
        self.assertIn('This command must be run as root', process.stderr)

    def test_usage(self):
        """Calling the script with no args prints out the usage."""
        process = self.script()
        self.assertEqual(1, process.returncode)
        self.assertIn('usage: ubuntu-advantage', process.stderr)

    def test_enable(self):
        """The script enables the ESM repository."""
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository enabled', process.stdout)
        expected = (
            'deb https://user:pass@esm.ubuntu.com/ubuntu precise main\n'
            '# deb-src https://user:pass@esm.ubuntu.com/ubuntu precise main\n')
        self.assertEqual(expected, self.repo_list.read_text())
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertEqual('GPG key', keyring_file.read_text())
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_install_apt_transport_https(self):
        """The apt-transport-https package is installed if it's not."""
        self.apt_method_https.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_missing_token(self):
        """The token must be specified when enabling the repository."""
        process = self.script('enable-esm')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_invalid_token(self):
        """The token must be specified as "user:password"."""
        process = self.script('enable-esm', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_disable(self):
        """The script disables the ESM repository."""
        self.script('enable-esm', 'user:pass')
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository disabled', process.stdout)
        self.assertFalse(self.repo_list.exists())
        # the keyring file is removed
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertFalse(keyring_file.exists())

    def test_disable_disabled(self):
        """If the repo is not enabled, disabling is a no-op."""
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository was not enabled', process.stdout)

    def test_is_esm_enabled_true(self):
        """is-esm-enabled returns 0 if the repository is enabled."""
        self.make_fake_binary('apt-cache', command='echo esm.ubuntu.com')
        process = self.script('is-esm-enabled')
        self.assertEqual(0, process.returncode)

    def test_is_esm_enabled_false(self):
        """is-esm-enabled returns 1 if the repository is not enabled."""
        self.make_fake_binary('apt-cache')
        process = self.script('is-esm-enabled')
        self.assertEqual(1, process.returncode)
