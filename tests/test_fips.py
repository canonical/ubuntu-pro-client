# Tests for FIPS-related commands.

from testing import UbuntuAdvantageTest


class FIPSTest(UbuntuAdvantageTest):

    SERIES = 'xenial'
    ARCH = 'x86_64'

    def setUp(self):
        super().setUp()
        self.cpuinfo.write_text('flags\t\t: fpu aes apic')

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
        self.assertIn(
            'Successfully configured FIPS. Please reboot into the FIPS kernel'
            ' to enable it.',
            process.stdout)
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
        self.assertEqual('FIPS is already enabled.', process.stderr.strip())

    def test_enable_fips_installed_not_enabled(self):
        """If fips is installed but not enabled an error is returned."""
        self.make_fake_binary('dpkg-query')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertEqual(
            'FIPS is already installed. '
            'Please reboot into the FIPS kernel to enable it.',
            process.stderr.strip())

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

    def test_unsupported_on_i686(self):
        """FIPS is unsupported on i686 arch."""
        self.ARCH = 'i686'
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertEqual(
            'FIPS is not supported on i686.', process.stderr.strip())

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

    def test_enable_fips_x86_64_aes_not_available(self):
        """The enable-fips command fails if AESNI is not available."""
        self.cpuinfo.write_text('flags\t\t: fpu tsc')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertEqual(
            'FIPS requires AES CPU extensions', process.stderr.strip())

    def test_enable_fips_ppc64le_power8(self):
        """POWER8 processors are supported by FIPS."""
        self.ARCH = 'ppc64le'
        self.cpuinfo.write_text('cpu\t\t: POWER8 (raw), altivec supported')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Successfully configured FIPS', process.stdout)

    def test_enable_fips_ppc64le_older_power(self):
        """processors older than POWER8 are not supported by FIPS."""
        self.ARCH = 'ppc64le'
        self.cpuinfo.write_text('cpu\t\t: POWER7')
        process = self.script('enable-fips', 'user:pass')
        self.assertEqual(6, process.returncode)
        self.assertEqual(
            'FIPS requires POWER8 or later', process.stderr.strip())

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

    def test_fips_cannot_be_disabled_if_enabled(self):
        """disable-fips says FIPS cannot be deactivated if it's enabled"""
        self.make_fake_binary('dpkg-query')
        p = self.fips_enabled_file
        p.write_text('1')
        process = self.script('disable-fips')
        self.assertEqual(1, process.returncode)
        self.assertEqual(
            'Disabling FIPS is currently not supported.',
            process.stderr.strip())

    def test_disable_fips_warns_if_not_enabled(self):
        """disable-fips will warn if FIPS is not enabled"""
        self.make_fake_binary('dpkg-query')
        p = self.fips_enabled_file
        p.write_text('0')
        process = self.script('disable-fips')
        self.assertEqual(1, process.returncode)
        self.assertEqual(
            'FIPS is not enabled.', process.stderr.strip())
