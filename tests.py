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
        self.key_file = Path(tempdir.join('apt.key'))

    def script(self, *args, user_id=0):
        """Run the script."""
        command = ['./ubuntu-advantage']
        command.extend(args)
        env = {
            'USER_ID': str(user_id),  # fake running as a specific user
            'REPO_LIST': str(self.repo_list),
            'APT_KEY_ADD': 'tee {}'.format(self.key_file)}
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
        process = self.script('enable-esm', 'user:pass', user_id=1000)
        self.assertEqual(2, process.returncode)
        self.assertIn('This command must be run as root', process.stderr)

    def test_usage(self):
        """Calling the script with not args prints out the usage."""
        process = self.script(user_id=1000)
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
        self.assertIn(
            '-----BEGIN PGP PUBLIC KEY BLOCK-----', self.key_file.read_text())

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

    def test_disable_disabled(self):
        """If the repo is not enabled, disabling is a no-op."""
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository was not enabled', process.stdout)
