import os
import re

from itertools import groupby

from uaclient import apt
from uaclient.entitlements import repo
from uaclient.clouds.identity import get_cloud_type
from uaclient import exceptions, status, util

try:
    from typing import Any, Callable, Dict, List, Set, Tuple, Union  # noqa

    StaticAffordance = Tuple[str, Callable[[], Any], bool]
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class FIPSCommonEntitlement(repo.RepoEntitlement):

    repo_pin_priority = 1001
    repo_key_file = "ubuntu-advantage-fips.gpg"  # Same for fips & fips-updates
    FIPS_PROC_FILE = "/proc/sys/crypto/fips_enabled"

    # RELEASE_BLOCKER GH: #104, don't prompt for conf differences in FIPS
    # Review this fix to see if we want more general functionality for all
    # services. And security/CPC signoff on expected conf behavior.
    apt_noninteractive = True

    help_doc_url = "https://ubuntu.com/security/certifications#fips"
    _incompatible_services = ["livepatch"]

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
        conditional_packages = [
            "strongswan",
            "strongswan-hmac",
            "openssh-client",
            "openssh-server",
        ]

        series = util.get_platform_info().get("series", "")
        # On Focal, we don't have the openssh hmac packages.
        # Therefore, we will not try to install them during
        # when enabling any FIPS service
        if series in ("xenial", "bionic"):
            conditional_packages += [
                "openssh-client-hmac",
                "openssh-server-hmac",
            ]

        return conditional_packages

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
        installed_packages = apt.get_installed_packages()
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
                print(
                    status.MESSAGE_FIPS_PACKAGE_NOT_AVAILABLE.format(
                        service=self.title, pkg=pkg
                    )
                )

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
            if operation == "install":
                self.cfg.add_notice("", status.MESSAGE_FIPS_REBOOT_REQUIRED)
            elif operation == "disable operation":
                self.cfg.add_notice(
                    "", status.MESSAGE_FIPS_DISABLE_REBOOT_REQUIRED
                )

    def _allow_fips_on_cloud_instance(
        self, series: str, cloud_id: str
    ) -> bool:
        """Return False when FIPS is allowed on this cloud and series.

        On Xenial Azure and GCP there will be no cloud-optimized kernel so
        block default ubuntu-fips enable. This can be overridden in
        config with features.allow_xenial_fips_on_cloud.

        GCP doesn't yet have a cloud-optimized kernel or metapackage so
        block enable of fips if the contract does not specify ubuntu-gcp-fips.
        This also can be overridden in config with
        features.allow_default_fips_metapackage_on_gcp.


        :return: False when this cloud, series or config override allows FIPS.
        """
        if cloud_id not in ("azure", "gce"):
            return True

        if cloud_id == "gce":
            if util.is_config_value_true(
                config=self.cfg.cfg,
                path_to_value="features.allow_default_fips_metapackage_on_gcp",
            ):
                return True
            return bool("ubuntu-gcp-fips" in super().packages)

        # Azure FIPS cloud support
        if series == "xenial":
            if util.is_config_value_true(
                config=self.cfg.cfg,
                path_to_value="features.allow_xenial_fips_on_cloud",
            ):
                return True
            else:
                return False

        return True

    @property
    def static_affordances(self) -> "Tuple[StaticAffordance, ...]":
        # Use a lambda so we can mock util.is_container in tests
        cloud_titles = {"azure": "an Azure", "gce": "a GCP"}
        cloud_id = get_cloud_type() or ""

        series = util.get_platform_info().get("series", "")
        blocked_message = status.MESSAGE_FIPS_BLOCK_ON_CLOUD.format(
            series=series.title(), cloud=cloud_titles.get(cloud_id)
        )
        return (
            (
                "Cannot install {} on a container.".format(self.title),
                lambda: util.is_container(),
                False,
            ),
            (
                blocked_message,
                lambda: self._allow_fips_on_cloud_instance(series, cloud_id),
                True,
            ),
        )

    def _replace_metapackage_on_cloud_instance(
        self, packages: "List[str]"
    ) -> "List[str]":
        """
        Identify correct metapackage to be used if in a cloud instance.

        Currently, the contract backend is not delivering the right
        metapackage on a Bionic Azure or AWS cloud instance. For those
        clouds, we have cloud specific fips metapackages and we should
        use them. We are now performing that correction here, but this
        is a temporary fix.
        """
        cfg_disable_fips_metapackage_override = util.is_config_value_true(
            config=self.cfg.cfg,
            path_to_value="features.disable_fips_metapackage_override",
        )

        if cfg_disable_fips_metapackage_override:
            return packages

        series = util.get_platform_info().get("series")
        if series != "bionic":
            return packages

        cloud_match = re.match(
            r"^(?P<cloud>(azure|aws)).*", get_cloud_type() or ""
        )
        cloud_id = cloud_match.group("cloud") if cloud_match else ""

        if cloud_id not in ("azure", "aws"):
            return packages

        cloud_metapkg = "ubuntu-{}-fips".format(cloud_id)
        # Replace only the ubuntu-fips meta package if exists
        return [
            cloud_metapkg if pkg == "ubuntu-fips" else pkg for pkg in packages
        ]

    @property
    def packages(self) -> "List[str]":
        packages = super().packages
        return self._replace_metapackage_on_cloud_instance(packages)

    def application_status(self) -> "Tuple[status.ApplicationStatus, str]":
        super_status, super_msg = super().application_status()

        if os.path.exists(self.FIPS_PROC_FILE):
            self.cfg.remove_notice("", status.MESSAGE_FIPS_REBOOT_REQUIRED)
            if util.load_file(self.FIPS_PROC_FILE).strip() == "1":
                self.cfg.remove_notice(
                    "", status.NOTICE_FIPS_MANUAL_DISABLE_URL
                )
                return super_status, super_msg
            else:
                self.cfg.remove_notice(
                    "", status.MESSAGE_FIPS_DISABLE_REBOOT_REQUIRED
                )
                self.cfg.add_notice("", status.NOTICE_FIPS_MANUAL_DISABLE_URL)
                return (
                    status.ApplicationStatus.DISABLED,
                    "{} is not set to 1".format(self.FIPS_PROC_FILE),
                )
        else:
            self.cfg.remove_notice(
                "", status.MESSAGE_FIPS_DISABLE_REBOOT_REQUIRED
            )

        if super_status != status.ApplicationStatus.ENABLED:
            return super_status, super_msg
        return (
            status.ApplicationStatus.ENABLED,
            "Reboot to FIPS kernel required",
        )

    def remove_packages(self) -> None:
        """Remove fips meta package to disable the service.

        FIPS meta-package will unset grub config options which will deactivate
        FIPS on any related packages.
        """
        installed_packages = set(apt.get_installed_packages())
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
                status.MESSAGE_DISABLE_FAILED_TMPL.format(title=self.title),
                env=env,
            )

    def _perform_enable(self) -> bool:
        if super()._perform_enable():
            self.cfg.remove_notice(
                "", status.NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD
            )
            return True

        return False


class FIPSEntitlement(FIPSCommonEntitlement):

    name = "fips"
    title = "FIPS"
    description = "NIST-certified core packages"
    origin = "UbuntuFIPS"

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
    ]

    @property
    def static_affordances(self) -> "Tuple[StaticAffordance, ...]":
        static_affordances = super().static_affordances

        fips_update = FIPSUpdatesEntitlement(self.cfg)
        enabled_status = status.ApplicationStatus.ENABLED
        is_fips_update_enabled = bool(
            fips_update.application_status()[0] == enabled_status
        )

        services_once_enabled = (
            self.cfg.read_cache("services-once-enabled") or {}
        )
        fips_updates_once_enabled = services_once_enabled.get(
            fips_update.name, False
        )

        return static_affordances + (
            (
                "Cannot enable {} when {} is enabled.".format(
                    self.title, fips_update.title
                ),
                lambda: is_fips_update_enabled,
                False,
            ),
            (
                "Cannot enable {} because {} was once enabled.".format(
                    self.title, fips_update.title
                ),
                lambda: fips_updates_once_enabled,
                False,
            ),
        )

    @property
    def messaging(
        self
    ) -> "Dict[str, List[Union[str, Tuple[Callable, Dict]]]]":
        return {
            "pre_enable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": status.PROMPT_FIPS_PRE_ENABLE,
                        "assume_yes": self.assume_yes,
                    },
                )
            ],
            "pre_disable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "assume_yes": self.assume_yes,
                        "msg": status.PROMPT_FIPS_PRE_DISABLE,
                    },
                )
            ],
        }

    def setup_apt_config(self) -> None:
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
        super().setup_apt_config()

    def _perform_enable(self) -> bool:
        if super()._perform_enable():
            self.cfg.remove_notice("", status.MESSAGE_FIPS_INSTALL_OUT_OF_DATE)
            return True

        return False


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = "fips-updates"
    title = "FIPS Updates"
    origin = "UbuntuFIPSUpdates"
    description = "NIST-certified core packages with priority security updates"

    @property
    def messaging(
        self
    ) -> "Dict[str, List[Union[str, Tuple[Callable, Dict]]]]":
        return {
            "pre_enable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "msg": status.PROMPT_FIPS_UPDATES_PRE_ENABLE,
                        "assume_yes": self.assume_yes,
                    },
                )
            ],
            "pre_disable": [
                (
                    util.prompt_for_confirmation,
                    {
                        "assume_yes": self.assume_yes,
                        "msg": status.PROMPT_FIPS_PRE_DISABLE,
                    },
                )
            ],
        }

    def _perform_enable(self) -> bool:
        if super()._perform_enable():
            services_once_enabled = (
                self.cfg.read_cache("services-once-enabled") or {}
            )
            services_once_enabled.update({self.name: True})
            self.cfg.write_cache(
                key="services-once-enabled", content=services_once_enabled
            )

            return True

        return False
