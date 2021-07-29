"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
import io
import mock
import os
from functools import partial

import pytest

from uaclient import apt
from uaclient import defaults
from uaclient import status, util
from uaclient.entitlements.fips import FIPSEntitlement, FIPSUpdatesEntitlement
from uaclient.clouds.identity import NoCloudTypeReason
from uaclient import exceptions


M_PATH = "uaclient.entitlements.fips."
M_LIVEPATCH_PATH = "uaclient.entitlements.livepatch.LivepatchEntitlement."
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
    @pytest.mark.parametrize("series", (("xenial"), ("bionic"), ("focal")))
    @mock.patch("uaclient.util.get_platform_info")
    def test_condiotional_packages(
        self, m_get_platform_info, series, entitlement
    ):
        """Test conditional package respect series restrictions"""
        m_get_platform_info.return_value = {"series": series}

        conditional_packages = entitlement.conditional_packages
        if series == "focal":
            assert [
                "strongswan",
                "strongswan-hmac",
                "openssh-client",
                "openssh-server",
            ] == conditional_packages
        else:
            assert [
                "strongswan",
                "strongswan-hmac",
                "openssh-client",
                "openssh-server",
                "openssh-client-hmac",
                "openssh-server-hmac",
            ] == conditional_packages

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
                assert (True, None) == entitlement.can_enable()
        assert ("", "") == capsys.readouterr()


class TestFIPSEntitlementEnable:
    @mock.patch("uaclient.apt.setup_apt_proxy")
    def test_enable_configures_apt_sources_and_auth_files(
        self, m_setup_apt_proxy, entitlement
    ):
        """When entitled, configure apt repo auth token, pinning and url."""
        patched_packages = ["a", "b"]
        expected_conditional_packages = [
            "openssh-server",
            "openssh-server-hmac",
            "strongswan",
            "strongswan-hmac",
        ]

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch("uaclient.apt.add_auth_apt_repo")
            )
            m_add_pinning = stack.enter_context(
                mock.patch("uaclient.apt.add_ppa_pinning")
            )
            m_installed_pkgs = stack.enter_context(
                mock.patch(
                    "uaclient.apt.get_installed_packages",
                    return_value=["openssh-server", "strongswan"],
                )
            )
            m_subp = stack.enter_context(
                mock.patch("uaclient.util.subp", return_value=("", ""))
            )
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, "can_enable")
            )
            stack.enter_context(
                mock.patch("uaclient.util.handle_message_operations")
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

            m_can_enable.return_value = (True, None)

            assert (True, None) == entitlement.enable()

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

        install_cmd = []
        install_cmd.append(
            mock.call(
                [
                    "apt-get",
                    "install",
                    "--assume-yes",
                    "--allow-downgrades",
                    '-o Dpkg::Options::="--force-confdef"',
                    '-o Dpkg::Options::="--force-confold"',
                ]
                + patched_packages,
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={"DEBIAN_FRONTEND": "noninteractive"},
            )
        )

        for pkg in expected_conditional_packages:
            install_cmd.append(
                mock.call(
                    [
                        "apt-get",
                        "install",
                        "--assume-yes",
                        "--allow-downgrades",
                        '-o Dpkg::Options::="--force-confdef"',
                        '-o Dpkg::Options::="--force-confold"',
                        pkg,
                    ],
                    capture=True,
                    retry_sleeps=apt.APT_RETRIES,
                    env={"DEBIAN_FRONTEND": "noninteractive"},
                )
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
                )
            ]
        )
        subp_calls += install_cmd

        assert [mock.call()] == m_can_enable.call_args_list
        assert 1 == m_setup_apt_proxy.call_count
        assert 1 == m_installed_pkgs.call_count
        assert add_apt_calls == m_add_apt.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
        assert subp_calls == m_subp.call_args_list
        assert [
            ["", status.MESSAGE_FIPS_REBOOT_REQUIRED]
        ] == entitlement.cfg.read_cache("notices")

    @pytest.mark.parametrize(
        "fips_common_enable_return_value, expected_remove_notice_calls",
        [
            (True, [mock.call("", status.MESSAGE_FIPS_INSTALL_OUT_OF_DATE)]),
            (False, []),
        ],
    )
    @mock.patch(
        "uaclient.entitlements.fips.FIPSCommonEntitlement._perform_enable"
    )
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    def test_enable_removes_out_of_date_notice_on_success(
        self,
        m_remove_notice,
        m_fips_common_enable,
        fips_common_enable_return_value,
        expected_remove_notice_calls,
        entitlement_factory,
    ):
        m_fips_common_enable.return_value = fips_common_enable_return_value
        fips_entitlement = entitlement_factory(FIPSEntitlement)
        assert (
            fips_common_enable_return_value
            is fips_entitlement._perform_enable()
        )
        assert expected_remove_notice_calls == m_remove_notice.call_args_list

    @pytest.mark.parametrize(
        "repo_enable_return_value, expected_remove_notice_calls",
        [
            (
                True,
                [mock.call("", status.NOTICE_WRONG_FIPS_METAPACKAGE_ON_CLOUD)],
            ),
            (False, []),
        ],
    )
    @mock.patch("uaclient.entitlements.repo.RepoEntitlement._perform_enable")
    @mock.patch("uaclient.config.UAConfig.remove_notice")
    def test_enable_removes_wrong_met_notice_on_success(
        self,
        m_remove_notice,
        m_repo_enable,
        repo_enable_return_value,
        expected_remove_notice_calls,
        entitlement,
    ):
        m_repo_enable.return_value = repo_enable_return_value
        assert repo_enable_return_value is entitlement._perform_enable()
        assert (
            expected_remove_notice_calls == m_remove_notice.call_args_list[:1]
        )

    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch("uaclient.apt.add_auth_apt_repo")
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "xenial"}
    )
    def test_enable_returns_false_on_missing_suites_directive(
        self,
        m_platform_info,
        m_add_apt,
        _m_setup_apt_proxy,
        fips_entitlement_factory,
    ):
        """When directives do not contain suites returns false."""
        entitlement = fips_entitlement_factory(suites=[])

        with mock.patch.object(
            entitlement, "can_enable", return_value=(True, None)
        ):
            with mock.patch("uaclient.util.handle_message_operations"):
                with pytest.raises(exceptions.UserFacingError) as excinfo:
                    entitlement.enable()
        error_msg = "Empty {} apt suites directive from {}".format(
            entitlement.name, defaults.BASE_CONTRACT_URL
        )
        assert error_msg == excinfo.value.msg
        assert 0 == m_add_apt.call_count

    @mock.patch("uaclient.apt.setup_apt_proxy")
    def test_enable_errors_on_repo_pin_but_invalid_origin(
        self, _m_setup_apt_proxy, entitlement
    ):
        """Error when no valid origin is provided on a pinned entitlemnt."""
        entitlement.origin = None  # invalid value

        with contextlib.ExitStack() as stack:
            m_add_apt = stack.enter_context(
                mock.patch("uaclient.apt.add_auth_apt_repo")
            )
            m_add_pinning = stack.enter_context(
                mock.patch("uaclient.apt.add_ppa_pinning")
            )
            stack.enter_context(
                mock.patch.object(
                    entitlement, "can_enable", return_value=(True, None)
                )
            )
            stack.enter_context(
                mock.patch("uaclient.util.handle_message_operations")
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

    @mock.patch("uaclient.apt.setup_apt_proxy")
    def test_failure_to_install_removes_apt_auth(
        self, _m_setup_apt_proxy, entitlement, tmpdir
    ):

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
                mock.patch.object(
                    entitlement, "can_enable", return_value=(True, None)
                )
            )
            stack.enter_context(
                mock.patch("uaclient.util.handle_message_operations")
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

    @mock.patch(
        "uaclient.entitlements.fips.get_cloud_type", return_value=("", None)
    )
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    @mock.patch("uaclient.util.prompt_for_confirmation", return_value=False)
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_livepatch_service_is_enabled(
        self,
        m_is_container,
        m_handle_message_op,
        m_prompt,
        m_is_config_value_true,
        m_platform_info,
        m_get_cloud_type,
        entitlement,
    ):
        m_handle_message_op.return_value = True
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"
        m_platform_info.return_value = {"series": "test"}

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            with mock.patch.object(
                entitlement,
                "applicability_status",
                return_value=(status.ApplicabilityStatus.APPLICABLE, ""),
            ):
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

    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch(
        M_LIVEPATCH_PATH + "application_status",
        return_value=((status.ApplicationStatus.DISABLED, "")),
    )
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_fips_update_service_is_enabled(
        self,
        m_is_container,
        m_livepatch,
        m_handle_message_op,
        entitlement_factory,
    ):
        m_handle_message_op.return_value = True
        fips_entitlement = entitlement_factory(FIPSEntitlement)
        base_path = "uaclient.entitlements.fips.FIPSUpdatesEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_fips_update:
            with mock.patch.object(
                fips_entitlement, "_allow_fips_on_cloud_instance"
            ) as m_allow_fips_on_cloud:
                m_allow_fips_on_cloud.return_value = True
                m_fips_update.return_value = (
                    status.ApplicationStatus.ENABLED,
                    "",
                )
                result, reason = fips_entitlement.enable()
                assert not result
                expected_msg = (
                    "Cannot enable FIPS when FIPS Updates is enabled."
                )
                assert expected_msg.strip() == reason.message.strip()

    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch(
        M_LIVEPATCH_PATH + "application_status",
        return_value=((status.ApplicationStatus.DISABLED, "")),
    )
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_fips_updates_service_once_enabled(
        self,
        m_is_container,
        m_livepatch,
        m_handle_message_op,
        entitlement_factory,
    ):
        m_handle_message_op.return_value = True
        fips_entitlement = entitlement_factory(
            FIPSEntitlement, services_once_enabled={"fips-updates": True}
        )

        with mock.patch.object(
            fips_entitlement, "_allow_fips_on_cloud_instance"
        ) as m_allow_fips_on_cloud:
            m_allow_fips_on_cloud.return_value = True
            result, reason = fips_entitlement.enable()
            assert not result
            expected_msg = (
                "Cannot enable FIPS because FIPS Updates was once enabled."
            )
            assert expected_msg.strip() == reason.message.strip()

    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.entitlements.fips.get_cloud_type")
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_on_xenial_cloud_instance(
        self,
        m_is_container,
        m_handle_message_op,
        m_cloud_type,
        m_platform_info,
        entitlement,
    ):
        m_handle_message_op.return_value = True
        m_cloud_type.return_value = ("azure", None)
        m_platform_info.return_value = {"series": "xenial"}
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            m_livepatch.return_value = (status.ApplicationStatus.DISABLED, "")
            result, reason = entitlement.enable()
            assert not result
            expected_msg = """\
            Ubuntu Xenial does not provide an Azure optimized FIPS kernel"""
            assert expected_msg.strip() in reason.message.strip()

    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    @mock.patch("uaclient.entitlements.fips.get_cloud_type")
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.util.is_container", return_value=False)
    def test_enable_fails_when_on_gcp_instance_with_default_fips(
        self,
        m_is_container,
        m_handle_message_op,
        m_get_cloud_type,
        m_is_config_value_true,
        m_platform_info,
        entitlement,
    ):
        m_handle_message_op.return_value = True
        m_get_cloud_type.return_value = ("gce", None)
        m_platform_info.return_value = {"series": "test"}

        ent_name = entitlement.name
        fips_cls_name = "FIPS" if ent_name == "fips" else "FIPSUpdates"
        base_path = "uaclient.entitlements.fips.{}Entitlement".format(
            fips_cls_name
        )

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_fips_status:
            m_fips_status.return_value = (
                status.ApplicationStatus.DISABLED,
                "",
            )
            result, reason = entitlement.enable()
            assert not result
            expected_msg = """\
            Ubuntu Test does not provide a GCP optimized FIPS kernel"""
            assert expected_msg.strip() in reason.message.strip()

    @pytest.mark.parametrize("allow_xenial_fips_on_cloud", ((True), (False)))
    @pytest.mark.parametrize("cloud_id", (("aws"), ("gce"), ("azure"), (None)))
    @pytest.mark.parametrize(
        "series", (("trusty"), ("xenial"), ("bionic"), ("focal"))
    )
    @mock.patch("uaclient.util.is_config_value_true")
    def test_prevent_fips_on_xenial_cloud_instances(
        self,
        m_is_config_value_true,
        series,
        cloud_id,
        allow_xenial_fips_on_cloud,
        entitlement,
    ):
        def mock_config_value(config, path_to_value):
            if "allow_xenial_fips_on_cloud" in path_to_value:
                return allow_xenial_fips_on_cloud

            return False

        m_is_config_value_true.side_effect = mock_config_value
        actual_value = entitlement._allow_fips_on_cloud_instance(
            cloud_id=cloud_id, series=series
        )

        if cloud_id == "aws" or cloud_id is None:
            assert actual_value
        elif cloud_id == "gce":
            assert not actual_value
        elif all([allow_xenial_fips_on_cloud, series == "xenial"]):
            assert actual_value
        elif series == "xenial":
            assert not actual_value
        else:
            assert actual_value

    @pytest.mark.parametrize(
        "cfg_allow_default_fips_metapkg_on_gcp", ((True), (False))
    )
    @pytest.mark.parametrize(
        "additional_pkgs", (["ubuntu-fips"], ["ubuntu-gcp-fips", "test"])
    )
    @pytest.mark.parametrize(
        "series", (("trusty"), ("xenial"), ("bionic"), ("focal"))
    )
    @mock.patch("uaclient.util.is_config_value_true")
    def test_prevent_default_fips_on_gcp_cloud(
        self,
        m_is_config_value,
        series,
        additional_pkgs,
        cfg_allow_default_fips_metapkg_on_gcp,
        fips_entitlement_factory,
    ):
        m_is_config_value.return_value = cfg_allow_default_fips_metapkg_on_gcp
        entitlement = fips_entitlement_factory(
            additional_packages=additional_pkgs
        )
        actual_value = entitlement._allow_fips_on_cloud_instance(
            cloud_id="gce", series=series
        )

        if all(
            [
                not cfg_allow_default_fips_metapkg_on_gcp,
                "ubuntu-gcp-fips" not in additional_pkgs,
            ]
        ):
            assert not actual_value
        else:
            assert actual_value


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

    @mock.patch(M_GETPLATFORM, return_value={"series": "xenial"})
    @mock.patch(M_PATH + "util.subp")
    @mock.patch(M_PATH + "apt.get_installed_packages")
    def test_remove_packages_output_message_when_fail(
        self, m_get_installed_packages, m_subp, _m_get_platform, entitlement
    ):
        m_get_installed_packages.return_value = ["ubuntu-fips"]
        m_subp.side_effect = util.ProcessExecutionError(cmd="test")
        expected_msg = "Could not disable {}.".format(entitlement.title)

        with pytest.raises(exceptions.UserFacingError) as exc_info:
            entitlement.remove_packages()

        assert exc_info.value.msg.strip() == expected_msg


@mock.patch("uaclient.util.handle_message_operations", return_value=True)
@mock.patch("uaclient.util.should_reboot", return_value=True)
@mock.patch(
    "uaclient.util.get_platform_info", return_value={"series": "xenial"}
)
class TestFIPSEntitlementDisable:
    def test_disable_on_can_disable_true_removes_apt_config_and_packages(
        self,
        _m_platform_info,
        _m_should_reboot,
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
        assert [
            ["", status.MESSAGE_FIPS_DISABLE_REBOOT_REQUIRED]
        ] == entitlement.cfg.read_cache("notices")


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

    @pytest.mark.parametrize("path_exists", ((True), (False)))
    @pytest.mark.parametrize("proc_content", (("0"), ("1")))
    def test_proc_file_is_used_to_determine_application_status_message(
        self, proc_content, path_exists, entitlement
    ):
        orig_load_file = util.load_file

        def fake_load_file(path):
            if path == "/proc/sys/crypto/fips_enabled":
                return proc_content
            return orig_load_file(path)

        orig_exists = os.path.exists

        def fake_exists(path):
            if path == "/proc/sys/crypto/fips_enabled":
                return path_exists
            return orig_exists(path)

        msg = "sure is some status here"
        entitlement.cfg.add_notice("", status.MESSAGE_FIPS_REBOOT_REQUIRED)

        if proc_content == "0":
            entitlement.cfg.add_notice(
                "", status.MESSAGE_FIPS_DISABLE_REBOOT_REQUIRED
            )

        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(status.ApplicationStatus.ENABLED, msg),
        ):
            with mock.patch("uaclient.util.load_file") as m_load_file:
                m_load_file.side_effect = fake_load_file
                with mock.patch("os.path.exists") as m_path_exists:
                    m_path_exists.side_effect = fake_exists
                    application_status = entitlement.application_status()

        expected_status = status.ApplicationStatus.ENABLED
        if path_exists and proc_content == "1":
            expected_msg = msg
            assert entitlement.cfg.read_cache("notices") is None
        elif path_exists and proc_content == "0":
            expected_msg = "/proc/sys/crypto/fips_enabled is not set to 1"
            expected_status = status.ApplicationStatus.DISABLED
            assert [
                ["", status.NOTICE_FIPS_MANUAL_DISABLE_URL]
            ] == entitlement.cfg.read_cache("notices")
        else:
            expected_msg = "Reboot to FIPS kernel required"
            assert [
                ["", status.MESSAGE_FIPS_REBOOT_REQUIRED]
            ] == entitlement.cfg.read_cache("notices")

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


class TestFipsEntitlementInstallPackages:
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_install_packages_fail_if_metapackage_not_installed(
        self, m_run_apt, entitlement
    ):
        m_run_apt.side_effect = exceptions.UserFacingError("error")
        with pytest.raises(exceptions.UserFacingError):
            entitlement.install_packages()

    @mock.patch(M_PATH + "apt.get_installed_packages")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_install_packages_dont_fail_if_conditional_pkgs_not_installed(
        self, m_run_apt, m_installed_pkgs, fips_entitlement_factory
    ):

        conditional_pkgs = ["b", "c"]
        m_installed_pkgs.return_value = conditional_pkgs
        packages = ["a"]
        entitlement = fips_entitlement_factory(additional_packages=packages)

        m_run_apt.side_effect = [
            True,
            exceptions.UserFacingError("error"),
            exceptions.UserFacingError("error"),
        ]

        fake_stdout = io.StringIO()
        with contextlib.redirect_stdout(fake_stdout):
            with mock.patch.object(
                type(entitlement), "conditional_packages", conditional_pkgs
            ):
                entitlement.install_packages()

        install_cmds = []
        all_pkgs = packages + conditional_pkgs
        for pkg in all_pkgs:
            install_cmds.append(
                mock.call(
                    [
                        "apt-get",
                        "install",
                        "--assume-yes",
                        "--allow-downgrades",
                        '-o Dpkg::Options::="--force-confdef"',
                        '-o Dpkg::Options::="--force-confold"',
                        pkg,
                    ],
                    "Could not enable {}.".format(entitlement.title),
                    env={"DEBIAN_FRONTEND": "noninteractive"},
                )
            )

        expected_msg = "\n".join(
            [
                "Installing {} packages".format(entitlement.title),
                status.MESSAGE_FIPS_PACKAGE_NOT_AVAILABLE.format(
                    service=entitlement.title, pkg="b"
                ),
                status.MESSAGE_FIPS_PACKAGE_NOT_AVAILABLE.format(
                    service=entitlement.title, pkg="c"
                ),
            ]
        )

        assert install_cmds == m_run_apt.call_args_list
        assert expected_msg.strip() in fake_stdout.getvalue().strip()


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

    @mock.patch("uaclient.util.get_platform_info")
    def test_currently_installed_packages_are_included_in_packages(
        self, m_platform_info, entitlement
    ):
        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        # and xenial should not trigger that
        m_platform_info.return_value = {"series": "xenial"}

        assert sorted(FIPS_ADDITIONAL_PACKAGES) == sorted(entitlement.packages)

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
        "cfg_disable_fips_metapckage_override", ((True), (False))
    )
    @pytest.mark.parametrize(
        "series", (("trusty"), ("xenial"), ("bionic"), ("focal"))
    )
    @pytest.mark.parametrize(
        "cloud_id",
        (
            ("azure-china"),
            ("aws-gov"),
            ("aws-china"),
            ("azure"),
            ("aws"),
            ("gce"),
            (None),
        ),
    )
    @mock.patch("uaclient.util.is_config_value_true")
    @mock.patch(M_PATH + "get_cloud_type")
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.apt.get_installed_packages")
    def test_packages_are_override_when_bionic_cloud_instance(
        self,
        m_installed_packages,
        m_platform_info,
        m_get_cloud_type,
        m_is_config_value,
        cloud_id,
        series,
        cfg_disable_fips_metapckage_override,
        fips_entitlement_factory,
    ):
        m_platform_info.return_value = {"series": series}
        m_get_cloud_type.return_value = (
            (cloud_id, None)
            if cloud_id is not None
            else (None, NoCloudTypeReason.NO_CLOUD_DETECTED)
        )
        m_installed_packages.return_value = []
        m_is_config_value.return_value = cfg_disable_fips_metapckage_override
        additional_packages = ["test1", "ubuntu-fips", "test2"]
        entitlement = fips_entitlement_factory(
            additional_packages=additional_packages
        )

        packages = entitlement.packages

        if all(
            [
                series == "bionic",
                cloud_id
                in ("azure", "aws", "aws-china", "aws-gov", "azure-china"),
                not cfg_disable_fips_metapckage_override,
            ]
        ):
            cloud_id = cloud_id.split("-")[0]
            assert packages == [
                "test1",
                "ubuntu-{}-fips".format(cloud_id),
                "test2",
            ]
        else:
            assert packages == additional_packages


class TestFIPSUpdatesEntitlementEnable:
    @pytest.mark.parametrize("enable_ret", ((True), (False)))
    @mock.patch(
        "uaclient.entitlements.fips.FIPSCommonEntitlement._perform_enable"
    )
    def test_fips_updates_enable_write_service_once_enable_file(
        self, m_perform_enable, enable_ret, entitlement_factory
    ):
        m_perform_enable.return_value = enable_ret
        m_write_cache = mock.MagicMock()
        m_read_cache = mock.MagicMock()
        m_read_cache.return_value = {}

        cfg = mock.MagicMock()
        cfg.read_cache = m_read_cache
        cfg.write_cache = m_write_cache

        fips_updates_ent = entitlement_factory(FIPSUpdatesEntitlement, cfg=cfg)
        assert fips_updates_ent._perform_enable() == enable_ret

        if enable_ret:
            assert 1 == m_read_cache.call_count
            assert 1 == m_write_cache.call_count
            assert [
                mock.call(
                    key="services-once-enabled", content={"fips-updates": True}
                )
            ] == m_write_cache.call_args_list
        else:
            assert not m_read_cache.call_count
            assert not m_write_cache.call_count
