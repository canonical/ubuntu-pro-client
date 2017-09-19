# Tests for FIPS-related commands.

from testing import UbuntuAdvantageTest


class FIPSTest(UbuntuAdvantageTest):

    SERIES = 'xenial'

    def test_enable_fips(self):
        """The enable-fips option enables the FIPS repository."""
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu FIPS PPA repository enabled.', process.stdout)
        expected = (
            'deb https://user:pass@private-ppa.launchpad.net/ubuntu-advantage/'
            'fips/ubuntu xenial main\n'
            '# deb-src https://user:pass@private-ppa.launchpad.net/'
            'ubuntu-advantage/fips/ubuntu xenial main\n')
        self.assertEqual(expected, self.repo_list.read_text())
        keyring_file = self.trusted_gpg_dir / 'ubuntu-fips-keyring.gpg'
        self.assertEqual('GPG key', keyring_file.read_text())
        self.assertIn('Successfully configured FIPS. PLEASE REBOOT '
                      'to complete FIPS enablement.', process.stdout)
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_fips_already_enabled(self):
        """If fips is already enabled, an error is returned."""
        self.make_fake_binary('dpkg-query')
        p = self.fips_enabled_file
        p.write_text('1')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertEqual(
            'FIPS is already enabled.', process.stdout.strip())

    def test_enable_fips_installed_not_enabled(self):
        """If fips is installed but not enabled an error is returned."""
        self.make_fake_binary('dpkg-query')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertEqual(
            'FIPS is already installed. '
            'Please reboot into the FIPS kernel to enable it.',
            process.stdout.strip())

    def test_enable_fips_writes_config(self):
        """The enable-fips option writes fips configuration."""
        self.script('enable-fips', 'user:pass')
        self.assertEqual(
            'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT fips=1"',
            self.boot_cfg.read_text().strip())

    def test_enable_fips_writes_config_with_boot_partition(self):
        """The fips configuration includes the /boot partition."""
        self.fstab.write_text('/dev/sda1 /boot ext2 defaults 0 1\n')
        self.script('enable-fips', 'user:pass')
        self.assertIn('bootdev=/dev/sda1', self.boot_cfg.read_text())

    def test_enable_fips_writes_config_s390x_parameters(self):
        """On S390x, FIPS parameters are appended to the config file."""
        self.ARCH = 's390x'
        self.boot_cfg.write_text('parameters=foo\n')
        self.script('enable-fips', 'user:pass')
        self.assertEqual('parameters=foo fips=1\n', self.boot_cfg.read_text())

    def test_enable_fips_install_apt_transport_https(self):
        """enable-fips installs apt-transport-https if needed."""
        self.apt_method_https.unlink()
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_fips_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_fips_install_ca_certificates(self):
        """enable-fips installs ca-certificates if needed."""
        self.ca_certificates.unlink()
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency ca-certificates',
            process.stdout)

    def test_enable_fips_install_ca_certificates_fails(self):
        """Stderr is printed if ca-certificates install fails."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_fips_missing_token(self):
        """The token must be specified when using enable-fips."""
        process = self.script('enable-fips')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_fips_invalid_token(self):
        """The FIPS token must be specified as "user:password"."""
        process = self.script('enable-fips', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_fips_only_supported_on_xenial(self):
        """The enable-fips option fails if not on Xenial."""
        self.SERIES = 'zesty'
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Canonical FIPS 140-2 Modules is not supported on zesty',
            process.stderr)

    def test_is_fips_enabled_true(self):
        """is-fips-enabled returns 0 if fips is enabled."""
        self.make_fake_binary('dpkg-query')
        p = self.fips_enabled_file
        p.write_text('1')
        process = self.script('is-fips-enabled')
        self.assertEqual(0, process.returncode)

    def test_is_fips_enabled_false(self):
        """is-fips-enabled returns 1 if fips is not enabled."""
        self.make_fake_binary('dpkg-query')
        p = self.fips_enabled_file
        p.write_text('0')
        process = self.script('is-fips-enabled')
        self.assertEqual(1, process.returncode)
