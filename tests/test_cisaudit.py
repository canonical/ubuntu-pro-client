"""Tests for CISAudit-related commands."""

from testing import UbuntuAdvantageTest


class CISAUDITTest(UbuntuAdvantageTest):

    SERIES = 'xenial'
    ARCH = 'x86_64'

    def setUp(self):
        super().setUp()
        self.setup_cisaudit()

    def test_enable_cisaudit_provisioning(self):
        """The enable-cisaudit enables security benchmarks repository."""
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Ubuntu Security Benchmarks PPA repository enabled.',
            process.stdout)
        expected = (
            'deb https://private-ppa.launchpad.net/ubuntu-advantage/'
            'security-benchmarks/ubuntu xenial main\n'
            '# deb-src https://private-ppa.launchpad.net/'
            'ubuntu-advantage/security-benchmarks/ubuntu xenial main\n')
        self.assertEqual(expected, self.cisaudit_repo_list.read_text())
        self.assertEqual(
            self.apt_auth_file.read_text(),
            'machine private-ppa.launchpad.net/ubuntu-advantage/'
            'security-benchmarks/ubuntu/'
            ' login user password pass\n')
        self.assertEqual(self.apt_auth_file.stat().st_mode, 0o100600)
        cis_keyring = 'ubuntu-securitybenchmarks-keyring.gpg'
        keyring_file = self.trusted_gpg_dir / cis_keyring
        self.assertEqual('GPG key', keyring_file.read_text())
        self.assertIn(
            'Successfully installed the CIS audit tool.',
            process.stdout)
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_cisaudit_auth_if_other_entries(self):
        """Existing auth.conf entries are preserved."""
        auth = 'machine example.com login user password pass\n'
        self.apt_auth_file.write_text(auth)
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(auth, self.apt_auth_file.read_text())

    def test_enable_cisaudit_install_apt_transport_https(self):
        """enable-cisaudit installs apt-transport-https if needed."""
        self.apt_method_https.unlink()
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_cisaudit_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_cisaudit_install_ca_certificates(self):
        """enable-cisaudit installs ca-certificates if needed."""
        self.ca_certificates.unlink()
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency ca-certificates',
            process.stdout)

    def test_enable_cisaudit_install_ca_certificates_fails(self):
        """Stderr is printed if ca-certificates install fails."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_cisaudit_missing_token(self):
        """The token must be specified when using enable-cisaudit."""
        process = self.script('enable-cisaudit')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_cisaudit_invalid_token_format(self):
        """The cisaudit token must be specified as "user:password"."""
        process = self.script('enable-cisaudit', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_cisaudit_invalid_token(self):
        """If token is invalid, an error is returned."""
        message = (
            'E: Failed to fetch https://esm.ubuntu.com/'
            '  401  Unauthorized [IP: 1.2.3.4]')
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn('Invalid token', process.stderr)

    def test_enable_cisaudit_error_checking_token(self):
        """If token check fails, an error is returned."""
        message = (
            'E: Failed to fetch https://esm.ubuntu.com/'
            '  404  Not Found [IP: 1.2.3.4]')
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn(
            'Failed checking token (404  Not Found [IP: 1.2.3.4])',
            process.stderr)

    def test_enable_cisaudit_skip_token_check_no_helper(self):
        """If apt-helper is not found, the token check is skipped."""
        self.apt_helper.unlink()
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Checking token... SKIPPED', process.stdout)

    def test_enable_cisaudit_only_supported_on_xenial(self):
        """The enable-cisaudit option fails if not on Xenial."""
        self.SERIES = 'zesty'
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Canonical CIS 16.04 Benchmark Audit Tool '
            'is not supported on zesty',
            process.stderr)

    def test_unsupported_on_i686(self):
        """CISAudit is unsupported on i686 arch."""
        self.ARCH = 'i686'
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(7, process.returncode)
        self.assertIn(
            'Sorry, but Canonical CIS 16.04 Benchmark Audit Tool '
            'is not supported on i686',
            process.stderr)

    def test_unsupported_on_arm64(self):
        """CISAudit is unsupported on arm64 arch."""
        self.ARCH = 'arm64'
        process = self.script('enable-cisaudit', 'user:pass')
        self.assertEqual(7, process.returncode)
        self.assertIn(
            'Sorry, but Canonical CIS 16.04 Benchmark Audit Tool '
            'is not supported on arm64',
            process.stderr)
