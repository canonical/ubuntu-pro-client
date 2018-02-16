"""Tests for the Livepatch MOTD"""

from testing import UbuntuAdvantageTest
from fakes import (
    LIVEPATCH_ENABLED_STATUS,
    LIVEPATCH_CHECKED_UNAPPLIED,
    STATUS_CACHE_LIVEPATCH_ENABLED,
    STATUS_CACHE_NO_LIVEPATCH,
    STATUS_CACHE_LIVEPATCH_ENABLED_NO_CONTENT,
    STATUS_CACHE_LIVEPATCH_DISABLED_AVAILABLE,
    STATUS_CACHE_LIVEPATCH_DISABLED_UNAVAILABLE,
    STATUS_CACHE_MIXED_CONTENT)
from random import randrange

LIVEPATCH_IS_ENABLED = 'Canonical Livepatch is enabled.'
LIVEPATCH_STATE_MESSAGES = {
    'checked': {
        'applied': [
            LIVEPATCH_IS_ENABLED,
            'All available patches applied.'],
        'unapplied': [
            LIVEPATCH_IS_ENABLED,
            'Patches are available, will be deployed shortly.'],
        'applied-with-bug': [
            LIVEPATCH_IS_ENABLED,
            'Live patching failed, please run `ubuntu-bug linux` to '
            'report a bug.'],
        'nothing-to-apply': [
            LIVEPATCH_IS_ENABLED,
            'All available patches applied.'],
        'apply-failed': [
            LIVEPATCH_IS_ENABLED,
            'Live patching failed, please run `ubuntu-bug linux` to '
            'report a bug.'],
        'applying': [
            LIVEPATCH_IS_ENABLED,
            'Live patching currently in progress.']
        },
    'needs-check': [
        LIVEPATCH_IS_ENABLED, 'Regular server check is pending.'],
    'check-failed': [
        LIVEPATCH_IS_ENABLED,
        'Livepatch server check failed.',
        'Please see /var/log/syslog for more information.'],
    'check-state-unknown': [
        LIVEPATCH_IS_ENABLED,
        'Unknown check status. Please see /var/log/syslog for more '
        'information.',
        'Status: "{}"'],
    'patch-state-unknown': [
        LIVEPATCH_IS_ENABLED,
        'Unknown patch status. Please see /var/log/syslog for more '
        'information.', 'Status: "{}"'],
}


class LivepatchMOTDTest(UbuntuAdvantageTest):

    SERIES = 'trusty'
    ARCH = 'x86_64'
    KERNEL_VERSION = '4.4.0-89-generic'
    SCRIPT = 'update-motd.d/99-livepatch'

    def setUp(self):
        super().setUp()
        self.setup_livepatch(installed=True, enabled=True)
        self.livepatch_token = '0123456789abcdef1234567890abcdef'
        self.ua_status_cache.write_text(
            STATUS_CACHE_LIVEPATCH_ENABLED.format(check_state="checked",
                                                  patch_state="applied"))

    def test_no_livepatch_content_in_status(self):
        """motd displays unknown check state if livepatch section is empty."""
        self.ua_status_cache.write_text(
            STATUS_CACHE_LIVEPATCH_ENABLED_NO_CONTENT)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['check-state-unknown']:
            self.assertIn(line.format(""), process.stdout)

    def test_disabled_but_available(self):
        """Livepatch is disabled but available for installation."""
        self.ua_status_cache.write_text(
            STATUS_CACHE_LIVEPATCH_DISABLED_AVAILABLE)
        process = self.script()
        self.assertEqual(0, process.returncode)
        self.assertIn('Canonical Livepatch is available for installation',
                      process.stdout)
        self.assertIn('Reduce system reboots and improve kernel security. '
                      'Activate at:\n     https://ubuntu.com/livepatch',
                      process.stdout)

    def test_disabled_unavailable(self):
        """Livepatch is disabled and not available."""
        self.ua_status_cache.write_text(
            STATUS_CACHE_LIVEPATCH_DISABLED_UNAVAILABLE)
        process = self.script()
        self.assertEqual(0, process.returncode)
        self.assertEqual('', process.stdout)

    def test_other_state_fields_ignored(self):
        """The MOTD script ignores *State fields not from livepatch."""
        self.ua_status_cache.write_text(STATUS_CACHE_MIXED_CONTENT)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applied']:
            self.assertIn(line, process.stdout)
        self.assertNotIn('should-not-be-here', process.stdout)

    def test_ua_script_without_livepatch(self):
        """MOTD is empty if there is no livepatch section in ua's output."""
        self.ua_status_cache.write_text(STATUS_CACHE_NO_LIVEPATCH)
        process = self.script()
        self.assertEqual(0, process.returncode)
        self.assertEqual('', process.stdout)

    def test_ua_script_not_installed(self):
        """MOTD is empty if there is no ubuntu-advantage script."""
        env_update = {"UA": "/does/not/exist"}
        process = self.script(env_update=env_update)
        self.assertEqual(0, process.returncode)
        self.assertEqual('', process.stdout)

    def test_checked_applied(self):
        """All applicable patches applied."""
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applied']:
            self.assertIn(line, process.stdout)

    def test_checked_unapplied(self):
        """checkState is checked, patchState is unapplied."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state='unapplied'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['unapplied']:
            self.assertIn(line, process.stdout)

    def test_checked_applied_with_bug(self):
        """checkState is checked, patchState is applied-with-bug."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state='applied-with-bug'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applied-with-bug']:
            self.assertIn(line, process.stdout)

    def test_checked_nothing_to_apply(self):
        """checkState is checked, patchState is nothing-to-apply."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state='nothing-to-apply'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['nothing-to-apply']:
            self.assertIn(line, process.stdout)

    def test_checked_apply_failed(self):
        """checkState is checked, patchState is apply-failed."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state='apply-failed'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['apply-failed']:
            self.assertIn(line, process.stdout)

    def test_checked_applying(self):
        """checkState is checked, patchState is applying."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state='applying'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applying']:
            self.assertIn(line, process.stdout)

    def test_needs_check(self):
        """checkState is needs-check."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='needs-check', patch_state='irrelevant'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['needs-check']:
            self.assertIn(line, process.stdout)

    def test_check_failed(self):
        """checkState is check-failed."""
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='check-failed', patch_state='irrelevant'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['check-failed']:
            self.assertIn(line, process.stdout)

    def test_check_unknown_state(self):
        """checkState is something unexpected."""
        random_state = 'check-state-{}'.format(randrange(99999))
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state=random_state, patch_state='irrelevant'))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['check-state-unknown']:
            self.assertIn(line.format(random_state), process.stdout)

    def test_patch_unknown_state(self):
        """patchState is something unexpected."""
        random_state = 'patch-state-{}'.format(randrange(99999))
        self.ua_status_cache.write_text(STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state=random_state))
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['patch-state-unknown']:
            self.assertIn(line.format(random_state), process.stdout)

    def test_script_uses_cached_status(self):
        """The script uses the cached status when it exists."""
        random_state = 'patch-state-{}'.format(randrange(99999))
        ua_status_cache = STATUS_CACHE_LIVEPATCH_ENABLED.format(
            check_state='checked', patch_state=random_state)
        self.ua_status_cache.write_text(ua_status_cache)
        # setup the livepatch command to show a status different from
        # the cache
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECKED_UNAPPLIED)
        process = self.script()
        self.assertEqual(0, process.returncode)
        # this confirms the cached data was used
        for line in LIVEPATCH_STATE_MESSAGES['patch-state-unknown']:
            self.assertIn(line.format(random_state), process.stdout)
        # this confirms that LIVEPATCH_CHECKED_UNAPPLIED was not used
        for line in LIVEPATCH_STATE_MESSAGES['checked']['unapplied'][1:]:
            self.assertNotIn(line, process.stdout)
        # this confirms the cached file did not change after the script ran
        self.assertEqual(ua_status_cache.format(random_state),
                         self.ua_status_cache.read_text())

    def test_script_exits_if_no_cache(self):
        """The motd exits silently if the cache file does not exist."""
        self.ua_status_cache.unlink()
        random_state = 'patch-state-{}'.format(randrange(99999))
        command = LIVEPATCH_ENABLED_STATUS.format(
            check_state='checked', patch_state=random_state)
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=command)
        process = self.script()
        self.assertEqual(0, process.returncode)
        self.assertEqual('', process.stdout)
        # the cache file is not created by the script
        self.assertEqual(False, self.ua_status_cache.is_file())

    def test_empty_status_cache_is_ignored(self):
        """The motd exits silently if the cache file is empty."""
        self.ua_status_cache.write_text('')
        random_state = 'patch-state-{}'.format(randrange(99999))
        command = LIVEPATCH_ENABLED_STATUS.format(
            check_state='checked', patch_state=random_state)
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=command)
        process = self.script()
        self.assertEqual(0, process.returncode)
        # cache is not updated and is still empty
        self.assertEqual('', self.ua_status_cache.read_text())
        # motd output is empty
        self.assertEqual('', process.stdout)
