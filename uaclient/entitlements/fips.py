import logging
import os
import re
from itertools import groupby
from typing import List, Optional, Tuple

from uaclient import api, apt, event_logger, exceptions, messages, system, util
from uaclient.clouds.identity import NoCloudTypeReason, get_cloud_type
from uaclient.entitlements import repo
from uaclient.entitlements.base import EntitlementWithMessage
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.files import notices
from uaclient.files.notices import Notice
from uaclient.files.state_files import (
    ServicesOnceEnabledData,
    services_once_enabled_file,
)
from uaclient.types import (  # noqa: F401
    MessagingOperations,
    MessagingOperationsDict,
    StaticAffordance,
)

event = event_logger.get_event_logger()
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

CONDITIONAL_PACKAGES_EVERYWHERE = [
    "strongswan",
    "strongswan-hmac",
    "openssh-client",
    "openssh-server",
    "shim-signed",
]
CONDITIONAL_PACKAGES_OPENSSH_HMAC = [
    "openssh-client-hmac",
    "openssh-server-hmac",
]
FIPS_CONDITIONAL_PACKAGES = {
    "xenial": CONDITIONAL_PACKAGES_EVERYWHERE
    + CONDITIONAL_PACKAGES_OPENSSH_HMAC,
    "bionic": CONDITIONAL_PACKAGES_EVERYWHERE
    + CONDITIONAL_PACKAGES_OPENSSH_HMAC,
    "focal": CONDITIONAL_PACKAGES_EVERYWHERE,
}


# In containers, we don't install the ubuntu-fips
# metapackage, but we do want to auto-upgrade any
# fips related packages that are already installed.
# These lists need to be kept up to date with the
# Depends of ubuntu-fips.
# Note that these lists only include those packages
# that are relevant for a container to upgrade
# after enabling fips or fips-updates.
UBUNTU_FIPS_METAPACKAGE_DEPENDS_XENIAL = [
    "openssl",
    "libssl1.0.0",
    "libssl1.0.0-hmac",
]
UBUNTU_FIPS_METAPACKAGE_DEPENDS_BIONIC = [
    "openssl",
    "libssl1.1",
    "libssl1.1-hmac",
    "libgcrypt20",
    "libgcrypt20-hmac",
]
UBUNTU_FIPS_METAPACKAGE_DEPENDS_FOCAL = [
    "openssl",
    "libssl1.1",
    "libssl1.1-hmac",
    "libgcrypt20",
    "libgcrypt20-hmac",
]
FIPS_CONTAINER_CONDITIONAL_PACKAGES = {
    "xenial": CONDITIONAL_PACKAGES_EVERYWHERE
    + CONDITIONAL_PACKAGES_OPENSSH_HMAC
    + UBUNTU_FIPS_METAPACKAGE_DEPENDS_XENIAL,
    "bionic": CONDITIONAL_PACKAGES_EVERYWHERE
    + CONDITIONAL_PACKAGES_OPENSSH_HMAC
    + UBUNTU_FIPS_METAPACKAGE_DEPENDS_BIONIC,
    "focal": CONDITIONAL_PACKAGES_EVERYWHERE
    + UBUNTU_FIPS_METAPACKAGE_DEPENDS_FOCAL,
}


class FIPSCommonEntitlement(repo.RepoEntitlement):
    repo_pin_priority = 1001
    repo_key_file = "ubuntu-pro-fips.gpg"  # Same for fips & fips-updates
    FIPS_PROC_FILE = "/proc/sys/crypto/fips_enabled"
    pre_enable_msg = messages.PROMPT_FIPS_PRE_ENABLE

    # RELEASE_BLOCKER GH: #104, don't prompt for conf differences in FIPS
    # Review this fix to see if we want more general functionality for all
    # services. And security/CPC signoff on expected conf behavior.
    apt_noninteractive = True

    help_doc_url = messages.urls.FIPS_HOME_PAGE

    fips_pro_package_holds = [
        "fips-initramfs",
        "fips-initramfs-generic",
        "libgcrypt20",
        "libgcrypt20-hmac",
        "libgmp10",
        "libgnutls30",
        "libhogweed6",
        "libnettle8",
        "libssl1.0.0",
        "libssl1.0.0-hmac",
        "libssl1.0.0",
        "libssl1.0.0-hmac",
        "libssl1.1",
        "libssl1.1-hmac",
        "libssl3",
        "linux-fips",
        "openssh-client",
        "openssh-client-hmac",
        "openssh-server",
        "openssh-server-hmac",
        "openssl",
        "openssl-fips-module-3",
        "shim-signed",
        "strongswan",
        "strongswan-hmac",
        "ubuntu-fips",
        "ubuntu-aws-fips",
        "ubuntu-azure-fips",
        "ubuntu-gcp-fips",
    ]

    @property
    def messaging(self) -> MessagingOperationsDict:
        post_enable = None  # type: Optional[MessagingOperations]
        if system.is_container():
            pre_enable_prompt = (
                messages.PROMPT_FIPS_CONTAINER_PRE_ENABLE.format(
                    title=self.title
                )
            )
            if not self.auto_upgrade_all_on_enable():
                post_enable = [messages.FIPS_RUN_APT_UPGRADE]
        else:
            pre_enable_prompt = self.pre_enable_msg

        pre_disable = None  # type: Optional[MessagingOperations]
        if not self.purge:
            pre_disable = [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.PROMPT_FIPS_PRE_DISABLE.format(
                            title=self.title
                        ),
                    },
                )
            ]

        messaging = {
            "pre_enable": [
                (
                    util.prompt_for_confirmation,
                    {"msg": pre_enable_prompt},
                )
            ],
            "pre_install": [
                (
                    self.prompt_if_kernel_downgrade,
                    {},
                )
            ],
            "post_enable": post_enable,
            "pre_disable": pre_disable,
        }  # type: MessagingOperationsDict

        if len(self.packages) == 1:
            # that is the kernel "ubuntu-fips" or "ubuntu-${cloud}-fips"
            ubuntu_fips_package_name = self.packages[0]
            ubuntu_fips_package_flavor_match = re.match(
                "ubuntu-([a-z]+)-fips", ubuntu_fips_package_name
            )
            if ubuntu_fips_package_flavor_match:
                ubuntu_fips_package_flavor = (
                    ubuntu_fips_package_flavor_match.group(1)
                )
            else:
                ubuntu_fips_package_flavor = "generic"
            current_flavor = system.get_kernel_info().flavor
            if ubuntu_fips_package_flavor != current_flavor:
                pre_enable = messaging.get("pre_enable") or []
                msg = messages.KERNEL_FLAVOR_CHANGE_WARNING_PROMPT.format(
                    variant=ubuntu_fips_package_flavor,
                    service=self.name,
                    base_flavor=ubuntu_fips_package_flavor,
                    current_flavor=current_flavor or "unknown",
                )
                pre_enable.append(
                    (
                        util.prompt_for_confirmation,
                        {"msg": msg},
                    )
                )
                messaging["pre_enable"] = pre_enable

        return messaging

    @property
    def conditional_packages(self):
        """
        Dictionary of conditional packages to be installed when
        enabling FIPS services. For example, if we are enabling
        FIPS services in a machine that has openssh-client installed,
        we will perform two actions:

        1. Upgrade the package to the FIPS version
        2. Install the corresponding hmac version of that package
           when available.
        """
        series = system.get_release_info().series

        if system.is_container():
            return FIPS_CONTAINER_CONDITIONAL_PACKAGES.get(series, [])

        return FIPS_CONDITIONAL_PACKAGES.get(series, [])

    def prompt_if_kernel_downgrade(self, *, assume_yes: bool) -> bool:
        """Check if installing a FIPS kernel will downgrade the kernel
        and prompt for confirmation if it will.
        """
        # Prior to installing packages, check if the kernel is being downgraded
        # and if so verify that the user wants to continue
        our_full_kernel_str = (
            system.get_kernel_info().proc_version_signature_version
        )
        if our_full_kernel_str is None:
            LOG.warning("Cannot gather kernel information")
            return False
        our_m = re.search(
            r"(?P<kernel_version>\d+\.\d+\.\d+)", our_full_kernel_str
        )
        fips_kernel_version_str = apt.get_pkg_candidate_version("linux-fips")
        if our_m is not None and fips_kernel_version_str is not None:
            our_kernel_version_str = our_m.group("kernel_version")
            LOG.debug(
                "Kernel information: cur='%s' and fips='%s'",
                our_full_kernel_str,
                fips_kernel_version_str,
            )
            if (
                apt.version_compare(
                    fips_kernel_version_str, our_kernel_version_str
                )
                < 0
            ):
                event.info(
                    messages.KERNEL_DOWNGRADE_WARNING.format(
                        current_version=our_kernel_version_str,
                        new_version=fips_kernel_version_str,
                    )
                )
                return util.prompt_for_confirmation(
                    msg=messages.PROMPT_YES_NO, assume_yes=assume_yes
                )
        else:
            LOG.warning(
                "Cannot gather kernel information for '%s' and '%s'",
                our_full_kernel_str,
                fips_kernel_version_str,
            )
        return True

    def hardcoded_install_conditional_packages(
        self, progress: api.ProgressWrapper
    ):
        # Any conditional packages should still be installed, but if
        # they fail to install we should not block the enable operation.
        desired_packages = []  # type: List[str]
        installed_packages = apt.get_installed_packages_names()
        pkg_groups = groupby(
            sorted(self.conditional_packages),
            key=lambda pkg_name: pkg_name.replace("-hmac", ""),
        )

        for pkg_name, pkg_list in pkg_groups:
            if pkg_name in installed_packages:
                desired_packages += pkg_list

        for pkg in desired_packages:
            try:
                apt.run_apt_install_command(
                    packages=[pkg],
                    override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
                    apt_options=[
                        "--allow-downgrades",
                        '-o Dpkg::Options::="--force-confdef"',
                        '-o Dpkg::Options::="--force-confold"',
                    ],
                )
            except exceptions.UbuntuProError:
                progress.emit(
                    "info",
                    messages.FIPS_PACKAGE_NOT_AVAILABLE.format(
                        service=self.title, pkg=pkg
                    ),
                )

    def auto_upgrade_all_on_enable(self) -> bool:
        install_all_updates_override = util.is_config_value_true(
            config=self.cfg.cfg, path_to_value="features.fips_auto_upgrade_all"
        )
        # noble onward automatically uses new auto-upgrade logic
        hardcoded_release = system.get_release_info().series in {
            "xenial",
            "bionic",
            "focal",
        }
        return install_all_updates_override or not hardcoded_release

    def install_all_available_fips_upgrades(
        self, progress: api.ProgressWrapper
    ):
        to_upgrade = [
            package.name
            for package in apt.get_installed_packages_with_uninstalled_candidate_in_origin(  # noqa: E501
                self.origin
            )
        ]

        to_upgrade.sort()
        if len(to_upgrade) > 0:
            try:
                progress.emit(
                    "info",
                    messages.INSTALLING_PACKAGES.format(
                        packages=" ".join(to_upgrade)
                    ),
                )
                self.unhold_packages(to_upgrade)
                apt.run_apt_install_command(
                    packages=to_upgrade,
                    override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
                    apt_options=[
                        "--allow-downgrades",
                        '-o Dpkg::Options::="--force-confdef"',
                        '-o Dpkg::Options::="--force-confold"',
                    ],
                )
            except exceptions.UbuntuProError:
                progress.emit("info", messages.FIPS_PACKAGES_UPGRADE_FAILURE)

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
        # We need to guarantee that the metapackage is installed.
        # While the other packages should still be installed, if they
        # fail, we should not block the enable operation.
        mandatory_packages = self.packages
        if mandatory_packages:
            super().install_packages(
                progress,
                package_list=mandatory_packages,
            )
        else:
            # then this won't get printed by install_packages, so do it here
            # instead
            progress.progress(
                messages.INSTALLING_SERVICE_PACKAGES.format(title=self.title)
            )

        if self.auto_upgrade_all_on_enable():
            self.install_all_available_fips_upgrades(progress)
        else:
            self.hardcoded_install_conditional_packages(progress)

        if self._check_for_reboot():
            notices.add(
                Notice.FIPS_SYSTEM_REBOOT_REQUIRED,
            )

    def _check_for_reboot(self) -> bool:
        """Check if system needs to be rebooted because of this service."""
        return system.should_reboot()

    def _check_for_reboot_msg(
        self, operation: str, silent: bool = False
    ) -> None:
        """Check if user should be alerted that a reboot must be performed.

        @param operation: The operation being executed.
        @param silent: Boolean set True to silence print/log of messages
        """
        reboot_required = self._check_for_reboot()
        event.needs_reboot(reboot_required)
        if reboot_required:
            if not silent:
                event.info(
                    messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation=operation
                    )
                )
            if operation == "disable operation":
                notices.add(
                    Notice.FIPS_DISABLE_REBOOT_REQUIRED,
                )

    def _allow_fips_on_cloud_instance(
        self, series: str, cloud_id: str
    ) -> bool:
        """Return False when FIPS is allowed on this cloud and series.

        On Xenial GCP there will be no cloud-optimized kernel so
        block default ubuntu-fips enable. This can be overridden in
        config with features.allow_xenial_fips_on_cloud.

        GCP doesn't yet have a cloud-optimized kernel or metapackage so
        block enable of fips if the contract does not specify ubuntu-gcp-fips.
        This also can be overridden in config with
        features.allow_default_fips_metapackage_on_gcp.

        :return: False when this cloud, series or config override allows FIPS.
        """
        if cloud_id == "gce":
            if util.is_config_value_true(
                config=self.cfg.cfg,
                path_to_value="features.allow_default_fips_metapackage_on_gcp",
            ):
                return True

            # GCE only has FIPS support for bionic and focal machines
            if series in ("bionic", "focal"):
                return True

            return bool("ubuntu-gcp-fips" in super().packages)

        return True

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        cloud_titles = {"aws": "an AWS", "azure": "an Azure", "gce": "a GCP"}
        cloud_id, _ = get_cloud_type()
        if cloud_id is None:
            cloud_id = ""

        series = system.get_release_info().series
        blocked_message = messages.FIPS_BLOCK_ON_CLOUD.format(
            series=series.title(), cloud=cloud_titles.get(cloud_id)
        )
        return (
            (
                blocked_message,
                lambda: self._allow_fips_on_cloud_instance(series, cloud_id),
                True,
            ),
        )

    @property
    def packages(self) -> List[str]:
        if system.is_container():
            return []
        return super().packages

    def application_status(
        self,
    ) -> Tuple[ApplicationStatus, Optional[messages.NamedMessage]]:
        super_status, super_msg = super().application_status()

        if system.is_container() and not system.should_reboot():
            notices.remove(
                Notice.FIPS_SYSTEM_REBOOT_REQUIRED,
            )
            return super_status, super_msg

        if os.path.exists(self.FIPS_PROC_FILE):
            # We are now only removing the notice if there is no reboot
            # required information regarding the fips metapackage we install.
            if not system.should_reboot(set(self.packages)):
                notices.remove(
                    Notice.FIPS_SYSTEM_REBOOT_REQUIRED,
                )

            if system.load_file(self.FIPS_PROC_FILE).strip() == "1":
                notices.remove(
                    Notice.FIPS_MANUAL_DISABLE_URL,
                )
                return super_status, super_msg
            else:
                notices.add(
                    Notice.FIPS_MANUAL_DISABLE_URL,
                )
                return (
                    ApplicationStatus.DISABLED,
                    messages.FIPS_PROC_FILE_ERROR.format(
                        file_name=self.FIPS_PROC_FILE
                    ),
                )

        if super_status != ApplicationStatus.ENABLED:
            return super_status, super_msg
        return (
            ApplicationStatus.ENABLED,
            messages.FIPS_REBOOT_REQUIRED,
        )

    def remove_packages(self) -> None:
        """Remove fips meta package to disable the service.

        FIPS meta-package will unset grub config options which will deactivate
        FIPS on any related packages.
        """
        installed_packages = set(apt.get_installed_packages_names())
        fips_metapackage = set(self.packages).difference(
            set(self.conditional_packages)
        )
        remove_packages = fips_metapackage.intersection(installed_packages)
        if remove_packages:
            apt.remove_packages(
                list(fips_metapackage),
                messages.DISABLE_FAILED_TMPL.format(title=self.title),
            )

    def _perform_enable(self, progress: api.ProgressWrapper) -> bool:
        if super()._perform_enable(progress):
            notices.remove(
                Notice.WRONG_FIPS_METAPACKAGE_ON_CLOUD,
            )
            notices.remove(Notice.FIPS_REBOOT_REQUIRED)
            notices.remove(Notice.FIPS_DISABLE_REBOOT_REQUIRED)
            return True

        return False

    def _perform_disable(self, progress: api.ProgressWrapper) -> bool:
        if super()._perform_disable(progress):
            if self._check_for_reboot():
                notices.add(
                    Notice.FIPS_DISABLE_REBOOT_REQUIRED,
                )
            return True

        return False

    def unhold_packages(self, package_names):
        cmd = ["apt-mark", "showholds"]
        holds = apt.run_apt_command(
            cmd,
            messages.EXECUTING_COMMAND_FAILED.format(command=" ".join(cmd)),
        )
        unholds = []
        for hold in holds.splitlines():
            if hold in package_names:
                unholds.append(hold)
        if unholds:
            unhold_cmd = ["apt-mark", "unhold"] + unholds
            holds = apt.run_apt_command(
                unhold_cmd,
                messages.EXECUTING_COMMAND_FAILED.format(
                    command=" ".join(unhold_cmd)
                ),
            )

    def setup_apt_config(self, progress: api.ProgressWrapper) -> None:
        """Setup apt config based on the resourceToken and directives.

        FIPS-specifically handle apt-mark unhold

        :raise UbuntuProError: on failure to setup any aspect of this apt
           configuration
        """
        self.unhold_packages(self.fips_pro_package_holds)
        super().setup_apt_config(progress)


class FIPSEntitlement(FIPSCommonEntitlement):
    name = "fips"
    title = messages.FIPS_TITLE
    description = messages.FIPS_DESCRIPTION
    help_text = messages.FIPS_HELP_TEXT
    origin = "UbuntuFIPS"
    pre_enable_msg = messages.PROMPT_FIPS_PRE_ENABLE

    @property
    def incompatible_services(self) -> Tuple[EntitlementWithMessage, ...]:
        from uaclient.entitlements.livepatch import LivepatchEntitlement
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            EntitlementWithMessage(
                LivepatchEntitlement, messages.LIVEPATCH_INVALIDATES_FIPS
            ),
            EntitlementWithMessage(
                FIPSUpdatesEntitlement, messages.FIPS_UPDATES_INVALIDATES_FIPS
            ),
            EntitlementWithMessage(
                RealtimeKernelEntitlement, messages.REALTIME_FIPS_INCOMPATIBLE
            ),
        )

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        static_affordances = super().static_affordances

        fips_updates = FIPSUpdatesEntitlement(cfg=self.cfg)
        enabled_status = ApplicationStatus.ENABLED
        is_fips_updates_enabled = bool(
            fips_updates.application_status()[0] == enabled_status
        )

        services_once_enabled_obj = services_once_enabled_file.read()
        fips_updates_once_enabled = (
            services_once_enabled_obj.fips_updates
            if services_once_enabled_obj
            else False
        )

        return static_affordances + (
            (
                messages.FIPS_ERROR_WHEN_FIPS_UPDATES_ENABLED.format(
                    fips=self.title, fips_updates=fips_updates.title
                ),
                lambda: is_fips_updates_enabled,
                False,
            ),
            (
                messages.FIPS_ERROR_WHEN_FIPS_UPDATES_ONCE_ENABLED.format(
                    fips=self.title, fips_updates=fips_updates.title
                ),
                lambda: fips_updates_once_enabled,
                False,
            ),
        )

    def _perform_enable(self, progress: api.ProgressWrapper) -> bool:
        cloud_type, error = get_cloud_type()
        if cloud_type is None and error == NoCloudTypeReason.CLOUD_ID_ERROR:
            LOG.warning(
                "Could not determine cloud, "
                "defaulting to generic FIPS package."
            )
            event.info(messages.FIPS_COULD_NOT_DETERMINE_CLOUD_DEFAULT_PACKAGE)
        if super()._perform_enable(progress):
            notices.remove(
                Notice.FIPS_INSTALL_OUT_OF_DATE,
            )
            return True

        return False


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):
    name = "fips-updates"
    title = messages.FIPS_UPDATES_TITLE
    origin = "UbuntuFIPSUpdates"
    description = messages.FIPS_UPDATES_DESCRIPTION
    help_text = messages.FIPS_UPDATES_HELP_TEXT
    pre_enable_msg = messages.PROMPT_FIPS_UPDATES_PRE_ENABLE

    @property
    def incompatible_services(self) -> Tuple[EntitlementWithMessage, ...]:
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            EntitlementWithMessage(
                FIPSEntitlement, messages.FIPS_INVALIDATES_FIPS_UPDATES
            ),
            EntitlementWithMessage(
                RealtimeKernelEntitlement,
                messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE,
            ),
        )

    def _perform_enable(self, progress: api.ProgressWrapper) -> bool:
        if super()._perform_enable(progress=progress):
            services_once_enabled_file.write(
                ServicesOnceEnabledData(fips_updates=True)
            )
            return True

        return False


class FIPSPreviewEntitlement(FIPSEntitlement):
    name = "fips-preview"
    title = messages.FIPS_PREVIEW_TITLE
    description = messages.FIPS_PREVIEW_DESCRIPTION
    help_text = messages.FIPS_PREVIEW_HELP_TEXT
    origin = "UbuntuFIPSPreview"
    pre_enable_msg = messages.PROMPT_FIPS_PREVIEW_PRE_ENABLE
    repo_key_file = "ubuntu-pro-fips-preview.gpg"

    @property
    def incompatible_services(self) -> Tuple[EntitlementWithMessage, ...]:
        return super().incompatible_services + (
            EntitlementWithMessage(
                FIPSEntitlement, messages.FIPS_INVALIDATES_FIPS_UPDATES
            ),
        )

    def _allow_fips_on_cloud_instance(
        self, series: str, cloud_id: str
    ) -> bool:
        # For fips-preview, we should not block the service
        # if there is no FIPS cloud-optimized kernel. That is
        # because this service is intended as an early access for
        # FIPS service, so users should be aware of the risks
        return True
