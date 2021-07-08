import abc
import copy
import logging
import os
import re

from uaclient import contract

try:
    from typing import (  # noqa: F401
        Any,
        Callable,
        Dict,
        List,
        Optional,
        Sequence,
        Tuple,
        Union,
    )
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


from uaclient import apt
from uaclient import exceptions
from uaclient.entitlements import base
from uaclient import status
from uaclient import util
from uaclient.status import ApplicationStatus

APT_DISABLED_PIN = "-32768"


class RepoEntitlement(base.UAEntitlement):

    repo_list_file_tmpl = "/etc/apt/sources.list.d/ubuntu-{name}.list"
    repo_pref_file_tmpl = "/etc/apt/preferences.d/ubuntu-{name}"

    # The repo Origin value for setting pinning
    origin = None  # type: Optional[str]

    # GH: #1084 call apt in noninteractive mode
    apt_noninteractive = False

    # Optional repo pin priority in subclass
    @property
    def repo_pin_priority(self) -> "Union[int, str, None]":
        return None

    # disable_apt_auth_only (ESM) to only remove apt auth files on disable
    @property
    def disable_apt_auth_only(self) -> bool:
        return False  # Set True on ESM to only remove apt auth

    @property
    def packages(self) -> "List[str]":
        """debs to install on enablement"""
        packages = []

        entitlement = self.cfg.entitlements.get(self.name, {}).get(
            "entitlement", {}
        )

        if entitlement:
            directives = entitlement.get("directives", {})
            additional_packages = copy.copy(
                directives.get("additionalPackages", [])
            )

            packages = additional_packages

        return packages

    @property
    @abc.abstractmethod
    def repo_key_file(self) -> str:
        pass

    def check_for_reboot_msg(self, operation: str) -> None:
        """Check if user should be alerted that a reboot must be performed.

        @param operation: The operation being executed.
        """
        if util.should_reboot():
            print(
                status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation=operation
                )
            )

    def _perform_enable(self) -> bool:
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        @raises: UserFacingError on failure to install suggested packages
        """
        self.setup_apt_config()
        if self.packages:
            msg_ops = self.messaging.get("pre_install", [])
            if not util.handle_message_operations(msg_ops):
                return False
            self.install_packages()
        print(status.MESSAGE_ENABLED_TMPL.format(title=self.title))
        self.check_for_reboot_msg(operation="install")
        return True

    def disable(self, silent=False):
        msg_ops = self.messaging.get("pre_disable", [])
        if not util.handle_message_operations(msg_ops):
            return False
        if not self.can_disable(silent):
            return False
        if hasattr(self, "remove_packages"):
            self.remove_packages()
        self._cleanup()
        msg_ops = self.messaging.get("post_disable", [])
        if not util.handle_message_operations(msg_ops):
            return False
        self.check_for_reboot_msg(operation="disable operation")
        return True

    def _cleanup(self) -> None:
        """Clean up the entitlement without checks or messaging"""
        self.remove_apt_config()

    def application_status(self) -> "Tuple[ApplicationStatus, str]":
        entitlement_cfg = self.cfg.entitlements.get(self.name, {})
        directives = entitlement_cfg.get("entitlement", {}).get(
            "directives", {}
        )
        repo_url = directives.get("aptURL")
        if not repo_url:
            return (
                ApplicationStatus.DISABLED,
                "{} does not have an aptURL directive".format(self.title),
            )
        protocol, repo_path = repo_url.split("://")
        policy = apt.run_apt_command(
            ["apt-cache", "policy"], status.MESSAGE_APT_POLICY_FAILED
        )
        match = re.search(
            r"(?P<pin>(-)?\d+) {}/ubuntu".format(repo_url), policy
        )
        if match and match.group("pin") != APT_DISABLED_PIN:
            return ApplicationStatus.ENABLED, "{} is active".format(self.title)
        return (
            ApplicationStatus.DISABLED,
            "{} is not configured".format(self.title),
        )

    def _check_apt_url_is_applied(self, apt_url):
        """Check if apt url delta should be applied.

        :param apt_url: string containing the apt url to be used.

        :return: False if apt url is already found on the source file.
                 True otherwise.
        """
        if not apt_url:
            return True

        apt_file = self.repo_list_file_tmpl.format(name=self.name)
        return bool(apt_url in util.load_file(apt_file))

    def process_contract_deltas(
        self,
        orig_access: "Dict[str, Any]",
        deltas: "Dict[str, Any]",
        allow_enable: bool = False,
    ) -> bool:
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

        delta_entitlement = deltas.get("entitlement", {})
        delta_directives = delta_entitlement.get("directives", {})
        delta_apt_url = delta_directives.get("aptURL")
        delta_packages = delta_directives.get("additionalPackages")
        status_cache = self.cfg.read_cache("status-cache")

        if delta_directives and status_cache:
            application_status = self._check_application_status_on_cache()
        else:
            application_status, _ = self.application_status()

        if application_status == status.ApplicationStatus.DISABLED:
            return True

        if not self._check_apt_url_is_applied(delta_apt_url):
            logging.info(
                "Updating '%s' apt sources list on changed directives.",
                self.name,
            )

            orig_entitlement = orig_access.get("entitlement", {})
            old_url = orig_entitlement.get("directives", {}).get("aptURL")
            if old_url:
                # Remove original aptURL and auth and rewrite
                repo_filename = self.repo_list_file_tmpl.format(name=self.name)
                apt.remove_auth_apt_repo(repo_filename, old_url)

            self.remove_apt_config()
            self.setup_apt_config()

        if delta_packages:
            logging.info(
                "Installing packages on changed directives: {}".format(
                    ", ".join(delta_packages)
                )
            )
            self.install_packages(package_list=delta_packages)

        return True

    def install_packages(
        self,
        package_list: "List[str]" = None,
        cleanup_on_failure: bool = True,
        verbose: bool = True,
    ) -> None:
        """Install contract recommended packages for the entitlement.

        :param package_list: Optional package list to use instead of
            self.packages.
        :param cleanup_on_failure: Cleanup apt files if apt install fails.
        :param verbose: If true, print messages to stdout
        """

        if verbose:
            print("Installing {title} packages".format(title=self.title))

        if self.apt_noninteractive:
            env = {"DEBIAN_FRONTEND": "noninteractive"}
            apt_options = [
                "--allow-downgrades",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
            ]
        else:
            env = {}
            apt_options = []
        if not package_list:
            package_list = self.packages
        try:
            apt.run_apt_command(
                ["apt-get", "install", "--assume-yes"]
                + apt_options
                + package_list,
                status.MESSAGE_ENABLED_FAILED_TMPL.format(title=self.title),
                env=env,
            )
        except exceptions.UserFacingError:
            if cleanup_on_failure:
                self._cleanup()
            raise

    def setup_apt_config(self) -> None:
        """Setup apt config based on the resourceToken and directives.
        Also sets up apt proxy if necessary.

        :raise UserFacingError: on failure to setup any aspect of this apt
           configuration
        """
        http_proxy = util.validate_proxy(
            "http", self.cfg.apt_http_proxy, util.PROXY_VALIDATION_APT_HTTP_URL
        )
        https_proxy = util.validate_proxy(
            "https",
            self.cfg.apt_https_proxy,
            util.PROXY_VALIDATION_APT_HTTPS_URL,
        )
        apt.setup_apt_proxy(http_proxy=http_proxy, https_proxy=https_proxy)
        repo_filename = self.repo_list_file_tmpl.format(name=self.name)
        resource_cfg = self.cfg.entitlements.get(self.name)
        directives = resource_cfg["entitlement"].get("directives", {})
        obligations = resource_cfg["entitlement"].get("obligations", {})
        token = resource_cfg.get("resourceToken")
        if not token:
            machine_token = self.cfg.machine_token["machineToken"]
            if not obligations.get("enableByDefault"):
                # services that are not enableByDefault need to obtain specific
                # resource access for tokens. We want to refresh this every
                # enable call because it is not refreshed by `ua refresh`.
                client = contract.UAContractClient(self.cfg)
                machine_access = client.request_resource_machine_access(
                    machine_token, self.name
                )
                if machine_access:
                    token = machine_access.get("resourceToken")
            if not token:
                token = machine_token
                logging.warning(
                    "No resourceToken present in contract for service %s."
                    " Using machine token as credentials",
                    self.title,
                )
        aptKey = directives.get("aptKey")
        if not aptKey:
            raise exceptions.UserFacingError(
                "Ubuntu Advantage server provided no aptKey directive for"
                " {}.".format(self.name)
            )
        repo_url = directives.get("aptURL")
        if not repo_url:
            raise exceptions.MissingAptURLDirective(self.name)
        repo_suites = directives.get("suites")
        if not repo_suites:
            raise exceptions.UserFacingError(
                "Empty {} apt suites directive from {}".format(
                    self.name, self.cfg.contract_url
                )
            )
        if self.repo_pin_priority:
            if not self.origin:
                raise exceptions.UserFacingError(
                    "Cannot setup apt pin. Empty apt repo origin value '{}'.\n"
                    "{}".format(
                        self.origin,
                        status.MESSAGE_ENABLED_FAILED_TMPL.format(
                            title=self.title
                        ),
                    )
                )
            repo_pref_file = self.repo_pref_file_tmpl.format(name=self.name)
            if self.repo_pin_priority != "never":
                apt.add_ppa_pinning(
                    repo_pref_file,
                    repo_url,
                    self.origin,
                    self.repo_pin_priority,
                )
            elif os.path.exists(repo_pref_file):
                os.unlink(repo_pref_file)  # Remove disabling apt pref file

        prerequisite_pkgs = []
        if not os.path.exists(apt.APT_METHOD_HTTPS_FILE):
            prerequisite_pkgs.append("apt-transport-https")
        if not os.path.exists(apt.CA_CERTIFICATES_FILE):
            prerequisite_pkgs.append("ca-certificates")

        if prerequisite_pkgs:
            print(
                "Installing prerequisites: {}".format(
                    ", ".join(prerequisite_pkgs)
                )
            )
            try:
                apt.run_apt_command(
                    ["apt-get", "install", "--assume-yes"] + prerequisite_pkgs,
                    status.MESSAGE_APT_INSTALL_FAILED,
                )
            except exceptions.UserFacingError:
                self.remove_apt_config()
                raise
        apt.add_auth_apt_repo(
            repo_filename, repo_url, token, repo_suites, self.repo_key_file
        )
        # Run apt-update on any repo-entitlement enable because the machine
        # probably wants access to the repo that was just enabled.
        # Side-effect is that apt policy will now report the repo as accessible
        # which allows ua status to report correct info
        print(status.MESSAGE_APT_UPDATING_LISTS)
        try:
            apt.run_apt_command(
                ["apt-get", "update"], status.MESSAGE_APT_UPDATE_FAILED
            )
        except exceptions.UserFacingError:
            self.remove_apt_config(run_apt_update=False)
            raise

    def remove_apt_config(self, run_apt_update=True):
        """Remove any repository apt configuration files.

        :param run_apt_update: If after removing the apt update
            command after removing the apt files.
        """
        series = util.get_platform_info()["series"]
        repo_filename = self.repo_list_file_tmpl.format(name=self.name)
        entitlement = self.cfg.entitlements[self.name].get("entitlement", {})
        access_directives = entitlement.get("directives", {})
        repo_url = access_directives.get("aptURL")
        if not repo_url:
            raise exceptions.MissingAptURLDirective(self.name)
        if self.disable_apt_auth_only:
            # We only remove the repo from the apt auth file, because
            # UA Infra: ESM is a special-case: we want to be able to report on
            # the available UA Infra: ESM updates even when it's disabled
            apt.remove_repo_from_apt_auth_file(repo_url)
            apt.restore_commented_apt_list_file(repo_filename)
        else:
            apt.remove_auth_apt_repo(
                repo_filename, repo_url, self.repo_key_file
            )
            apt.remove_apt_list_files(repo_url, series)
        if self.repo_pin_priority:
            repo_pref_file = self.repo_pref_file_tmpl.format(name=self.name)
            if self.repo_pin_priority == "never":
                # Disable the repo with a pinning file
                apt.add_ppa_pinning(
                    repo_pref_file,
                    repo_url,
                    self.origin,
                    self.repo_pin_priority,
                )
            elif os.path.exists(repo_pref_file):
                os.unlink(repo_pref_file)

        if run_apt_update:
            print(status.MESSAGE_APT_UPDATING_LISTS)
            apt.run_apt_command(
                ["apt-get", "update"], status.MESSAGE_APT_UPDATE_FAILED
            )
