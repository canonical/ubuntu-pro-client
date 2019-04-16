# Tests for ESM-related commands.

from testing import UbuntuAdvantageTest
from fakes import APT_GET_LOG_WRAPPER


class ESMTest(UbuntuAdvantageTest):

    SERIES = 'precise'

    def test_enable_esm_precise(self):
        """The enable-esm option enables the ESM repository on p."""
        self.SERIES = 'precise'
        expected_repo_list = (
            'deb https://user:pass@esm.ubuntu.com/ubuntu precise main\n'
            '# deb-src https://user:pass@esm.ubuntu.com/ubuntu precise main\n')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository enabled', process.stdout)
        self.assertEqual(expected_repo_list, self.repo_list.read_text())
        keyring_file = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        self.assertEqual('GPG key', keyring_file.read_text())
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
             process.stdout)

    def test_enable_esm_trusty(self):
        """The enable-esm option enables the ESM repository on t."""
        self.SERIES = 'trusty'
        expected_repo_list = (
            'deb https://user:pass@esm.ubuntu.com/ubuntu '
            'trusty-security main\n'
            '# deb-src https://user:pass@esm.ubuntu.com/ubuntu '
            'trusty-security main\n'
            '\n'
            'deb https://user:pass@esm.ubuntu.com/ubuntu '
            'trusty-updates main\n'
            '# deb-src https://user:pass@esm.ubuntu.com/ubuntu '
            'trusty-updates main\n')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository enabled', process.stdout)
        self.assertEqual(expected_repo_list, self.repo_list.read_text())
        keyring_file = self.trusted_gpg_dir / 'ubuntu-trusty-esm-keyring.gpg'
        self.assertEqual('GPG key trusty', keyring_file.read_text())
        # the apt-transport-https dependency is already installed
        self.assertNotIn(
            'Installing missing dependency apt-transport-https',
             process.stdout)

    def test_enable_esm_install_apt_transport_https(self):
        """enable-esm installs apt-transport-https if needed."""
        self.apt_method_https.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency apt-transport-https',
            process.stdout)

    def test_enable_esm_install_apt_transport_https_apt_get_options(self):
        """apt-get accepts defaults when installing apt-transports-https."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command=APT_GET_LOG_WRAPPER)
        self.script('enable-esm', 'user:pass')
        # apt-get is called both to install packages and update lists
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold install '
            'apt-transport-https',
            self.read_file('apt_get.args'))
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold update',
            self.read_file('apt_get.args'))
        self.assertIn(
            'DEBIAN_FRONTEND=noninteractive', self.read_file('apt_get.env'))

    def test_enable_esm_install_apt_transport_https_fails(self):
        """Stderr is printed if apt-transport-https install fails."""
        self.apt_method_https.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_esm_install_ca_certificates(self):
        """enable-esm installs ca-certificates if needed."""
        self.ca_certificates.unlink()
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(0, process.returncode)
        self.assertIn(
            'Installing missing dependency ca-certificates',
            process.stdout)

    def test_enable_esm_install_ca_certificates_apt_get_options(self):
        """apt-get accepts defaults when installing ca-certificates."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command=APT_GET_LOG_WRAPPER)
        self.script('enable-esm', 'user:pass')
        # apt-get is called both to install packages and update lists
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold install ca-certificates',
            self.read_file('apt_get.args'))
        self.assertIn(
            '-y -o Dpkg::Options::=--force-confold update',
            self.read_file('apt_get.args'))
        self.assertIn(
            'DEBIAN_FRONTEND=noninteractive', self.read_file('apt_get.env'))

    def test_enable_esm_install_ca_certificates_fails(self):
        """Stderr is printed if ca-certificates install fails."""
        self.ca_certificates.unlink()
        self.make_fake_binary('apt-get', command='echo failed >&2; false')
        process = self.script('enable-esm', 'user:pass')
        self.assertEqual(1, process.returncode)
        self.assertIn('failed', process.stderr)

    def test_enable_esm_missing_token(self):
        """The token must be specified when using enable-esm."""
        process = self.script('enable-esm')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_esm_invalid_token(self):
        """The ESM token must be specified as "user:password"."""
        process = self.script('enable-esm', 'foo-bar')
        self.assertEqual(3, process.returncode)
        self.assertIn(
            'Invalid token, it must be in the form "user:password"',
            process.stderr)

    def test_enable_esm_fails_on_x_b_c_d(self):
        """The enable-esm option fails on X, B, C, D."""
        for series in ['xenial', 'bionic', 'cosmic', 'disco']:
            self.SERIES = series
            process = self.script('enable-esm', 'user:pass')
            self.assertEqual(4, process.returncode)
            self.assertIn(
                'Extended Security Maintenance is not supported on '
                '{}'.format(series), process.stderr)

    def test_disable_esm(self):
        """The disable-esm option disables the ESM repository."""
        self.script('enable-esm', 'user:pass')
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository disabled', process.stdout)
        self.assertFalse(self.repo_list.exists())
        # the keyring files are removed
        keyring_file_precise = self.trusted_gpg_dir / 'ubuntu-esm-keyring.gpg'
        keyring_file_trusty = (
            self.trusted_gpg_dir / 'ubuntu-trusty-esm-keyring.gpg')
        self.assertFalse(keyring_file_precise.exists())
        self.assertFalse(keyring_file_trusty.exists())

    def test_disable_esm_disabled(self):
        """If the ESM repo is not enabled, disable-esm is a no-op."""
        process = self.script('disable-esm')
        self.assertEqual(0, process.returncode)
        self.assertIn('Ubuntu ESM repository was not enabled', process.stdout)

    def test_disable_esm_only_supported_on_precise(self):
        """The disable-esm option fails if not on Precise."""
        self.SERIES = 'xenial'
        process = self.script('disable-esm')
        self.assertEqual(4, process.returncode)
        self.assertIn(
            'Extended Security Maintenance is not supported on xenial',
            process.stderr)

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
