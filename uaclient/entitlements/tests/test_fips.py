"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
import itertools
import mock
from functools import partial

import pytest

from uaclient import apt
from uaclient import defaults
from uaclient import status, util
from uaclient.entitlements.fips import FIPSEntitlement, FIPSUpdatesEntitlement
from uaclient import exceptions


M_PATH = "uaclient.entitlements.fips."
M_REPOPATH = "uaclient.entitlements.repo."
M_GETPLATFORM = M_REPOPATH + "util.get_platform_info"


@pytest.fixture(params=[FIPSEntitlement, FIPSUpdatesEntitlement])
def fips_entitlement_factory(request, entitlement_factory):
    """Parameterized fixture so we apply all tests to both FIPS and Updates"""
    additional_packages = [
        "fips-initramfs",
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

    return partial(
        entitlement_factory,
        request.param,
        additional_packages=additional_packages,
    )


@pytest.fixture
def entitlement(fips_entitlement_factory):
    return fips_entitlement_factory()


class TestFIPSEntitlementDefaults:
    def test_default_repo_key_file(self, entitlement):
        """GPG keyring file is the same for both FIPS and FIPS with Updates"""
        assert entitlement.repo_key_file == "ubuntu-advantage-fips.gpg"

    def test_default_repo_pinning(self, entitlement):
        """FIPS and FIPS with Updates repositories are pinned."""
        assert entitlement.repo_pin_priority == 1001

    @pytest.mark.parametrize("assume_yes", (True, False))
    def test_messaging_passes_assume_yes(
        self, assume_yes, fips_entitlement_factory
    ):
        """FIPS and FIPS Updates pass assume_yes into messaging args"""
        entitlement = fips_entitlement_factory(assume_yes=assume_yes)
        expected_msging = {
            "fips": {
                "pre_enable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": status.PROMPT_FIPS_PRE_ENABLE,
                        },
                    )
                ],
                "post_enable": [
                    status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="install"
                    )
                ],
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": status.PROMPT_FIPS_PRE_DISABLE,
                        },
                    )
                ],
                "post_disable": [
                    status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="disable operation"
                    )
                ],
            },
            "fips-updates": {
                "pre_enable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "msg": status.PROMPT_FIPS_UPDATES_PRE_ENABLE,
                            "assume_yes": assume_yes,
                        },
                    )
                ],
                "post_enable": [
                    status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="install"
                    )
                ],
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": status.PROMPT_FIPS_PRE_DISABLE,
                        },
                    )
                ],
                "post_disable": [
                    status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="disable operation"
                    )
                ],
            },
        }
        if entitlement.name in expected_msging:
            assert expected_msging[entitlement.name] == entitlement.messaging
        else:
            assert False, "Unknown entitlement {}".format(entitlement.name)


class TestFIPSEntitlementCanEnable:
    def test_can_enable_true_on_entitlement_inactive(
        self, capsys, entitlement
    ):
        """When entitlement is disabled, can_enable returns True."""
        with mock.patch.object(
            entitlement,
            "applicability_status",
            return_value=(status.ApplicabilityStatus.APPLICABLE, ""),
        ):
            with mock.patch.object(
                entitlement,
                "application_status",
                return_value=(status.ApplicationStatus.DISABLED, ""),
            ):
                assert True is entitlement.can_enable()
        assert ("", "") == capsys.readouterr()


class TestFIPSEntitlementEnable:
    def test_enable_configures_apt_sources_and_auth_files(self, entitlement):
        """When entitled, configure apt repo auth token, pinning and url."""
        patched_packages = ["a", "b"]
        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch("uaclient.apt.add_auth_apt_repo")
            )
            m_add_pinning = stack.enter_context(
                mock.patch("uaclient.apt.add_ppa_pinning")
            )
            m_subp = stack.enter_context(
                mock.patch("uaclient.util.subp", return_value=("", ""))
            )
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, "can_enable")
            )
            stack.enter_context(
                mock.patch(M_REPOPATH + "handle_message_operations")
            )
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
            )
            stack.enter_context(mock.patch(M_REPOPATH + "os.path.exists"))
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), "packages", m_packages)
            )

            m_can_enable.return_value = True

            assert True is entitlement.enable()

        repo_url = "http://{}".format(entitlement.name.upper())
        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-{}-xenial.list".format(
                    entitlement.name
                ),
                repo_url,
                "{}-token".format(entitlement.name),
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]
        apt_pinning_calls = [
            mock.call(
                "/etc/apt/preferences.d/ubuntu-{}-xenial".format(
                    entitlement.name
                ),
                repo_url,
                entitlement.origin,
                1001,
            )
        ]
        install_cmd = mock.call(
            ["apt-get", "install", "--assume-yes"] + patched_packages,
            capture=True,
            retry_sleeps=apt.APT_RETRIES,
        )

        subp_calls = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
            ),
            install_cmd,
        ]

        assert [mock.call(silent=mock.ANY)] == m_can_enable.call_args_list
        assert add_apt_calls == m_add_apt.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
        assert subp_calls == m_subp.call_args_list

    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_enable_returns_false_on_can_enable_false(
        self, m_platform_info, entitlement
    ):
        """When can_enable is false enable returns false and noops."""
        with mock.patch.object(entitlement, "can_enable", return_value=False):
            with mock.patch(M_REPOPATH + "handle_message_operations"):
                assert False is entitlement.enable()
        assert 0 == m_platform_info.call_count

    @mock.patch("uaclient.apt.add_auth_apt_repo")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_enable_returns_false_on_missing_suites_directive(
        self, m_platform_info, m_add_apt, fips_entitlement_factory
    ):
        """When directives do not contain suites returns false."""
        entitlement = fips_entitlement_factory(suites=[])

        with mock.patch.object(entitlement, "can_enable", return_value=True):
            with mock.patch(M_REPOPATH + "handle_message_operations"):
                with pytest.raises(exceptions.UserFacingError) as excinfo:
                    entitlement.enable()
        error_msg = "Empty {} apt suites directive from {}".format(
            entitlement.name, defaults.BASE_CONTRACT_URL
        )
        assert error_msg == excinfo.value.msg
        assert 0 == m_add_apt.call_count

    def test_enable_errors_on_repo_pin_but_invalid_origin(self, entitlement):
        """Error when no valid origin is provided on a pinned entitlemnt."""
        entitlement.origin = None  # invalid value

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch("uaclient.apt.add_auth_apt_repo")
            )
            m_add_pinning = stack.enter_context(
                mock.patch("uaclient.apt.add_ppa_pinning")
            )
            stack.enter_context(mock.patch.object(entitlement, "can_enable"))
            stack.enter_context(
                mock.patch(M_REPOPATH + "handle_message_operations")
            )
            m_remove_apt_config = stack.enter_context(
                mock.patch.object(entitlement, "remove_apt_config")
            )
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
            )
            stack.enter_context(mock.patch(M_REPOPATH + "os.path.exists"))

            with pytest.raises(exceptions.UserFacingError) as excinfo:
                entitlement.enable()

        error_msg = (
            "Cannot setup apt pin. Empty apt repo origin value 'None'.\n"
            "Could not enable {}.".format(entitlement.title)
        )
        assert error_msg == excinfo.value.msg
        assert 0 == m_add_apt.call_count
        assert 0 == m_add_pinning.call_count
        assert 0 == m_remove_apt_config.call_count

    def test_failure_to_install_doesnt_remove_packages(self, entitlement):
        def fake_subp(cmd, *args, **kwargs):
            if "install" in cmd:
                raise util.ProcessExecutionError(cmd)
            return ("", "")

        with contextlib.ExitStack() as stack:
            m_subp = stack.enter_context(
                mock.patch("uaclient.util.subp", side_effect=fake_subp)
            )
            stack.enter_context(
                mock.patch.object(entitlement, "can_enable", return_value=True)
            )
            stack.enter_context(
                mock.patch(M_REPOPATH + "handle_message_operations")
            )
            stack.enter_context(
                mock.patch.object(
                    entitlement, "setup_apt_config", return_value=True
                )
            )
            stack.enter_context(
                mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
            )
            stack.enter_context(mock.patch(M_REPOPATH + "os.path.exists"))

            with pytest.raises(exceptions.UserFacingError) as excinfo:
                entitlement.enable()
            error_msg = "Could not enable {}.".format(entitlement.title)
            assert error_msg == excinfo.value.msg

        for call in m_subp.call_args_list:
            assert "remove" not in call[0][0]


def _fips_pkg_combinations():
    """Construct all combinations of fips_packages and expected installs"""
    fips_packages = {
        "libssl1.0.0": {"libssl1.0.0-hmac"},
        "openssh-client": {"openssh-client-hmac"},
        "openssh-server": {"openssh-server-hmac"},
        "openssl": set(),
        "strongswan": {"strongswan-hmac"},
    }

    items = [  # These are the items that we will combine together
        (pkg_name, [pkg_name] + list(extra_pkgs))
        for pkg_name, extra_pkgs in fips_packages.items()
    ]
    # This produces combinations in all possible combination lengths
    combinations = itertools.chain.from_iterable(
        itertools.combinations(items, n) for n in range(1, len(items))
    )
    ret = []
    # This for loop flattens each combination together in to a single
    # (installed_packages, expected_installs) item
    for combination in combinations:
        installed_packages, expected_installs = [], []
        for pkg, installs in combination:
            installed_packages.append(pkg)
            expected_installs.extend(installs)
        ret.append((installed_packages, expected_installs))
    return ret


class TestFipsEntitlementPackages:
    @mock.patch(M_PATH + "apt.get_installed_packages", return_value=[])
    def test_packages_is_list(self, _mock, entitlement):
        """RepoEntitlement.enable will fail if it isn't"""
        assert isinstance(entitlement.packages, list)

    @mock.patch(M_PATH + "apt.get_installed_packages", return_value=[])
    def test_fips_required_packages_included(self, _mock, entitlement):
        """The fips_required_packages should always be in .packages"""
        assert entitlement.fips_required_packages.issubset(
            entitlement.packages
        )

    @pytest.mark.parametrize(
        "installed_packages,expected_installs", _fips_pkg_combinations()
    )
    @mock.patch(M_PATH + "apt.get_installed_packages")
    def test_currently_installed_packages_are_included_in_packages(
        self,
        m_get_installed_packages,
        entitlement,
        installed_packages,
        expected_installs,
    ):
        """If FIPS packages are already installed, upgrade them"""
        m_get_installed_packages.return_value = list(installed_packages)
        full_expected_installs = (
            list(entitlement.fips_required_packages) + expected_installs
        )
        assert full_expected_installs == entitlement.packages

    @mock.patch(M_PATH + "apt.get_installed_packages")
    def test_multiple_packages_calls_dont_mutate_state(
        self, m_get_installed_packages, entitlement
    ):
        # Make it appear like all packages are installed
        m_get_installed_packages.return_value.__contains__.return_value = True

        before = (
            copy.deepcopy(entitlement.fips_required_packages),
            copy.deepcopy(entitlement.fips_packages),
        )

        assert entitlement.packages

        after = (
            copy.deepcopy(entitlement.fips_required_packages),
            copy.deepcopy(entitlement.fips_packages),
        )

        assert before == after


class TestFIPSEntitlementDisable:
    @pytest.mark.parametrize("silent", [False, True])
    @mock.patch("uaclient.util.get_platform_info")
    def test_disable_returns_false_and_does_nothing(
        self, m_platform_info, entitlement, silent, capsys
    ):
        """When can_disable is false disable returns false and noops."""
        with mock.patch("uaclient.apt.remove_auth_apt_repo") as m_remove_apt:
            assert False is entitlement.disable(silent)
        assert 0 == m_remove_apt.call_count

        expected_stdout = ""
        if not silent:
            expected_stdout = "Warning: no option to disable {}\n".format(
                entitlement.title
            )
        assert (expected_stdout, "") == capsys.readouterr()


class TestFIPSEntitlementApplicationStatus:
    @pytest.mark.parametrize(
        "super_application_status",
        [
            s
            for s in status.ApplicationStatus
            if s is not status.ApplicationStatus.ENABLED
        ],
    )
    def test_non_enabled_passed_through(
        self, entitlement, super_application_status
    ):
        msg = "sure is some status here"
        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(super_application_status, msg),
        ):
            application_status = entitlement.application_status()

        assert (super_application_status, msg) == application_status

    @pytest.mark.parametrize(
        "platform_info,expected_status,expected_msg",
        (
            (
                {"kernel": "4.4.0-1002-fips"},
                status.ApplicationStatus.ENABLED,
                None,
            ),
            (
                {"kernel": "4.4.0-148-generic"},
                status.ApplicationStatus.ENABLED,
                "Reboot to FIPS kernel required",
            ),
        ),
    )
    def test_kernels_are_used_to_detemine_application_status_message(
        self, entitlement, platform_info, expected_status, expected_msg
    ):
        msg = "sure is some status here"
        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(status.ApplicationStatus.ENABLED, msg),
        ):
            with mock.patch(
                M_PATH + "util.get_platform_info", return_value=platform_info
            ):
                application_status = entitlement.application_status()

        if expected_msg is None:
            # None indicates that we expect the super-class message to be
            # passed through
            expected_msg = msg
        assert (expected_status, expected_msg) == application_status

    def test_fips_does_not_show_enabled_when_fips_updates_is(
        self, entitlement
    ):
        with mock.patch(M_PATH + "util.subp") as m_subp:
            m_subp.return_value = (
                "1001 http://FIPS-UPDATES/ubuntu"
                " xenial-updates/main amd64 Packages\n",
                "",
            )

            application_status, _ = entitlement.application_status()

        expected_status = status.ApplicationStatus.DISABLED
        if isinstance(entitlement, FIPSUpdatesEntitlement):
            expected_status = status.ApplicationStatus.ENABLED

        assert expected_status == application_status
