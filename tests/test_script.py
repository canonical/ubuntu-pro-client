# Tests for the ubuntu-advantage script.

from testing import UbuntuAdvantageTest


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

    def test_status_precise(self):
        """The status command shows livepatch not available on precise."""
        self.SERIES = 'precise'
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)
        self.assertIn("esm: disabled", process.stdout)

    def test_status_precise_esm_enabled(self):
        """The status command shows esm enabled."""
        self.SERIES = 'precise'
        self.make_fake_binary('apt-cache', command='echo esm.ubuntu.com')
        process = self.script('status')
        self.assertIn("livepatch: disabled (not available)", process.stdout)
        self.assertIn("esm: enabled", process.stdout)

    def test_status_xenial(self):
        """The status command shows only livepatch available on xenial."""
        self.SERIES = 'xenial'
        self.setup_livepatch(installed=True)
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
        self.assertIn("fully-patched: true", process.stdout)
        self.assertIn("esm: disabled (not available)", process.stdout)
