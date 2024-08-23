import abc
import copy
import logging
import re
from os.path import exists
from typing import Any, Dict, List, Optional, Tuple, Union

from uaclient import (
    api,
    apt,
    contract,
    event_logger,
    exceptions,
    http,
    messages,
    system,
    util,
)
from uaclient.entitlements import base
from uaclient.entitlements.entitlement_status import (
    ApplicationStatus,
    CanDisableFailure,
    CanDisableFailureReason,
)
from uaclient.files.state_files import status_cache_file

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

# See 'What does a specific Ubuntu kernel version number mean?' in
# https://wiki.ubuntu.com/Kernel/FAQ
RE_KERNEL_PKG = r"^linux-image-([\d]+[.-][\d]+[.-][\d]+-[\d]+-[A-Za-z0-9_-]+)$"


class RepoEntitlement(base.UAEntitlement):
    repo_file_tmpl = "/etc/apt/sources.list.d/ubuntu-{name}.{extension}"
    repo_pref_file_tmpl = "/etc/apt/preferences.d/ubuntu-{name}"
    repo_url_tmpl = "{}/ubuntu"

    # The repo Origin value defined in apt metadata
    origin = None  # type: Optional[str]

    # GH: #1084 call apt in noninteractive mode
    apt_noninteractive = False

    # Check if the requested packages are installed to inform if
    # the service is enabled or not
    check_packages_are_installed = False

    # RepoEntitlements can be purged, unless specifically stated
    supports_purge = True

    # Optional repo pin priority in subclass
    @property
    def repo_pin_priority(self) -> Union[int, str, None]:
        return None

    @property
    def repo_file(self) -> str:
        extension = "sources"
        series = system.get_release_info().series
        if series in apt.SERIES_NOT_USING_DEB822:
            extension = "list"
        return self.repo_file_tmpl.format(name=self.name, extension=extension)

    @property
    def repo_policy_check_tmpl(self) -> str:
        return self.repo_url_tmpl + " {}"

    @property
    def packages(self) -> List[str]:
        """debs to install on enablement"""
        packages = []

        entitlement = self.entitlement_cfg.get("entitlement", {})

        if entitlement:
            directives = entitlement.get("directives", {})
            additional_packages = copy.copy(
                directives.get("additionalPackages", [])
            )

            packages = additional_packages

        return packages

    @property
    def apt_url(self) -> Optional[str]:
        return (
            self.entitlement_cfg.get("entitlement", {})
            .get("directives", {})
            .get("aptURL")
        )

    @property
    def apt_suites(self) -> Optional[str]:
        return (
            self.entitlement_cfg.get("entitlement", {})
            .get("directives", {})
            .get("suites")
        )

    def _check_for_reboot(self) -> bool:
        """Check if system needs to be rebooted."""
        reboot_required = system.should_reboot(
            installed_pkgs=set(self.packages)
        )
        event.needs_reboot(reboot_required)
        return reboot_required

    @property
    @abc.abstractmethod
    def repo_key_file(self) -> str:
        pass

    def can_disable(
        self, ignore_dependent_services: bool = False
    ) -> Tuple[bool, Optional[CanDisableFailure]]:
        result, reason = super().can_disable(
            ignore_dependent_services=ignore_dependent_services
        )
        if result is False:
            return result, reason

        if not self.origin and self.purge:
            return (
                False,
                CanDisableFailure(
                    CanDisableFailureReason.NO_PURGE_WITHOUT_ORIGIN,
                    messages.REPO_PURGE_FAIL_NO_ORIGIN.format(
                        entitlement_name=self.title, title=self.title
                    ),
                ),
            )

        return result, reason

    def enable_steps(self) -> int:
        will_install = self.packages is not None and len(self.packages) > 0
        if self.access_only or not will_install:
            # 1. Configure APT
            # 2. Update APT lists
            return 2
        else:
            # 3. Install packages
            return 3

    def _perform_enable(self, progress: api.ProgressWrapper) -> bool:
        """Enable specific entitlement.

        @return: True on success, False otherwise.
        @raises: UbuntuProError on failure to install suggested packages
        """
        progress.progress(
            messages.CONFIGURING_APT_ACCESS.format(service=self.title)
        )
        self.setup_apt_config(progress)

        if self.supports_access_only and self.access_only:
            if len(self.packages) > 0:
                progress.emit(
                    "info",
                    messages.SKIPPING_INSTALLING_PACKAGES.format(
                        packages=" ".join(self.packages)
                    ),
                )
        else:
            self.install_packages(progress)
        return True

    def disable_steps(self) -> int:
        if not self.purge:
            # 1. Unconfigure APT
            # 2. Update package lists
            return 2
        else:
            # 3. Purge
            return 3

    def _perform_disable(self, progress: api.ProgressWrapper):
        if self.purge and self.origin:
            progress.emit("info", messages.PURGE_EXPERIMENTAL)
            progress.emit("info", "")

            repo_origin_packages = apt.get_installed_packages_by_origin(
                self.origin
            )

            if not self.purge_kernel_check(repo_origin_packages, progress):
                return False

            packages_to_reinstall = []
            packages_to_remove = []
            for package in repo_origin_packages:
                alternatives = apt.get_remote_versions_for_package(
                    package, exclude_origin=self.origin
                )
                if alternatives:
                    # We can call max(List[Version]) but mypy doesn't know.
                    # Or doesn't like it.
                    packages_to_reinstall.append(
                        (package, max(alternatives))  # type: ignore
                    )
                else:
                    packages_to_remove.append(package)

            if not self.prompt_for_purge(
                packages_to_remove, packages_to_reinstall, progress
            ):
                return False

        if hasattr(self, "remove_packages"):
            self.remove_packages()
        self.remove_apt_config(progress)

        if self.purge and self.origin:
            progress.progress(
                messages.PURGING_PACKAGES.format(title=self.title)
            )
            self.execute_reinstall(packages_to_reinstall)
            self.execute_removal(packages_to_remove)
        return True

    def purge_kernel_check(self, package_list, progress: api.ProgressWrapper):
        """
        Checks if the purge operation involves a kernel.

        When package called 'linux-image-*' is in the package list, warn the
        user that a kernel is being removed. Then, show the user what the
        current kernel is.

        If the current kernel is to be removed, and there are no other valid
        Ubuntu Kernels installed in the system, return False to abort the
        operation.

        If there is another Ubuntu kernel - besides the one installed - then
        prompt the user for confirmation before proceeding.
        """
        linux_image_versions = []
        for package in package_list:
            m = re.search(RE_KERNEL_PKG, package.name)
            if m:
                linux_image_versions.append(m.group(1))
        if linux_image_versions:
            # A kernel needs to be removed to purge
            # API will fail here, but we want CLI to allow it to continue
            # after a prompt
            if not progress.is_interactive():
                raise exceptions.NonInteractiveKernelPurgeDisallowed()

            progress.emit(
                "info",
                messages.PURGE_KERNEL_REMOVAL.format(service=self.title),
            )
            progress.emit("info", " ".join(linux_image_versions))

            current_kernel = system.get_kernel_info().uname_release
            progress.emit(
                "info",
                messages.PURGE_CURRENT_KERNEL.format(
                    kernel_version=current_kernel
                ),
            )

            installed_kernels = system.get_installed_ubuntu_kernels()
            # Any installed Ubuntu Kernel not being touched in this operation
            alternative_kernels = [
                version
                for version in installed_kernels
                if version not in linux_image_versions
            ]

            if not alternative_kernels:
                progress.emit("info", messages.PURGE_NO_ALTERNATIVE_KERNEL)
                return False

            progress.emit(
                "message_operation",
                [
                    (
                        util.prompt_for_confirmation,
                        {"msg": messages.PURGE_KERNEL_CONFIRMATION},
                    )
                ],
            )

        return True

    def prompt_for_purge(
        self,
        packages_to_remove,
        packages_to_reinstall,
        progress: api.ProgressWrapper,
    ):
        prompt = False
        if packages_to_remove:
            progress.emit("info", messages.WARN_PACKAGES_REMOVAL)
            progress.emit(
                "info",
                util.create_package_list_str(
                    [package.name for package in packages_to_remove]
                ),
            )
            prompt = True

        if packages_to_reinstall:
            progress.emit("info", messages.WARN_PACKAGES_REINSTALL)
            progress.emit(
                "info",
                util.create_package_list_str(
                    [package.name for (package, _) in packages_to_reinstall]
                ),
            )
            prompt = True

        if prompt:
            progress.emit(
                "message_operation",
                [
                    (
                        util.prompt_for_confirmation,
                        {"msg": messages.PROCEED_YES_NO},
                    )
                ],
            )
        return True

    def execute_removal(self, packages_to_remove):
        # We need to check again if the package is installed, because there is
        # an intermediate step between listing the packages and acting on them.
        # Some reinstalls may also uninstall dependencies.
        # Packages may be removed between those operations.
        installed_packages = apt.get_installed_packages_names()
        to_remove = [
            package.name
            for package in packages_to_remove
            if package.name in installed_packages
        ]
        if to_remove:
            apt.purge_packages(
                to_remove,
                messages.UNINSTALLING_PACKAGES_FAILED.format(
                    packages=to_remove
                ),
            )

    def execute_reinstall(self, packages_to_reinstall):
        # We need to check again if the package is installed, because there is
        # an intermediate step between listing the packages and acting on them.
        # Packages may be removed between those operations.
        installed_packages = apt.get_installed_packages_names()
        to_reinstall = [
            "{}={}".format(package.name, version.ver_str)
            for (package, version) in packages_to_reinstall
            if package.name in installed_packages
        ]
        if to_reinstall:
            apt.reinstall_packages(to_reinstall)

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        current_status = (
            ApplicationStatus.DISABLED,
            messages.SERVICE_NOT_CONFIGURED.format(title=self.title),
        )

        entitlement_cfg = self.entitlement_cfg
        directives = entitlement_cfg.get("entitlement", {}).get(
            "directives", {}
        )
        repo_url = directives.get("aptURL")
        if not repo_url:
            return (
                ApplicationStatus.DISABLED,
                messages.NO_APT_URL_FOR_SERVICE.format(title=self.title),
            )
        repo_suites = directives.get("suites")
        if not repo_suites:
            return (
                ApplicationStatus.DISABLED,
                messages.NO_SUITES_FOR_SERVICE.format(title=self.title),
            )

        policy = apt.get_apt_cache_policy(error_msg=messages.APT_POLICY_FAILED)
        for suite in repo_suites:
            service_match = re.search(
                self.repo_policy_check_tmpl.format(repo_url, suite), policy
            )
            if service_match:
                current_status = (
                    ApplicationStatus.ENABLED,
                    messages.SERVICE_IS_ACTIVE.format(title=self.title),
                )
                break

        if self.check_packages_are_installed:
            for package in self.packages:
                if not apt.is_installed(package):
                    return (
                        ApplicationStatus.DISABLED,
                        messages.SERVICE_DISABLED_MISSING_PACKAGE.format(
                            service=self.name, package=package
                        ),
                    )

        return current_status

    def _check_apt_url_is_applied(self, apt_url):
        """Check if apt url delta should be applied.

        :param apt_url: string containing the apt url to be used.

        :return: False if apt url is already found on the source file.
                 True otherwise.
        """
        apt_file = self.repo_file
        # If the apt file is commented out, we will assume that we need
        # to regenerate the apt file, regardless of the apt url delta
        if all(
            line.startswith("#")
            for line in system.load_file(apt_file).strip().split("\n")
        ):
            return False

        # If the file is not commented out and we don't have delta,
        # we will not do anything
        if not apt_url:
            return True

        # If the delta is already in the file, we won't reconfigure it
        # again
        return bool(apt_url in system.load_file(apt_file))

    def process_contract_deltas(
        self,
        orig_access: Dict[str, Any],
        deltas: Dict[str, Any],
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
        status_cache = status_cache_file.read()

        if delta_directives and status_cache:
            application_status = self._check_application_status_on_cache()
        else:
            application_status, _ = self.application_status()

        if application_status == ApplicationStatus.DISABLED:
            return False

        if not self._check_apt_url_is_applied(delta_apt_url):
            LOG.info(
                "New aptURL, updating %s apt sources list to %s",
                self.name,
                delta_apt_url,
            )
            event.info(
                messages.REPO_UPDATING_APT_SOURCES.format(service=self.name)
            )

            orig_entitlement = orig_access.get("entitlement", {})
            old_url = orig_entitlement.get("directives", {}).get("aptURL")
            if old_url:
                # Remove original aptURL and auth and rewrite
                apt.remove_auth_apt_repo(self.repo_file, old_url)

            self.remove_apt_config(api.ProgressWrapper())
            self.setup_apt_config(api.ProgressWrapper())

        if delta_packages:
            LOG.info("New additionalPackages, installing %r", delta_packages)
            event.info(
                messages.REPO_REFRESH_INSTALLING_PACKAGES.format(
                    packages=", ".join(delta_packages)
                )
            )
            self.install_packages(
                api.ProgressWrapper(), package_list=delta_packages
            )

        return True

    def install_packages(
        self,
        progress: api.ProgressWrapper,
        package_list: Optional[List[str]] = None,
        cleanup_on_failure: bool = True,
    ) -> None:
        """Install contract recommended packages for the entitlement.

        :param package_list: Optional package list to use instead of
            self.packages.
        :param cleanup_on_failure: Cleanup apt files if apt install fails.
        """

        if not package_list:
            package_list = self.packages

        if not package_list:
            return

        progress.emit("message_operation", self.messaging.get("pre_install"))

        try:
            self._update_sources_list(progress)
        except exceptions.UbuntuProError:
            if cleanup_on_failure:
                self.remove_apt_config(api.ProgressWrapper())
            raise

        progress.progress(
            messages.INSTALLING_SERVICE_PACKAGES.format(title=self.title)
        )

        if self.apt_noninteractive:
            override_env_vars = {"DEBIAN_FRONTEND": "noninteractive"}
            apt_options = [
                "--allow-downgrades",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
            ]
        else:
            override_env_vars = None
            apt_options = []

        try:
            apt.run_apt_install_command(
                packages=package_list,
                apt_options=apt_options,
                override_env_vars=override_env_vars,
            )
        except exceptions.UbuntuProError:
            if cleanup_on_failure:
                LOG.info(
                    "Apt install failed, removing apt config for {}".format(
                        self.name
                    )
                )
                self.remove_apt_config(api.ProgressWrapper())
            raise

    def setup_apt_config(self, progress: api.ProgressWrapper) -> None:
        """Setup apt config based on the resourceToken and directives.
        Also sets up apt proxy if necessary.

        :raise UbuntuProError: on failure to setup any aspect of this apt
           configuration
        """
        http_proxy = None  # type: Optional[str]
        https_proxy = None  # type: Optional[str]
        scope = None  # type: Optional[apt.AptProxyScope]
        if self.cfg.global_apt_http_proxy or self.cfg.global_apt_https_proxy:
            http_proxy = http.validate_proxy(
                "http",
                self.cfg.global_apt_http_proxy,
                http.PROXY_VALIDATION_APT_HTTP_URL,
            )
            https_proxy = http.validate_proxy(
                "https",
                self.cfg.global_apt_https_proxy,
                http.PROXY_VALIDATION_APT_HTTPS_URL,
            )
            scope = apt.AptProxyScope.GLOBAL
        elif self.cfg.ua_apt_http_proxy or self.cfg.ua_apt_https_proxy:
            http_proxy = http.validate_proxy(
                "http",
                self.cfg.ua_apt_http_proxy,
                http.PROXY_VALIDATION_APT_HTTP_URL,
            )
            https_proxy = http.validate_proxy(
                "https",
                self.cfg.ua_apt_https_proxy,
                http.PROXY_VALIDATION_APT_HTTPS_URL,
            )
            scope = apt.AptProxyScope.UACLIENT

        apt.setup_apt_proxy(
            http_proxy=http_proxy, https_proxy=https_proxy, proxy_scope=scope
        )
        repo_filename = self.repo_file
        resource_cfg = self.entitlement_cfg
        directives = resource_cfg["entitlement"].get("directives", {})
        obligations = resource_cfg["entitlement"].get("obligations", {})
        token = resource_cfg.get("resourceToken")
        if not token:
            machine_token = self.machine_token_file.machine_token[
                "machineToken"
            ]
            if not obligations.get("enableByDefault"):
                # services that are not enableByDefault need to obtain specific
                # resource access for tokens. We want to refresh this every
                # enable call because it is not refreshed by `pro refresh`.
                client = contract.UAContractClient(self.cfg)
                machine_access = client.get_resource_machine_access(
                    machine_token, self.name
                )
                if machine_access:
                    token = machine_access.get("resourceToken")
            if not token:
                token = machine_token
                LOG.warning(
                    "No resourceToken present in contract for service %s."
                    " Using machine token as credentials",
                    self.title,
                )
        aptKey = directives.get("aptKey")
        if not aptKey:
            raise exceptions.RepoNoAptKey(entitlement_name=self.name)
        repo_url = directives.get("aptURL")
        if not repo_url:
            raise exceptions.MissingAptURLDirective(entitlement_name=self.name)
        repo_suites = directives.get("suites")
        if not repo_suites:
            raise exceptions.RepoNoSuites(entitlement_name=self.name)
        if self.repo_pin_priority:
            if not self.origin:
                raise exceptions.RepoPinFailNoOrigin(
                    entitlement_name=self.name,
                    title=self.title,
                )
            repo_pref_file = self.repo_pref_file_tmpl.format(name=self.name)
            apt.add_ppa_pinning(
                repo_pref_file,
                repo_url,
                self.origin,
                self.repo_pin_priority,
            )

        prerequisite_pkgs = []
        if not exists(apt.APT_METHOD_HTTPS_FILE):
            prerequisite_pkgs.append("apt-transport-https")
        if not exists(apt.CA_CERTIFICATES_FILE):
            prerequisite_pkgs.append("ca-certificates")

        if prerequisite_pkgs:
            progress.emit(
                "info",
                messages.INSTALLING_PACKAGES.format(
                    packages=", ".join(prerequisite_pkgs)
                ),
            )
            try:
                apt.run_apt_install_command(packages=prerequisite_pkgs)
            except exceptions.UbuntuProError:
                self.remove_apt_config(api.ProgressWrapper())
                raise
        apt.add_auth_apt_repo(
            repo_filename,
            self.repo_url_tmpl.format(repo_url),
            token,
            repo_suites,
            self.repo_key_file,
        )
        # Run apt-update on any repo-entitlement enable because the machine
        # probably wants access to the repo that was just enabled.
        # Side-effect is that apt policy will now report the repo as accessible
        # which allows pro status to report correct info
        progress.progress(messages.APT_UPDATING_LIST.format(name=self.title))
        try:
            apt.update_sources_list(repo_filename)
        except exceptions.UbuntuProError:
            self.remove_apt_config(api.ProgressWrapper(), run_apt_update=False)
            raise

    def remove_apt_config(
        self,
        progress: api.ProgressWrapper,
        run_apt_update: bool = True,
    ):
        """Remove any repository apt configuration files.

        :param run_apt_update: If after removing the apt update
            command after removing the apt files.
        """
        series = system.get_release_info().series
        repo_filename = self.repo_file
        entitlement = self.machine_token_file.entitlements()[self.name].get(
            "entitlement", {}
        )
        access_directives = entitlement.get("directives", {})
        repo_url = access_directives.get("aptURL")
        if not repo_url:
            raise exceptions.MissingAptURLDirective(entitlement_name=self.name)

        repo_url = self.repo_url_tmpl.format(repo_url)

        progress.progress(
            messages.REMOVING_APT_CONFIGURATION.format(title=self.title)
        )
        apt.remove_auth_apt_repo(repo_filename, repo_url, self.repo_key_file)
        apt.remove_apt_list_files(repo_url, series)

        if self.repo_pin_priority:
            repo_pref_file = self.repo_pref_file_tmpl.format(name=self.name)
            system.ensure_file_absent(repo_pref_file)

        if run_apt_update:
            progress.progress(messages.APT_UPDATING_LISTS)
            apt.run_apt_update_command()
