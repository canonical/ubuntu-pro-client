"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
import io
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
FIPS_ADDITIONAL_PACKAGES = ["ubuntu-fips"]


@pytest.fixture(params=[FIPSEntitlement, FIPSUpdatesEntitlement])
def fips_entitlement_factory(request, entitlement_factory):
    """Parameterized fixture so we apply all tests to both FIPS and Updates"""
    additional_packages = FIPS_ADDITIONAL_PACKAGES

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
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": status.PROMPT_FIPS_PRE_DISABLE,
                        },
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
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": status.PROMPT_FIPS_PRE_DISABLE,
                        },
                    )
                ],
            },
        }

        if entitlement.name in expected_msging:
            assert expected_msging[entitlement.name] == entitlement.messaging
        else:
            assert False, "Unknown entitlement {}".format(entitlement.name)


class TestFIPSEntitlementCanEnable:
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    def test_can_enable_true_on_entitlement_inactive(
        self, m_is_config_value_true, capsys, entitlement
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
                "/etc/apt/sources.list.d/ubuntu-{}.list".format(
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
                "/etc/apt/preferences.d/ubuntu-{}".format(entitlement.name),
                repo_url,
                entitlement.origin,
                1001,
            )
        ]
        install_cmd = mock.call(
            [
                "apt-get",
                "install",
                "--assume-yes",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
            ]
            + patched_packages,
            capture=True,
            retry_sleeps=apt.APT_RETRIES,
            env={"DEBIAN_FRONTEND": "noninteractive"},
        )

        if isinstance(entitlement, FIPSEntitlement):
            subp_calls = [
                mock.call(
                    ["apt-mark", "showholds"],
                    capture=True,
                    retry_sleeps=apt.APT_RETRIES,
                    env={},
                )
            ]
        else:
            subp_calls = []
        subp_calls.extend(
            [
                mock.call(
                    ["apt-get", "update"],
                    capture=True,
                    retry_sleeps=apt.APT_RETRIES,
                    env={},
                ),
                install_cmd,
            ]
        )

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

    def test_failure_to_install_removes_apt_auth(self, entitlement, tmpdir):

        authfile = tmpdir.join("90ubuntu-advantage")
        authfile.write("")

        def fake_subp(cmd, *args, **kwargs):
            if "install" in cmd:
                raise util.ProcessExecutionError(cmd)
            return ("", "")

        with contextlib.ExitStack() as stack:
            stack.enter_context(
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
            m_remove_apt_config = stack.enter_context(
                mock.patch.object(
                    entitlement, "remove_apt_config", return_value=True
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

        assert 1 == m_remove_apt_config.call_count

    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    @mock.patch("uaclient.util.prompt_for_confirmation", return_value=False)
    @mock.patch("uaclient.entitlements.repo.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_livepatch_service_is_enabled(
        self,
        m_is_container,
        m_handle_message_op,
        m_prompt,
        m_is_config_value_true,
        entitlement,
    ):
        m_handle_message_op.return_value = True
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            with mock.patch.object(
                entitlement, "_prevent_fips_on_xenial_cloud_instances"
            ) as m_prevent_xenial_on_cloud:
                m_prevent_xenial_on_cloud.return_value = False
                m_livepatch.return_value = (
                    status.ApplicationStatus.ENABLED,
                    "",
                )
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    entitlement.enable()

        expected_msg = "Cannot enable {} when Livepatch is enabled".format(
            entitlement.title
        )
        assert expected_msg.strip() in fake_stdout.getvalue().strip()

    @mock.patch("uaclient.entitlements.repo.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_fips_update_service_is_enabled(
        self, m_is_container, m_handle_message_op, entitlement_factory
    ):
        m_handle_message_op.return_value = True
        fips_entitlement = entitlement_factory(FIPSEntitlement)
        base_path = "uaclient.entitlements.fips.FIPSUpdatesEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_fips_update:
            with mock.patch.object(
                fips_entitlement, "_prevent_fips_on_xenial_cloud_instances"
            ) as m_prevent_xenial_on_cloud:
                m_prevent_xenial_on_cloud.return_value = False
                m_fips_update.return_value = (
                    status.ApplicationStatus.ENABLED,
                    "",
                )
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    fips_entitlement.enable()

        expected_msg = "Cannot enable FIPS when FIPS Updates is enabled"
        assert expected_msg.strip() == fake_stdout.getvalue().strip()

    @mock.patch("uaclient.entitlements.fips.get_cloud_type")
    @mock.patch("uaclient.entitlements.repo.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_on_xenial_cloud_instance(
        self, m_is_container, m_handle_message_op, m_cloud_type, entitlement
    ):
        m_handle_message_op.return_value = True
        m_cloud_type.return_value = "azure"
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            with mock.patch.object(
                entitlement, "_prevent_fips_on_xenial_cloud_instances"
            ) as m_prevent_xenial_on_cloud:
                m_prevent_xenial_on_cloud.return_value = True
                m_livepatch.return_value = (
                    status.ApplicationStatus.DISABLED,
                    "",
                )
                fake_stdout = io.StringIO()
                with contextlib.redirect_stdout(fake_stdout):
                    entitlement.enable()

        expected_msg = """\
        Ubuntu Xenial does not provide an Azure optimized FIPS kernel"""
        assert expected_msg.strip() in fake_stdout.getvalue().strip()

    @pytest.mark.parametrize("allow_xenial_fips_on_cloud", ((True), (False)))
    @pytest.mark.parametrize("cloud_id", (("aws"), ("gce"), ("azure"), (None)))
    @pytest.mark.parametrize(
        "series", (("trusty"), ("xenial"), ("bionic"), ("focal"))
    )
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.entitlements.fips.get_cloud_type")
    @mock.patch("uaclient.util.is_config_value_true")
    def test_prevent_fips_on_xenial_cloud_instances(
        self,
        m_is_config_value_true,
        m_get_cloud_type,
        m_platform_info,
        series,
        cloud_id,
        allow_xenial_fips_on_cloud,
        entitlement,
    ):
        m_is_config_value_true.return_value = allow_xenial_fips_on_cloud
        m_get_cloud_type.return_value = cloud_id
        m_platform_info.return_value = {"series": series}

        actual_value = entitlement._prevent_fips_on_xenial_cloud_instances()

        if all(
            [
                not allow_xenial_fips_on_cloud,
                cloud_id in ("azure", "gce"),
                series == "xenial",
            ]
        ):
            assert actual_value
        else:
            assert not actual_value


class TestFIPSEntitlementRemovePackages:
    @pytest.mark.parametrize("installed_pkgs", (["sl"], ["ubuntu-fips", "sl"]))
    @mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
    @mock.patch(M_PATH + "util.subp")
    @mock.patch(M_PATH + "apt.get_installed_packages")
    def test_remove_packages_only_removes_if_package_is_installed(
        self,
        m_get_installed_packages,
        m_subp,
        _m_get_platform,
        installed_pkgs,
        entitlement,
    ):
        m_subp.return_value = ("success", "")
        m_get_installed_packages.return_value = installed_pkgs
        entitlement.remove_packages()
        remove_cmd = mock.call(
            [
                "apt-get",
                "remove",
                "--assume-yes",
                '-o Dpkg::Options::="--force-confdef"',
                '-o Dpkg::Options::="--force-confold"',
                "ubuntu-fips",
            ],
            capture=True,
            retry_sleeps=apt.APT_RETRIES,
            env={"DEBIAN_FRONTEND": "noninteractive"},
        )
        if "ubuntu-fips" in installed_pkgs:
            assert [remove_cmd] == m_subp.call_args_list
        else:
            assert 0 == m_subp.call_count


@mock.patch(M_REPOPATH + "handle_message_operations", return_value=True)
@mock.patch(
    "uaclient.util.get_platform_info", return_value={"series": "xenial"}
)
class TestFIPSEntitlementDisable:
    def test_disable_on_can_disable_true_removes_apt_config_and_packages(
        self,
        _m_platform_info,
        m_handle_message_operations,
        entitlement,
        tmpdir,
    ):
        """When can_disable, disable removes apt config and packages."""
        with mock.patch.object(entitlement, "can_disable", return_value=True):
            with mock.patch.object(
                entitlement, "remove_apt_config"
            ) as m_remove_apt_config:
                with mock.patch.object(
                    entitlement, "remove_packages"
                ) as m_remove_packages:
                    assert entitlement.disable(True)
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_remove_packages.call_args_list

    def test_disable_on_can_disable_true_removes_packages(
        self,
        _m_platform_info,
        m_handle_message_operations,
        entitlement,
        tmpdir,
    ):
        """When can_disable, disable removes apt configuration"""
        with mock.patch.object(entitlement, "can_disable", return_value=True):
            with mock.patch.object(
                entitlement, "remove_apt_config"
            ) as m_remove_apt_config:
                assert entitlement.disable(True)
        assert [mock.call()] == m_remove_apt_config.call_args_list


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
    def test_kernels_are_used_to_determine_application_status_message(
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


def _fips_pkg_combinations():
    """Construct all combinations of fips_packages and expected installs"""
    fips_packages = {
        "openssh-client": {"openssh-client-hmac"},
        "openssh-server": {"openssh-server-hmac"},
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


class TestFipsSetupAPTConfig:
    @pytest.mark.parametrize(
        "held_packages,unhold_packages",
        (
            ("", []),
            ("asdf\n", []),
            (
                "openssh-server\nlibssl1.1-hmac\nasdf\n",
                ["openssh-server", "libssl1.1-hmac"],
            ),
        ),
    )
    @mock.patch(M_REPOPATH + "RepoEntitlement.setup_apt_config")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_setup_apt_cofig_unmarks_held_fips_packages(
        self,
        run_apt_command,
        setup_apt_config,
        held_packages,
        unhold_packages,
        entitlement,
    ):
        """Unmark only fips-specific package holds if present."""
        run_apt_command.return_value = held_packages
        entitlement.setup_apt_config()
        if isinstance(entitlement, FIPSUpdatesEntitlement):
            expected_calls = []
        else:
            expected_calls = [
                mock.call(
                    ["apt-mark", "showholds"], "apt-mark showholds failed."
                )
            ]
            if unhold_packages:
                cmd = ["apt-mark", "unhold"] + unhold_packages
                expected_calls.append(
                    mock.call(cmd, " ".join(cmd) + " failed.")
                )
        assert expected_calls == run_apt_command.call_args_list
        assert [mock.call()] == setup_apt_config.call_args_list


class TestFipsEntitlementPackages:
    @mock.patch(M_PATH + "apt.get_installed_packages", return_value=[])
    @mock.patch("uaclient.util.get_platform_info")
    def test_packages_is_list(self, m_platform_info, _mock, entitlement):
        """RepoEntitlement.enable will fail if it isn't"""

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_platform_info.return_value = {"series": "test"}

        assert isinstance(entitlement.packages, list)

    @mock.patch(M_PATH + "apt.get_installed_packages", return_value=[])
    @mock.patch("uaclient.util.get_platform_info")
    def test_fips_required_packages_included(
        self, m_platform_info, _mock, entitlement
    ):
        """The fips_required_packages should always be in .packages"""

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_platform_info.return_value = {"series": "test"}

        assert set(FIPS_ADDITIONAL_PACKAGES).issubset(
            set(entitlement.packages)
        )

    @pytest.mark.parametrize(
        "installed_packages,expected_installs", _fips_pkg_combinations()
    )
    @mock.patch(M_PATH + "apt.get_installed_packages")
    @mock.patch("uaclient.util.get_platform_info")
    def test_currently_installed_packages_are_included_in_packages(
        self,
        m_platform_info,
        m_get_installed_packages,
        entitlement,
        installed_packages,
        expected_installs,
    ):
        """If FIPS packages are already installed, upgrade them"""
        m_get_installed_packages.return_value = list(installed_packages)

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_platform_info.return_value = {"series": "test"}

        full_expected_installs = FIPS_ADDITIONAL_PACKAGES + expected_installs
        assert sorted(full_expected_installs) == sorted(entitlement.packages)

    @mock.patch(M_PATH + "apt.get_installed_packages")
    @mock.patch("uaclient.util.get_platform_info")
    def test_multiple_packages_calls_dont_mutate_state(
        self, m_platform_info, m_get_installed_packages, entitlement
    ):
        # Make it appear like all packages are installed
        m_get_installed_packages.return_value.__contains__.return_value = True

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_platform_info.return_value = {"series": "test"}

        before = copy.deepcopy(entitlement.conditional_packages)

        assert entitlement.packages

        after = copy.deepcopy(entitlement.conditional_packages)

        assert before == after

    @pytest.mark.parametrize(
        "series", (("trusty"), ("xenial"), ("bionic"), ("focal"))
    )
    @pytest.mark.parametrize("cloud_id", (("azure"), ("aws"), ("gce"), (None)))
    @mock.patch(M_PATH + "get_cloud_type")
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.apt.get_installed_packages")
    def test_packages_are_override_when_bionic_cloud_instance(
        self,
        m_installed_packages,
        m_platform_info,
        m_get_cloud_type,
        cloud_id,
        series,
        entitlement,
    ):
        m_platform_info.return_value = {"series": series}
        m_get_cloud_type.return_value = cloud_id
        m_installed_packages.return_value = []
        packages = entitlement.packages

        if series == "bionic" and cloud_id in ("azure", "aws"):
            assert packages == ["ubuntu-{}-fips".format(cloud_id)]
        else:
            assert packages == ["ubuntu-fips"]
