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

    def disable(self, silent: bool = False) -> bool:
        """FIPS cannot be disabled, so simply display a message to the user"""
        if not silent:
            print("Warning: no option to disable {}".format(self.title))
        return False

    def _cleanup(self) -> None:
        """FIPS can't be cleaned up automatically, so don't do anything"""
        pass


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
