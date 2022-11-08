import logging
import os
from itertools import groupby
from typing import List, Optional, Tuple  # noqa: F401

from uaclient import apt, event_logger, exceptions, messages, system, util
from uaclient.clouds.identity import NoCloudTypeReason, get_cloud_type
from uaclient.entitlements import repo
from uaclient.entitlements.base import IncompatibleService
from uaclient.entitlements.entitlement_status import ApplicationStatus
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

CONDITIONAL_PACKAGES_EVERYWHERE = [
    "strongswan",
    "strongswan-hmac",
    "openssh-client",
    "openssh-server",
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
    repo_key_file = "ubuntu-advantage-fips.gpg"  # Same for fips & fips-updates
    FIPS_PROC_FILE = "/proc/sys/crypto/fips_enabled"

    # RELEASE_BLOCKER GH: #104, don't prompt for conf differences in FIPS
    # Review this fix to see if we want more general functionality for all
    # services. And security/CPC signoff on expected conf behavior.
    apt_noninteractive = True

    help_doc_url = "https://ubuntu.com/security/certifications#fips"

    fips_pro_package_holds = [
        "fips-initramfs",
        "libssl1.1",
        "libssl1.1-hmac",
        "libssl1.0.0",
        "libssl1.0.0-hmac",
        "libssl1.0.0",
        "libssl1.0.0-hmac",
        "linux-fips",
        "openssh-client",
        "openssh-client-hmac",
        "openssh-server",
        "openssh-server-hmac",
        "openssl",
        "strongswan",
        "strongswan-hmac",
        "libgcrypt20",
        "libgcrypt20-hmac",
        "fips-initramfs-generic",
    ]

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
        series = system.get_platform_info().get("series", "")

        if system.is_container():
            return FIPS_CONTAINER_CONDITIONAL_PACKAGES.get(series, [])

        return FIPS_CONDITIONAL_PACKAGES.get(series, [])

    def install_packages(
        self,
        package_list: Optional[List[str]] = None,
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
            event.info("Installing {title} packages".format(title=self.title))

        # We need to guarantee that the metapackage is installed.
        # While the other packages should still be installed, if they
        # fail, we should not block the enable operation.
        mandatory_packages = self.packages
        super().install_packages(
            package_list=mandatory_packages, verbose=False
        )

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
                super().install_packages(
                    package_list=[pkg], cleanup_on_failure=False, verbose=False
                )
            except exceptions.UserFacingError:
                event.info(
                    messages.FIPS_PACKAGE_NOT_AVAILABLE.format(
                        service=self.title, pkg=pkg
                    )
                )

    def _check_for_reboot_msg(
        self, operation: str, silent: bool = False
    ) -> None:
        """Check if user should be alerted that a reboot must be performed.

        @param operation: The operation being executed.
        @param silent: Boolean set True to silence print/log of messages
        """
        reboot_required = system.should_reboot()
        event.needs_reboot(reboot_required)
        if reboot_required:
            if not silent:
                event.info(
                    messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation=operation
                    )
                )
            if operation == "install":
                self.cfg.notice_file.add(
                    "", messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg
                )
            elif operation == "disable operation":
                self.cfg.notice_file.add(
                    "", messages.FIPS_DISABLE_REBOOT_REQUIRED
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

        series = system.get_platform_info().get("series", "")
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
            self.cfg.notice_file.try_remove(
                "", messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg
            )
            return super_status, super_msg

        if os.path.exists(self.FIPS_PROC_FILE):

            # We are now only removing the notice if there is no reboot
            # required information regarding the fips metapackage we install.
            if not system.should_reboot(set(self.packages)):
                self.cfg.notice_file.try_remove(
                    "", messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg
                )

            self.cfg.notice_file.try_remove(
                "", messages.FIPS_REBOOT_REQUIRED_MSG
            )
            if system.load_file(self.FIPS_PROC_FILE).strip() == "1":
                self.cfg.notice_file.try_remove(
                    "", messages.NOTICE_FIPS_MANUAL_DISABLE_URL
                )
                return super_status, super_msg
            else:
                self.cfg.notice_file.try_remove(
                    "", messages.FIPS_DISABLE_REBOOT_REQUIRED
                )
                self.cfg.notice_file.try_add(
                    "", messages.NOTICE_FIPS_MANUAL_DISABLE_URL
                )
                return (
                    ApplicationStatus.DISABLED,
                    messages.FIPS_PROC_FILE_ERROR.format(
                        file_name=self.FIPS_PROC_FILE
                    ),
                )
        else:
            self.cfg.notice_file.try_remove(
                "", messages.FIPS_DISABLE_REBOOT_REQUIRED
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
            env = {"DEBIAN_FRONTEND": "noninteractive"}
            apt_options = [
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
            ]
            apt.run_apt_command(
                ["apt-get", "remove", "--assume-yes"]
                + apt_options
                + list(remove_packages),
                messages.DISABLE_FAILED_TMPL.format(title=self.title),
                env=env,
            )

    def _perform_enable(self, silent: bool = False) -> bool:
        if super()._perform_enable(silent=silent):
            self.cfg.notice_file.try_remove(
                "", messages.NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD
            )
            self.cfg.notice_file.try_remove(
                "", messages.FIPS_REBOOT_REQUIRED_MSG
            )
            return True

        return False

    def setup_apt_config(self, silent: bool = False) -> None:
        """Setup apt config based on the resourceToken and directives.

        FIPS-specifically handle apt-mark unhold

        :raise UserFacingError: on failure to setup any aspect of this apt
           configuration
        """
        cmd = ["apt-mark", "showholds"]
        holds = apt.run_apt_command(cmd, " ".join(cmd) + " failed.")
        unholds = []
        for hold in holds.splitlines():
            if hold in self.fips_pro_package_holds:
                unholds.append(hold)
        if unholds:
            unhold_cmd = ["apt-mark", "unhold"] + unholds
            holds = apt.run_apt_command(
                unhold_cmd, " ".join(unhold_cmd) + " failed."
            )
        super().setup_apt_config(silent=silent)


class FIPSEntitlement(FIPSCommonEntitlement):

    name = "fips"
    title = "FIPS"
    description = "NIST-certified core packages"
    origin = "UbuntuFIPS"

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        from uaclient.entitlements.livepatch import LivepatchEntitlement
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            IncompatibleService(
                LivepatchEntitlement, messages.LIVEPATCH_INVALIDATES_FIPS
            ),
            IncompatibleService(
                FIPSUpdatesEntitlement, messages.FIPS_UPDATES_INVALIDATES_FIPS
            ),
            IncompatibleService(
                RealtimeKernelEntitlement, messages.REALTIME_FIPS_INCOMPATIBLE
            ),
        )

    @property
    def static_affordances(self) -> Tuple[StaticAffordance, ...]:
        static_affordances = super().static_affordances

        fips_updates = FIPSUpdatesEntitlement(self.cfg)
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

    @property
    def messaging(self) -> MessagingOperationsDict:
        post_enable = None  # type: Optional[MessagingOperations]
        if system.is_container():
            pre_enable_prompt = (
                messages.PROMPT_FIPS_CONTAINER_PRE_ENABLE.format(
                    title=self.title
                )
            )
            post_enable = [messages.FIPS_RUN_APT_UPGRADE]
        else:
            pre_enable_prompt = messages.PROMPT_FIPS_PRE_ENABLE

        return {
            "pre_enable": [
                (
                    util.prompt_for_confirmation,
                    {"msg": pre_enable_prompt, "assume_yes": self.assume_yes},
                )
            ],
            "post_enable": post_enable,
            "pre_disable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.PROMPT_FIPS_PRE_DISABLE,
                        "assume_yes": self.assume_yes,
                    },
                )
            ],
        }

    def _perform_enable(self, silent: bool = False) -> bool:
        cloud_type, error = get_cloud_type()
        if cloud_type is None and error == NoCloudTypeReason.CLOUD_ID_ERROR:
            logging.warning(
                "Could not determine cloud, "
                "defaulting to generic FIPS package."
            )
        if super()._perform_enable(silent=silent):
            self.cfg.notice_file.try_remove(
                "", messages.FIPS_INSTALL_OUT_OF_DATE
            )
            return True

        return False


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = "fips-updates"
    title = "FIPS Updates"
    origin = "UbuntuFIPSUpdates"
    description = "NIST-certified core packages with priority security updates"

    @property
    def incompatible_services(self) -> Tuple[IncompatibleService, ...]:
        from uaclient.entitlements.realtime import RealtimeKernelEntitlement

        return (
            IncompatibleService(
                FIPSEntitlement, messages.FIPS_INVALIDATES_FIPS_UPDATES
            ),
            IncompatibleService(
                RealtimeKernelEntitlement,
                messages.REALTIME_FIPS_UPDATES_INCOMPATIBLE,
            ),
        )

    @property
    def messaging(self) -> MessagingOperationsDict:
        post_enable = None  # type: Optional[MessagingOperations]
        if system.is_container():
            pre_enable_prompt = (
                messages.PROMPT_FIPS_CONTAINER_PRE_ENABLE.format(
                    title=self.title
                )
            )
            post_enable = [messages.FIPS_RUN_APT_UPGRADE]
        else:
            pre_enable_prompt = messages.PROMPT_FIPS_UPDATES_PRE_ENABLE

        return {
            "pre_enable": [
                (
                    util.prompt_for_confirmation,
                    {"msg": pre_enable_prompt, "assume_yes": self.assume_yes},
                )
            ],
            "post_enable": post_enable,
            "pre_disable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": messages.PROMPT_FIPS_PRE_DISABLE,
                        "assume_yes": self.assume_yes,
                    },
                )
            ],
        }

    def _perform_enable(self, silent: bool = False) -> bool:
        if super()._perform_enable(silent=silent):
            self.cfg.notice_file.try_remove(
                "", messages.FIPS_DISABLE_REBOOT_REQUIRED
            )

            services_once_enabled_file.write(
                ServicesOnceEnabledData(fips_updates=True)
            )
            return True

        return False
