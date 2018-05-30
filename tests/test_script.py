"""Tests for the ubuntu-advantage script."""

from testing import UbuntuAdvantageTest
from fakes import LIVEPATCH_UNSUPPORTED_KERNEL


class UbuntuAdvantageScriptTest(UbuntuAdvantageTest):

    def test_enable_disable_needs_root(self):
        """The script must be run as root for enable and disable actions."""
        self.make_fake_binary('id', command='echo 100')
        actions = ['enable-esm', 'disable-esm', 'enable-livepatch',
                   'disable-livepatch']
        for action in actions:
            # we don't need to pass a token for the enable actions since the
            # root check is before the parameter check
            process = self.script(action)
            self.assertEqual(2, process.returncode)
            self.assertIn('This command must be run as root', process.stderr)

    def test_usage(self):
        """Calling the script with no args prints out the usage."""
        process = self.script()
        self.assertEqual(1, process.returncode)
        self.assertIn('usage: ubuntu-advantage', process.stderr)

    def test_invalid_command(self):
        """Calling the script with an unknown command prints an error."""
        process = self.script('invalid')
        self.assertEqual(1, process.returncode)
        self.assertIn('Invalid command: "invalid"', process.stderr)
        self.assertIn('usage: ubuntu-advantage', process.stderr)

    def test_unknown_service_command(self):
        """Calling the script with an unknown service arg prints an error."""
        process = self.script('break-esm')
        self.assertEqual(1, process.returncode)
        self.assertIn('Invalid command: "break-esm"', process.stderr)
        self.assertIn('usage: ubuntu-advantage', process.stderr)

    def test_status_precise(self):
        """The status command shows livepatch not available on precise."""
        self.SERIES = 'precise'
        self.setup_livepatch(installed=False, enabled=False)
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)
        self.assertIn("esm: disabled", process.stdout)

    def test_status_precise_esm_enabled(self):
        """The status command shows esm enabled."""
        self.SERIES = 'precise'
        self.setup_esm(enabled=True)
        self.setup_livepatch(installed=False, enabled=False)
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)
        self.assertIn("esm: enabled", process.stdout)

    def test_status_xenial(self):
        """The status command shows only livepatch available on xenial."""
        self.SERIES = 'xenial'
        self.setup_livepatch(installed=True, enabled=False)
        process = self.script('status')
        self.assertIn("livepatch: disabled", process.stdout)
        self.assertIn("esm: disabled (not available)", process.stdout)

    def test_status_xenial_livepatch_enabled(self):
        """The status command shows livepatch enabled on xenial."""
        self.SERIES = 'xenial'
        self.setup_livepatch(installed=True, enabled=True)
        process = self.script('status')
        self.assertIn("livepatch: enabled", process.stdout)
        # the livepatch status output is also included
        self.assertIn("patchState: applied", process.stdout)
        self.assertIn("esm: disabled (not available)", process.stdout)

    def test_status_i686_livepatch_not_avaiable(self):
        """The status command shows livepatch as not available on i686."""
        self.SERIES = 'xenial'
        self.ARCH = 'i686'
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)

    def test_status_with_one_service(self):
        """The status for a single service can be returned."""
        self.SERIES = 'precise'
        process = self.script('status', 'fips')
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stdout, 'fips: disabled (not available)\n')

    def test_status_with_one_service_unknown(self):
        """The script exits with error on unknown service status name."""
        process = self.script('status', 'unknown')
        self.assertEqual(process.returncode, 1)

    def test_status_livepatch_unsupported_kernel(self):
        """Livepatch is unavailable on an unsupported kernel."""
        self.SERIES = 'xenial'
        self.ARCH = 'x86_64'
        self.setup_livepatch(
            installed=True, enabled=False,
            livepatch_command=LIVEPATCH_UNSUPPORTED_KERNEL)
        process = self.script('status')
        self.assertIn('livepatch: disabled (unsupported kernel)',
                      process.stdout)

    def test_version(self):
        """The version command shows the package version."""
        self.make_fake_binary('dpkg-query', command='echo 123')
        process = self.script('version')
        self.assertEqual(process.stdout, '123\n')
