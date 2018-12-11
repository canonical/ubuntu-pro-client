import os
import platform

from uaclient import apt
from uaclient.entitlements import base
from uaclient import status
from uaclient import util


class RepoEntitlement(base.UAEntitlement):

    repo_list_file_tmpl = '/etc/apt/sources.list.d/ubuntu-{name}-{series}.list'
    # TODO(Get repo_url from Contract service's Entitlements response)
    # https://github.com/CanonicalLtd/ua-service/issues/7
    # Set by subclasses
    repo_url = 'UNSET'
    repo_key_file = 'UNSET'  # keyfile delivered by ubuntu-cloudimage-keyring

    def enable(self):
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        """
        if not self.can_enable():
            return False
        series = platform.dist()[2]
        repo_filename = self.repo_list_file_tmpl.format(
            name=self.name, series=series)
        keyring_file = os.path.join(apt.KEYRINGS_DIR, self.repo_key_file)
        # TODO(Get credentials from Contract service's Entitlements response)
        credentials = 'user{name}:pass'.format(name=self.name)
        apt.add_auth_apt_repo(
            repo_filename, self.repo_url, credentials, keyring_file)
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            util.subp(['apt-get', 'install', 'apt-transport-https'])
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            util.subp(['apt-get', 'install', 'ca-certificates'])
        util.subp(['apt-get', 'update'])
        print(status.MESSAGE_ENABLED_TMPL.format(title=self.title))
        return True

    def operational_status(self):
        """Return operational status of RepoEntitlement."""
        apt_policy = util.subp(['apt-cache', 'policy'])
        if ' %s ' % self.repo_url in apt_policy:
            return status.ACTIVE
        return status.INACTIVE
