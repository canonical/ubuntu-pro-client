"""Tests for CC-related commands."""

from testing import UbuntuAdvantageTest


class CCTest(UbuntuAdvantageTest):

    SERIES = 'xenial'
    ARCH = 'x86_64'

    def setUp(self):
        super().setUp()
        self.setup_cc()

    def test_enable_cc_provisioning(self):
        """The enable-cc-provisioning enables commoncriteria repository."""
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Ubuntu Common Criteria PPA repository enabled.',
            process.stdout)
        expected = (
            'deb https://private-ppa.launchpad.net/ubuntu-advantage/'
            'commoncriteria/ubuntu xenial main\n'
            '# deb-src https://private-ppa.launchpad.net/'
            'ubuntu-advantage/commoncriteria/ubuntu xenial main\n')
        self.assertEqual(expected, self.cc_repo_list.read_text())
        self.assertEqual(
            self.apt_auth_file.read_text(),
            'machine private-ppa.launchpad.net/ubuntu-advantage/'
            'commoncriteria/ubuntu/'
            ' login user password pass\n')
        self.assertEqual(self.apt_auth_file.stat().st_mode, 0o100600)
        keyring_file = self.trusted_gpg_dir / 'ubuntu-cc-keyring.gpg'
        self.assertEqual('GPG key', keyring_file.read_text())
        self.assertIn(
            'Successfully prepared this machine to host'
            ' the Common Criteria artifacts',
            process.stdout)
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_cc_provisioning_auth_if_other_entries(self):
        """Existing auth.conf entries are preserved."""
        auth = 'machine example.com login user password pass\n'
        self.apt_auth_file.write_text(auth)
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(auth, self.apt_auth_file.read_text())

    def test_enable_cc_provisioning_install_apt_transport_https(self):
        """enable-cc-provisioning installs apt-transport-https if needed."""
        self.apt_method_https.unlink()
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_cc_provisioning_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_cc_provisioning_install_ca_certificates(self):
        """enable-fips installs ca-certificates if needed."""
        self.ca_certificates.unlink()
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency ca-certificates',
            process.stdout)

    def test_enable_cc_provisioning_install_ca_certificates_fails(self):
        """Stderr is printed if ca-certificates install fails."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_cc_provisioning_missing_token(self):
        """The token must be specified when using enable-fips."""
        process = self.script('enable-cc-provisioning')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_cc_provisioning_invalid_token_format(self):
        """The CC token must be specified as "user:password"."""
        process = self.script('enable-cc-provisioning', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_cc_provisioning_invalid_token(self):
        """If token is invalid, an error is returned."""
        message = (
            'E: Failed to fetch https://esm.ubuntu.com/'
            '  401  Unauthorized [IP: 1.2.3.4]')
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn('Invalid token', process.stderr)

    def test_enable_cc_provisioning_error_checking_token(self):
        """If token check fails, an error is returned."""
        message = (
            'E: Failed to fetch https://esm.ubuntu.com/'
            '  404  Not Found [IP: 1.2.3.4]')
        self.make_fake_binary(
            'apt-helper', command='echo "{}"; exit 1'.format(message))
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(3, process.returncode)
        self.assertIn('Checking token... ERROR', process.stdout)
        self.assertIn(
            'Failed checking token (404  Not Found [IP: 1.2.3.4])',
            process.stderr)

    def test_enable_cc_provisioning_skip_token_check_no_helper(self):
        """If apt-helper is not found, the token check is skipped."""
        self.apt_helper.unlink()
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Checking token... SKIPPED', process.stdout)

    def test_enable_cc_provisioning_only_supported_on_xenial(self):
        """The enable-cc-provisioning option fails if not on Xenial."""
        self.SERIES = 'zesty'
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Canonical Common Criteria EAL2 Provisioning is '
            'not supported on zesty',
            process.stderr)

    def test_unsupported_on_i686(self):
        """CC is unsupported on i686 arch."""
        self.ARCH = 'i686'
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(7, process.returncode)
        self.assertIn(
            'Sorry, but Canonical Common Criteria EAL2 Provisioning '
            'is not supported on i686',
            process.stderr)

    def test_unsupported_on_arm64(self):
        """CC is unsupported on arm64 arch."""
        self.ARCH = 'arm64'
        process = self.script('enable-cc-provisioning', 'user:pass')
        self.assertEqual(7, process.returncode)
        self.assertIn(
            'Sorry, but Canonical Common Criteria EAL2 Provisioning '
            'is not supported on arm64',
            process.stderr)

    def test_disable_cc_provisioning(self):
        """The disable-cc-provisioning option disables commoncriteria repo."""
        self.setup_cc(enabled=True)
        other_auth = 'machine example.com login user password pass\n'
        self.apt_auth_file.write_text(other_auth)
        process = self.script('disable-cc-provisioning')
        self.assertEqual(0, process.returncode)
        self.assertFalse(self.cc_repo_list.exists())
        # the keyring file is removed
        keyring_file = self.trusted_gpg_dir / 'ubuntu-cc-keyring.gpg'
        self.assertFalse(keyring_file.exists())
        # credentials are removed
        self.assertEqual(self.apt_auth_file.read_text(), other_auth)

    def test_disable_cc_provisioning_fails_already_disabled(self):
        """If commoncriteria repo is not enabled, disable fails."""
        process = self.script('disable-cc-provisioning')
        self.assertEqual(8, process.returncode)
        self.assertIn(
            'Canonical Common Criteria EAL2 Provisioning is not enabled\n',
            process.stderr)
