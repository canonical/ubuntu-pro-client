import abc
import logging
import os
import re

try:
    from typing import (  # noqa: F401
        Any, cast, Dict, List, Optional, Tuple, Union)
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    def cast(_, x):  # type: ignore
        return x


from uaclient import apt
from uaclient.entitlements import base
from uaclient import status
from uaclient import util
from uaclient.status import ApplicationStatus

APT_DISABLED_PIN = '-32768'
# charm-helpers uses 10 seconds between retries. Hope for an optimal first try
APT_RETRIES = [1.0, 10.0, 10.0]


class RepoEntitlement(base.UAEntitlement):

    repo_list_file_tmpl = '/etc/apt/sources.list.d/ubuntu-{name}-{series}.list'
    repo_pref_file_tmpl = '/etc/apt/preferences.d/ubuntu-{name}-{series}'

    # The repo Origin value for setting pinning
    origin = None  # type: Optional[str]

    # Optional repo pin priority in subclass
    repo_pin_priority = None  # type: Union[int, str, None]

    # disable_apt_auth_only (ESM) to only remove apt auth files on disable
    disable_apt_auth_only = False  # Set True on ESM to only remove apt auth

    # Any custom messages to emit pre or post enable or disable operations;
    # currently post_enable is used in CommonCriteria
    messaging = {}  # type: Dict[str, List[str]]

    @property
    def packages(self) -> 'List[str]':
        """debs to install on enablement"""
        return []

    @property
    @abc.abstractmethod
    def repo_url(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def repo_key_file(self) -> str:
        pass

    def enable(self, *, silent_if_inapplicable: bool = False) -> bool:
        """Enable specific entitlement.

        :param silent_if_inapplicable:
            Don't emit any messages until after it has been determined that
            this entitlement is applicable to the current machine.

        @return: True on success, False otherwise.
        """
        if not self.can_enable(silent=silent_if_inapplicable):
            return False
        if not self.setup_apt_config():
            return False
        if self.packages:
            try:
                print(
                    'Installing {title} packages'.format(title=self.title))
                for msg in self.messaging.get('pre_install', []):
                    print(msg)
                util.subp(
                    ['apt-get', 'install', '--assume-yes'] + self.packages,
                    capture=True, retry_sleeps=APT_RETRIES)
            except util.ProcessExecutionError:
                self.disable(silent=True, force=True)
                logging.error(
                    status.MESSAGE_ENABLED_FAILED_TMPL.format(
                        title=self.title))
                return False
        print(status.MESSAGE_ENABLED_TMPL.format(title=self.title))
        for msg in self.messaging.get('post_enable', []):
            print(msg)
        return True

    def disable(self, silent=False, force=False):
        if not self.can_disable(silent, force):
            return False
        self.remove_apt_config()
        try:
            util.subp(
                ['apt-get', 'remove', '--assume-yes'] + self.packages)
        except util.ProcessExecutionError:
            pass
        if not silent:
            print(status.MESSAGE_DISABLED_TMPL.format(title=self.title))
        return True

    def application_status(self) -> 'Tuple[ApplicationStatus, str]':
        entitlement_cfg = self.cfg.entitlements.get(self.name, {})
        directives = entitlement_cfg.get(
            'entitlement', {}).get('directives', {})
        repo_url = directives.get('aptURL')
        if not repo_url:
            repo_url = self.repo_url
        protocol, repo_path = repo_url.split('://')
        out, _err = util.subp(['apt-cache', 'policy'])
        match = re.search(r'(?P<pin>(-)?\d+) %s' % repo_url, out)
        if match and match.group('pin') != APT_DISABLED_PIN:
            return ApplicationStatus.ENABLED, '%s is active' % self.title
        return ApplicationStatus.DISABLED, '%s is not configured' % self.title

    def process_contract_deltas(
            self, orig_access: 'Dict[str, Any]',
            deltas: 'Dict[str, Any]', allow_enable: bool = False) -> bool:
        """Process any contract access deltas for this entitlement.

        :param orig_access: Dictionary containing the original
            resourceEntitlement access details.
        :param deltas: Dictionary which contains only the changed access keys
        and values.
        :param allow_enable: Boolean set True if allowed to perform the enable
            operation. When False, a message will be logged to inform the user
            about the recommended enabled service.

        :return: True when delta operations are processed; False when noop.
        """
        if super().process_contract_deltas(orig_access, deltas, allow_enable):
            return True  # Already processed parent class deltas

        application_status, _ = self.application_status()
        if application_status == status.ApplicationStatus.DISABLED:
            return True
        logging.info(
            "Updating '%s' apt sources list on changed directives." %
            self.name)
        delta_entitlement = deltas.get('entitlement', {})
        if delta_entitlement.get('directives', {}).get('aptURL'):
            orig_entitlement = orig_access.get('entitlement', {})
            old_url = orig_entitlement.get('directives', {}).get('aptURL')
            if old_url:
                # Remove original aptURL and auth and rewrite
                series = util.get_platform_info()['series']
                repo_filename = self.repo_list_file_tmpl.format(
                    name=self.name, series=series)
                apt.remove_auth_apt_repo(repo_filename, old_url)
        self.remove_apt_config()
        self.setup_apt_config()
        return True

    def setup_apt_config(self):
        series = util.get_platform_info()['series']
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        resource_cfg = self.cfg.entitlements.get(self.name)
        directives = resource_cfg['entitlement'].get('directives', {})
        token = resource_cfg.get('resourceToken')
        if not token:
            logging.debug(
                'No specific resourceToken present. Using machine token'
                ' as %s credentials', self.title)
            token = self.cfg.machine_token['machineToken']
        if directives.get('aptKey'):
            logging.debug(
                "Ignoring aptKey directive '%s'", directives.get('aptKey'))
        keyring_file = os.path.join(apt.KEYRINGS_DIR, self.repo_key_file)
        repo_url = directives.get('aptURL')
        if not repo_url:
            repo_url = self.repo_url
        repo_suites = directives.get('suites')
        if not repo_suites:
            logging.error(
                'Empty %s apt suites directive from %s',
                self.name, self.cfg.contract_url)
            return False
        if self.repo_pin_priority:
            if not self.origin:
                logging.error(
                    "Cannot setup apt pin. Empty apt repo origin value '%s'." %
                    self.origin)
                logging.error(
                    status.MESSAGE_ENABLED_FAILED_TMPL.format(
                        title=self.title))
                return False
            repo_pref_file = self.repo_pref_file_tmpl.format(
                name=self.name, series=series)
            if self.repo_pin_priority != 'never':
                apt.add_ppa_pinning(
                    repo_pref_file, repo_url, self.origin,
                    self.repo_pin_priority)
            elif os.path.exists(repo_pref_file):
                os.unlink(repo_pref_file)  # Remove disabling apt pref file

        prerequisite_pkgs = []
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            prerequisite_pkgs.append('apt-transport-https')
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            prerequisite_pkgs.append('ca-certificates')

        if prerequisite_pkgs:
            print('Installing prerequisites: {}'.format(
                ', '.join(prerequisite_pkgs)))
            try:
                util.subp(
                    ['apt-get', 'install', '--assume-yes'] + prerequisite_pkgs,
                    capture=True, retry_sleeps=APT_RETRIES)
            except util.ProcessExecutionError as e:
                logging.error(str(e))
                return False
        try:
            apt.add_auth_apt_repo(
                repo_filename, repo_url, token, repo_suites,
                keyring_file)
        except apt.InvalidAPTCredentialsError as e:
            logging.error(str(e))
            return False
        # Run apt-update on any repo-entitlement enable because the machine
        # probably wants access to the repo that was just enabled.
        # Side-effect is that apt policy will new report the repo as accessible
        # which allows ua status to report correct info
        print('Updating package lists')
        util.subp(
            ['apt-get', 'update'], capture=True, retry_sleeps=APT_RETRIES)
        return True

    def remove_apt_config(self):
        """Remove any repository apt configuration files."""
        series = util.get_platform_info()['series']
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        keyring_file = os.path.join(apt.APT_KEYS_DIR, self.repo_key_file)
        entitlement = self.cfg.read_cache(
            'machine-access-%s' % self.name).get('entitlement', {})
        access_directives = entitlement.get('directives', {})
        repo_url = access_directives.get('aptURL', self.repo_url)
        if not repo_url:
            repo_url = self.repo_url
        if self.disable_apt_auth_only:
            # We only remove the repo from the apt auth file, because ESM
            # is a special-case: we want to be able to report on the
            # available ESM updates even when it's disabled
            apt.remove_repo_from_apt_auth_file(repo_url)
            apt.restore_commented_apt_list_file(repo_filename)
        else:
            apt.remove_auth_apt_repo(repo_filename, repo_url, keyring_file)
            apt.remove_apt_list_files(repo_url, series)
        if self.repo_pin_priority:
            repo_pref_file = self.repo_pref_file_tmpl.format(
                name=self.name, series=series)
            if self.repo_pin_priority == 'never':
                # Disable the repo with a pinning file
                apt.add_ppa_pinning(
                    repo_pref_file, repo_url, self.origin,
                    self.repo_pin_priority)
            elif os.path.exists(repo_pref_file):
                os.unlink(repo_pref_file)
