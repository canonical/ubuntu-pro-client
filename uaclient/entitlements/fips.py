from itertools import groupby

from uaclient import apt
from uaclient.entitlements import repo
from uaclient import status, util

try:
    from typing import Any, Callable, Dict, List, Set, Tuple, Union  # noqa

    StaticAffordance = Tuple[str, Callable[[], Any], bool]
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass


class FIPSCommonEntitlement(repo.RepoEntitlement):

    repo_pin_priority = 1001
    repo_key_file = "ubuntu-advantage-fips.gpg"  # Same for fips & fips-updates
    is_beta = True

    """
    Dictionary of conditional packages to be installed when
    enabling FIPS services. For example, if we are enabling
    FIPS services in a machine that has openssh-client installed,
    we will perform two actions:

    1. Upgrade the package to the FIPS version
    2. Install the correspinding hmac version of that package.
    """
    conditional_packages = [
        "openssh-client",
        "openssh-client-hmac",
        "openssh-server",
        "openssh-server-hmac",
        "strongswan",
        "strongswan-hmac",
    ]

    # RELEASE_BLOCKER GH: #104, don't prompt for conf differences in FIPS
    # Review this fix to see if we want more general functionality for all
    # services. And security/CPC signoff on expected conf behavior.
    apt_noninteractive = True

    help_doc_url = "https://ubuntu.com/security/certifications#fips"

    @property
    def static_affordances(self) -> "Tuple[StaticAffordance, ...]":
        # Use a lambda so we can mock util.is_container in tests
        from uaclient.entitlements.livepatch import LivepatchEntitlement

        livepatch_ent = LivepatchEntitlement(self.cfg)
        enabled_status = status.ApplicationStatus.ENABLED

        is_livepatch_enabled = bool(
            livepatch_ent.application_status()[0] == enabled_status
        )

        return (
            (
                "Cannot install {} on a container".format(self.title),
                lambda: util.is_container(),
                False,
            ),
            (
                "Cannot enable {} when Livepatch is enabled".format(
                    self.title
                ),
                lambda: is_livepatch_enabled,
                False,
            ),
        )

    @property
    def packages(self) -> "List[str]":
        packages = super().packages
        installed_packages = apt.get_installed_packages()

        pkg_groups = groupby(
            self.conditional_packages,
            key=lambda pkg_name: pkg_name.replace("-hmac", ""),
        )

        for pkg_name, pkg_list in pkg_groups:
            if pkg_name in installed_packages:
                packages += pkg_list

        return packages

    def application_status(self) -> "Tuple[status.ApplicationStatus, str]":
        super_status, super_msg = super().application_status()
        if super_status != status.ApplicationStatus.ENABLED:
            return super_status, super_msg
        running_kernel = util.get_platform_info()["kernel"]
        if running_kernel.endswith("-fips"):
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
                status.MESSAGE_ENABLED_FAILED_TMPL.format(title=self.title),
                env=env,
            )


class FIPSEntitlement(FIPSCommonEntitlement):

    name = "fips"
    title = "FIPS"
    description = "NIST-certified FIPS modules"
    origin = "UbuntuFIPS"

    @property
    def static_affordances(self) -> "Tuple[StaticAffordance, ...]":
        static_affordances = super().static_affordances

        fips_update = FIPSUpdatesEntitlement(self.cfg)
        enabled_status = status.ApplicationStatus.ENABLED
        is_fips_update_enabled = bool(
            fips_update.application_status()[0] == enabled_status
        )

        return static_affordances + (
            (
                "Cannot enable {} when {} is enabled".format(
                    self.title, fips_update.title
                ),
                lambda: is_fips_update_enabled,
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


class FIPSUpdatesEntitlement(FIPSCommonEntitlement):

    name = "fips-updates"
    title = "FIPS Updates"
    origin = "UbuntuFIPSUpdates"
    description = "Uncertified security updates to FIPS modules"

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
