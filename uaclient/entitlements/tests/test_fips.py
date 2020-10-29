"""Tests related to uaclient.entitlement.base module."""

import contextlib
import io
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
    additional_packages = ["ubuntu-fips"]

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

        subp_calls = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={},
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

    @mock.patch("uaclient.entitlements.repo.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_livepatch_service_is_enabled(
        self, m_is_container, m_handle_message_op, entitlement
    ):
        m_handle_message_op.return_value = True
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            m_livepatch.return_value = (status.ApplicationStatus.ENABLED, "")
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                entitlement.enable()

        expected_msg = "Cannot enable {} when Livepatch is enabled".format(
            entitlement.title
        )
        assert expected_msg.strip() == fake_stdout.getvalue().strip()

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
            m_fips_update.return_value = (status.ApplicationStatus.ENABLED, "")
            fake_stdout = io.StringIO()
            with contextlib.redirect_stdout(fake_stdout):
                fips_entitlement.enable()

        expected_msg = "Cannot enable FIPS when FIPS Updates is enabled"
        assert expected_msg.strip() == fake_stdout.getvalue().strip()


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
