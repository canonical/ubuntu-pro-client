# Tests for Livepatch-related commands.

from testing import UbuntuAdvantageTest
from fakes import APT_GET_LOG_WRAPPER


class LivepatchTest(UbuntuAdvantageTest):

    SERIES = 'trusty'
    ARCH = 'x86_64'
    KERNEL_VERSION = '4.4.0-89-generic'

    def setUp(self):
        super().setUp()
        self.setup_livepatch(installed=True, enabled=True)
        self.livepatch_token = '0123456789abcdef1234567890abcdef'

    def test_livepatch_supported_trusty_xenial_not_precise(self):
        """Livepatch is supported in trusty and xenial but not precise."""
        for series in ['trusty', 'xenial']:
            self.SERIES = series
            process = self.script('enable-livepatch')
            # if we get a token error, that means we passed the ubuntu
            # release check.
            self.assertEqual(3, process.returncode)
            self.assertIn('Invalid or missing Livepatch token', process.stderr)
        # precise is not supported
        self.SERIES = 'precise'
        process = self.script('enable-livepatch')
        self.assertEqual(4, process.returncode)
        self.assertIn('Sorry, but Canonical Livepatch is not supported on '
                      'precise', process.stderr)

    def test_enable_livepatch_missing_token(self):
        """The token must be specified when using enable-livepatch."""
        process = self.script('enable-livepatch')
        self.assertEqual(3, process.returncode)
        self.assertIn('Invalid or missing Livepatch token', process.stderr)

    def test_enable_livepatch_invalid_token(self):
        """The Livepatch token must be specified as 32 hex chars."""
        process = self.script('enable-livepatch', 'invalid:token')
        self.assertEqual(3, process.returncode)
        self.assertIn('Invalid or missing Livepatch token', process.stderr)

    def test_enable_livepatch_unsupported_on_ii686(self):
        """Livepatch is only supported on i686."""
        self.ARCH = 'i686'
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(7, process.returncode)
        self.assertIn(
            'Sorry, but Canonical Livepatch is not supported on i686',
            process.stderr)

    def test_enable_livepatch_installs_snapd(self):
        """enable-livepatch installs snapd if needed."""
        self.snapd.unlink()
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn('Installing missing dependency snapd', process.stdout)

    def test_enable_livepatch_apt_get_options(self):
        """apt-get is called with options to accept defaults."""
        self.snapd.unlink()
        self.make_fake_binary('apt-get', command=APT_GET_LOG_WRAPPER)
        self.script('enable-livepatch', self.livepatch_token)
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold install snapd',
            self.read_file('apt_get.args'))
        self.assertIn(
            'DEBIAN_FRONTEND=noninteractive', self.read_file('apt_get.env'))

    def test_enable_livepatch_installs_snap(self):
        """enable-livepatch installs the livepatch snap if needed."""
        self.setup_livepatch(installed=False)
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing the canonical-livepatch snap', process.stdout)

    def test_is_livepatch_enabled_true(self):
        """is-livepatch-enabled returns 0 if the service is enabled."""
        process = self.script('is-livepatch-enabled')
        self.assertEqual(0, process.returncode)

    def test_is_livepatch_enabled_false(self):
        """is-livepatch-enabled returns 1 if the service is not enabled."""
        self.setup_livepatch(enabled=False)
        process = self.script('is-livepatch-enabled')
        self.assertEqual(1, process.returncode)

    def test_enable_livepatch_enabled(self):
        """enable-livepatch when it's already enabled is detected."""
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn('Livepatch already enabled.', process.stdout)

    def test_enable_livepatch(self):
        """enable-livepatch enables the livepatch service."""
        self.setup_livepatch(enabled=False)
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully enabled device. Using machine-token:',
                      process.stdout)

    def test_disable_livepatch_invalid_remove_snap_option(self):
        """disable-livepatch complains if given an invalid argument."""
        process = self.script('disable-livepatch', '-invalidargument')
        self.assertEqual(1, process.returncode)
        self.assertIn('Unknown option "-invalidargument"', process.stderr)

    def test_disable_livepatch_already_disabled(self):
        """disable-livepatch when it's already disabled is detected."""
        self.setup_livepatch(enabled=False)
        process = self.script('disable-livepatch')
        self.assertEqual(0, process.returncode)
        self.assertIn('Livepatch is already disabled.', process.stdout)

    def test_disable_livepatch_supported_trusty_xenial_not_precise(self):
        """Livepatch can't be disabled on unsupported distros."""
        for series in ['trusty', 'xenial']:
            self.SERIES = series
            process = self.script('disable-livepatch')
            self.assertEqual(0, process.returncode)
        # precise is not supported
        self.SERIES = 'precise'
        process = self.script('disable-livepatch')
        # self.assertEqual(4, process.returncode)
        self.assertIn('Sorry, but Canonical Livepatch is not supported on '
                      'precise', process.stderr)

    def test_disable_livepatch(self):
        """disable-livepatch disables the service."""
        process = self.script('disable-livepatch')
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully disabled device. Removed machine-token: '
                      'deadbeefdeadbeefdeadbeefdeadbeef', process.stdout)
        self.assertIn('Note: the canonical-livepatch snap is still installed',
                      process.stdout)

    def test_disable_livepatch_removing_snap(self):
        """disable-livepatch with '-r' will also remove the snap."""
        process = self.script('disable-livepatch', '-r')
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully disabled device. Removed machine-token: '
                      'deadbeefdeadbeefdeadbeefdeadbeef', process.stdout)
        self.assertIn('canonical-livepatch removed', process.stdout)

    def test_enable_livepatch_old_kernel(self):
        """enable-livepatch with an old kernel will not enable livepatch."""
        self.setup_livepatch(enabled=False)
        self.KERNEL_VERSION = '3.10.0-30-generic'
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(5, process.returncode)
        self.assertIn('Your currently running kernel ({}) is too '
                      'old'.format(self.KERNEL_VERSION), process.stdout)

    def test_enable_livepatch_apt_output_is_hidden(self):
        """Hide all apt output when enabling livepatch if exit status is 0."""
        self.make_fake_binary('apt-get',
                              command='echo this goes to stderr >&2;'
                              'echo this goes to stdout;exit 0')
        self.setup_livepatch(enabled=False)
        self.snapd.unlink()
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(0, process.returncode)
        # the UA script is redirecting stderr to stdout and capturing that,
        # but then writing everything back to stderr if there was an error
        self.assertNotIn('this goes to stderr', process.stderr)
        self.assertNotIn('this goes to stdout', process.stderr)

    def test_enable_livepatch_apt_output_shown_if_errors(self):
        """enable-livepatch displays apt errors if there were any."""
        apt_error_code = 99
        self.make_fake_binary(
            'apt-get', command='echo this goes to stderr >&2;'
            'echo this goes to stdout;exit {}'.format(apt_error_code))
        self.setup_livepatch(enabled=False)
        self.snapd.unlink()
        process = self.script('enable-livepatch', self.livepatch_token)
        self.assertEqual(apt_error_code, process.returncode)
        # the UA script is redirecting stderr to stdout and capturing that,
        # but then writing everything back to stderr if there was an error
        self.assertIn('this goes to stderr', process.stderr)
        self.assertIn('this goes to stdout', process.stderr)
