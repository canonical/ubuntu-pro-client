"""Tests for the Livepatch MOTD"""

from testing import UbuntuAdvantageTest
from fakes import (
    LIVEPATCH_ENABLED_STATUS,
    LIVEPATCH_CHECKED_UNAPPLIED,
    LIVEPATCH_CHECKED_APPLIED_WITH_BUG,
    LIVEPATCH_CHECKED_NOTHING_TO_APPLY,
    LIVEPATCH_CHECKED_APPLY_FAILED,
    LIVEPATCH_CHECKED_APPLYING,
    LIVEPATCH_NEEDS_CHECK,
    LIVEPATCH_CHECK_FAILED,
    UA_STATE_ELSEWHERE)
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
        self.ua_no_livepatch = str(self.bin_dir / 'ua-no-livepatch')
        self.make_fake_binary(
            'ua-no-livepatch',
            command='echo -e esm: disabled\nfips: disabled\n')
        self.ua_state_elsewhere = str(self.bin_dir / 'ua-state-elsewhere')
        self.make_fake_binary(
            'ua-state-elsewhere',
            command=UA_STATE_ELSEWHERE)

    def test_no_livepatch_content_in_status(self):
        """motd displays unknown check state if livepatch section is empty."""
        self.setup_livepatch(installed=True, enabled=True,
                             livepatch_command="exit 0")
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['check-state-unknown']:
            self.assertIn(line.format(""), process.stdout)

    def test_disabled_but_available(self):
        """Livepatch is disabled but available for installation."""
        self.setup_livepatch(installed=True, enabled=False)
        process = self.script()
        self.assertEqual(0, process.returncode)
        self.assertIn('Canonical Livepatch is available for installation',
                      process.stdout)
        self.assertIn('Reduce system reboots and improve kernel security. '
                      'Activate at:\n     https://ubuntu.com/livepatch',
                      process.stdout)

    def test_disabled_unavailable(self):
        """Livepatch is disabled and not available."""
        self.SERIES = 'precise'
        self.setup_livepatch(installed=False, enabled=False)
        process = self.script()
        self.assertEqual(0, process.returncode)
        self.assertEqual('', process.stdout)

    def test_other_state_fields_ignored(self):
        """The MOTD script ignores *State fields not from livepatch."""
        env_update = {"UA": self.ua_state_elsewhere}
        process = self.script(env_update=env_update)
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applied']:
            self.assertIn(line, process.stdout)
        # make sure the bad fields were actually there and this test is
        # valid
        self.SCRIPT = self.ua_state_elsewhere
        ua_status = self.script()
        self.assertIn('should-not-be-here', ua_status.stdout)

    def test_ua_script_without_livepatch(self):
        """MOTD is empty if there is no livepatch section in ua's output."""
        env_update = {"UA": self.ua_no_livepatch}
        process = self.script(env_update=env_update)
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
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECKED_UNAPPLIED)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['unapplied']:
            self.assertIn(line, process.stdout)

    def test_checked_applied_with_bug(self):
        """checkState is checked, patchState is applied-with-bug."""
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECKED_APPLIED_WITH_BUG)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applied-with-bug']:
            self.assertIn(line, process.stdout)

    def test_checked_nothing_to_apply(self):
        """checkState is checked, patchState is nothing-to-apply."""
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECKED_NOTHING_TO_APPLY)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['nothing-to-apply']:
            self.assertIn(line, process.stdout)

    def test_checked_apply_failed(self):
        """checkState is checked, patchState is apply-failed."""
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECKED_APPLY_FAILED)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['apply-failed']:
            self.assertIn(line, process.stdout)

    def test_checked_applying(self):
        """checkState is checked, patchState is applying."""
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECKED_APPLYING)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['checked']['applying']:
            self.assertIn(line, process.stdout)

    def test_needs_check(self):
        """checkState is needs-check."""
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_NEEDS_CHECK)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['needs-check']:
            self.assertIn(line, process.stdout)

    def test_check_failed(self):
        """checkState is check-failed."""
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=LIVEPATCH_CHECK_FAILED)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['check-failed']:
            self.assertIn(line, process.stdout)

    def test_check_unknown_state(self):
        """checkState is something unexpected."""
        random_state = 'check-state-{}'.format(randrange(99999))
        command = LIVEPATCH_ENABLED_STATUS.format(
            check_state=random_state, patch_state='foo')
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=command)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['check-state-unknown']:
            self.assertIn(line.format(random_state), process.stdout)

    def test_patch_unknown_state(self):
        """patchState is something unexpected."""
        random_state = 'patch-state-{}'.format(randrange(99999))
        command = LIVEPATCH_ENABLED_STATUS.format(
            check_state='checked', patch_state=random_state)
        self.setup_livepatch(
            installed=True, enabled=True,
            livepatch_command=command)
        process = self.script()
        self.assertEqual(0, process.returncode)
        for line in LIVEPATCH_STATE_MESSAGES['patch-state-unknown']:
            self.assertIn(line.format(random_state), process.stdout)
