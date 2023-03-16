"""Tests related to uaclient.entitlement.base module."""

import contextlib
import copy
import io
import logging
import os
from functools import partial

import mock
import pytest

import uaclient.entitlements.fips as fips
from uaclient import apt, defaults, exceptions, messages, system, util
from uaclient.clouds.identity import NoCloudTypeReason
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
    CanEnableFailureReason,
)
from uaclient.entitlements.fips import (
    CONDITIONAL_PACKAGES_EVERYWHERE,
    CONDITIONAL_PACKAGES_OPENSSH_HMAC,
    UBUNTU_FIPS_METAPACKAGE_DEPENDS_BIONIC,
    UBUNTU_FIPS_METAPACKAGE_DEPENDS_FOCAL,
    UBUNTU_FIPS_METAPACKAGE_DEPENDS_XENIAL,
    FIPSEntitlement,
    FIPSUpdatesEntitlement,
)
from uaclient.files.notices import Notice, NoticesManager

M_PATH = "uaclient.entitlements.fips."
M_LIVEPATCH_PATH = "uaclient.entitlements.livepatch.LivepatchEntitlement."
M_REPOPATH = "uaclient.entitlements.repo."
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
    @pytest.mark.parametrize(
        "series, is_container, expected",
        (
            (
                "xenial",
                False,
                CONDITIONAL_PACKAGES_EVERYWHERE
                + CONDITIONAL_PACKAGES_OPENSSH_HMAC,
            ),
            (
                "xenial",
                True,
                CONDITIONAL_PACKAGES_EVERYWHERE
                + CONDITIONAL_PACKAGES_OPENSSH_HMAC
                + UBUNTU_FIPS_METAPACKAGE_DEPENDS_XENIAL,
            ),
            (
                "bionic",
                False,
                CONDITIONAL_PACKAGES_EVERYWHERE
                + CONDITIONAL_PACKAGES_OPENSSH_HMAC,
            ),
            (
                "bionic",
                True,
                CONDITIONAL_PACKAGES_EVERYWHERE
                + CONDITIONAL_PACKAGES_OPENSSH_HMAC
                + UBUNTU_FIPS_METAPACKAGE_DEPENDS_BIONIC,
            ),
            ("focal", False, CONDITIONAL_PACKAGES_EVERYWHERE),
            (
                "focal",
                True,
                CONDITIONAL_PACKAGES_EVERYWHERE
                + UBUNTU_FIPS_METAPACKAGE_DEPENDS_FOCAL,
            ),
        ),
    )
    @mock.patch("uaclient.system.is_container")
    @mock.patch("uaclient.system.get_release_info")
    def test_conditional_packages(
        self,
        m_get_release_info,
        m_is_container,
        series,
        is_container,
        expected,
        entitlement,
    ):
        """Test conditional package respect series restrictions"""
        m_get_release_info.return_value = mock.MagicMock(series=series)
        m_is_container.return_value = is_container

        conditional_packages = entitlement.conditional_packages
        assert expected == conditional_packages

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
                            "msg": messages.PROMPT_FIPS_PRE_ENABLE,
                        },
                    )
                ],
                "post_enable": None,
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": messages.PROMPT_FIPS_PRE_DISABLE,
                        },
                    )
                ],
            },
            "fips-updates": {
                "pre_enable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "msg": messages.PROMPT_FIPS_UPDATES_PRE_ENABLE,
                            "assume_yes": assume_yes,
                        },
                    )
                ],
                "post_enable": None,
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": assume_yes,
                            "msg": messages.PROMPT_FIPS_PRE_DISABLE,
                        },
                    )
                ],
            },
        }

        if entitlement.name in expected_msging:
            assert expected_msging[entitlement.name] == entitlement.messaging
        else:
            assert False, "Unknown entitlement {}".format(entitlement.name)

    @mock.patch("uaclient.system.is_container", return_value=True)
    def test_messaging_on_containers(
        self, _m_is_container, fips_entitlement_factory
    ):
        """FIPS and FIPS Updates have different messaging on containers"""
        entitlement = fips_entitlement_factory()

        expected_msging = {
            "fips": {
                "pre_enable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": False,
                            "msg": messages.PROMPT_FIPS_CONTAINER_PRE_ENABLE.format(  # noqa: E501
                                title="FIPS"
                            ),
                        },
                    )
                ],
                "post_enable": [messages.FIPS_RUN_APT_UPGRADE],
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": False,
                            "msg": messages.PROMPT_FIPS_PRE_DISABLE,
                        },
                    )
                ],
            },
            "fips-updates": {
                "pre_enable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "msg": messages.PROMPT_FIPS_CONTAINER_PRE_ENABLE.format(  # noqa: E501
                                title="FIPS Updates"
                            ),
                            "assume_yes": False,
                        },
                    )
                ],
                "post_enable": [messages.FIPS_RUN_APT_UPGRADE],
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "assume_yes": False,
                            "msg": messages.PROMPT_FIPS_PRE_DISABLE,
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
            return_value=(ApplicabilityStatus.APPLICABLE, ""),
        ):
            with mock.patch.object(
                entitlement,
                "application_status",
                return_value=(ApplicationStatus.DISABLED, ""),
            ):
                with mock.patch.object(
                    entitlement,
                    "detect_incompatible_services",
                    return_value=False,
                ):
                    assert (True, None) == entitlement.can_enable()
        assert ("", "") == capsys.readouterr()


class TestFIPSEntitlementEnable:
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_PATH + "get_cloud_type", return_value=("", None))
    def test_enable_configures_apt_sources_and_auth_files(
        self,
        _m_get_cloud_type,
        m_setup_apt_proxy,
        entitlement,
    ):
        """When entitled, configure apt repo auth token, pinning and url."""
        notice_ent_cls = NoticesManager()
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
                    "uaclient.apt.get_installed_packages_names",
                    return_value=["openssh-server", "strongswan"],
                )
            )
            m_subp = stack.enter_context(
                mock.patch("uaclient.system.subp", return_value=("", ""))
            )
            m_can_enable = stack.enter_context(
                mock.patch.object(entitlement, "can_enable")
            )
            stack.enter_context(
                mock.patch("uaclient.util.handle_message_operations")
            )
            stack.enter_context(
                mock.patch(
                    "uaclient.system.get_release_info",
                    return_value=mock.MagicMock(series="xenial"),
                )
            )
            stack.enter_context(
                mock.patch(
                    "uaclient.entitlements.fips.system.should_reboot",
                    return_value=True,
                )
            )
            stack.enter_context(mock.patch(M_REPOPATH + "exists"))
            stack.enter_context(
                mock.patch.object(fips, "services_once_enabled_file")
            )
            # Note that this patch uses a PropertyMock and happens on the
            # entitlement's type because packages is a property
            m_packages = mock.PropertyMock(return_value=patched_packages)
            stack.enter_context(
                mock.patch.object(type(entitlement), "packages", m_packages)
            )
            stack.enter_context(
                mock.patch("uaclient.system.is_container", return_value=False)
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

        subp_calls = [
            mock.call(
                ["apt-mark", "showholds"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={},
            ),
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={},
            ),
        ]
        subp_calls += install_cmd

        assert [mock.call()] == m_can_enable.call_args_list
        assert 1 == m_setup_apt_proxy.call_count
        assert 1 == m_installed_pkgs.call_count
        assert add_apt_calls == m_add_apt.call_args_list
        assert apt_pinning_calls == m_add_pinning.call_args_list
        assert subp_calls == m_subp.call_args_list
        assert [
            messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg,
        ] == notice_ent_cls.list()

    @pytest.mark.parametrize(
        "fips_common_enable_return_value, expected_remove_notice_calls",
        [
            (True, [mock.call(Notice.FIPS_INSTALL_OUT_OF_DATE)]),
            (False, []),
        ],
    )
    @mock.patch(
        "uaclient.entitlements.fips.FIPSCommonEntitlement._perform_enable"
    )
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
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
                [
                    mock.call(
                        Notice.WRONG_FIPS_METAPACKAGE_ON_CLOUD,
                    ),
                    mock.call(
                        Notice.FIPS_REBOOT_REQUIRED,
                    ),
                ],
            ),
            (False, []),
        ],
    )
    @mock.patch("uaclient.entitlements.repo.RepoEntitlement._perform_enable")
    @mock.patch("uaclient.files.notices.NoticesManager.remove")
    def test_enable_removes_wrong_met_notice_on_success(
        self,
        m_remove_notice,
        m_repo_enable,
        repo_enable_return_value,
        expected_remove_notice_calls,
        entitlement,
    ):
        m_repo_enable.return_value = repo_enable_return_value
        with mock.patch.object(fips, "services_once_enabled_file"):
            assert repo_enable_return_value is entitlement._perform_enable()
        assert (
            expected_remove_notice_calls == m_remove_notice.call_args_list[:2]
        )

    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch("uaclient.apt.add_auth_apt_repo")
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    def test_enable_returns_false_on_missing_suites_directive(
        self,
        m_get_release_info,
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
                mock.patch(
                    "uaclient.system.get_release_info",
                    return_value=mock.MagicMock(series="xenial"),
                )
            )
            stack.enter_context(mock.patch(M_REPOPATH + "exists"))

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

    @mock.patch(
        "uaclient.entitlements.fips.get_cloud_type", return_value=("", None)
    )
    @mock.patch("uaclient.system.get_release_info")
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    @mock.patch("uaclient.util.prompt_for_confirmation", return_value=False)
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.system.is_container", return_value=False)
    def test_fips_enable_fails_when_livepatch_service_is_enabled(
        self,
        m_is_container,
        m_handle_message_op,
        m_prompt,
        m_is_config_value_true,
        m_get_release_info,
        m_get_cloud_type,
        entitlement_factory,
    ):
        fips_ent = entitlement_factory(FIPSEntitlement)
        m_handle_message_op.return_value = True
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"
        m_get_release_info.return_value = mock.MagicMock(series="test")

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            with mock.patch.object(
                fips_ent,
                "applicability_status",
                return_value=(ApplicabilityStatus.APPLICABLE, ""),
            ):
                m_livepatch.return_value = (
                    ApplicationStatus.ENABLED,
                    "",
                )
                ret, fail = fips_ent.enable()

        assert not ret
        expected_msg = "Cannot enable FIPS when Livepatch is enabled."
        assert expected_msg == fail.message.msg

    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch(
        M_LIVEPATCH_PATH + "application_status",
        return_value=((ApplicationStatus.DISABLED, "")),
    )
    @mock.patch("uaclient.system.is_container", return_value=False)
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
                    ApplicationStatus.ENABLED,
                    "",
                )
                result, reason = fips_entitlement.enable()
                assert not result
                expected_msg = (
                    "Cannot enable FIPS when FIPS Updates is enabled."
                )
                assert expected_msg.strip() == reason.message.msg.strip()

    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch(
        M_LIVEPATCH_PATH + "application_status",
        return_value=((ApplicationStatus.DISABLED, "")),
    )
    @mock.patch("uaclient.system.is_container", return_value=False)
    def test_enable_fails_when_fips_updates_service_once_enabled(
        self,
        m_is_container,
        m_livepatch,
        m_handle_message_op,
        entitlement_factory,
    ):
        m_handle_message_op.return_value = True
        fake_dof = mock.MagicMock()
        fake_ua_file = mock.MagicMock()
        fake_ua_file.to_json.return_value = {"fips_updates": True}
        fake_dof.read.return_value = fake_ua_file
        fips_entitlement = entitlement_factory(FIPSEntitlement)

        with mock.patch.object(
            fips_entitlement, "_allow_fips_on_cloud_instance"
        ) as m_allow_fips_on_cloud:
            m_allow_fips_on_cloud.return_value = True
            with mock.patch.object(
                fips, "services_once_enabled_file", fake_dof
            ):
                result, reason = fips_entitlement.enable()
                assert not result
                expected_msg = (
                    "Cannot enable FIPS because FIPS Updates was once enabled."
                )
                assert expected_msg.strip() == reason.message.msg.strip()

    @mock.patch("uaclient.system.get_release_info")
    @mock.patch("uaclient.entitlements.fips.get_cloud_type")
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.system.is_container", return_value=False)
    def test_enable_fails_when_on_xenial_cloud_instance(
        self,
        m_is_container,
        m_handle_message_op,
        m_cloud_type,
        m_get_release_info,
        entitlement,
    ):
        m_handle_message_op.return_value = True
        m_cloud_type.return_value = ("gce", None)
        m_get_release_info.return_value = mock.MagicMock(series="xenial")
        base_path = "uaclient.entitlements.livepatch.LivepatchEntitlement"

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_livepatch:
            m_livepatch.return_value = (ApplicationStatus.DISABLED, "")
            result, reason = entitlement.enable()
            assert not result
            expected_msg = """\
            Ubuntu Xenial does not provide a GCP optimized FIPS kernel"""
            assert expected_msg.strip() in reason.message.msg.strip()

    @mock.patch("uaclient.system.get_release_info")
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    @mock.patch("uaclient.entitlements.fips.get_cloud_type")
    @mock.patch("uaclient.util.handle_message_operations")
    @mock.patch("uaclient.system.is_container", return_value=False)
    def test_enable_fails_when_on_gcp_instance_with_default_fips(
        self,
        m_is_container,
        m_handle_message_op,
        m_get_cloud_type,
        m_is_config_value_true,
        m_get_release_info,
        entitlement,
    ):
        m_handle_message_op.return_value = True
        m_get_cloud_type.return_value = ("gce", None)
        m_get_release_info.return_value = mock.MagicMock(series="test")

        ent_name = entitlement.name
        fips_cls_name = "FIPS" if ent_name == "fips" else "FIPSUpdates"
        base_path = "uaclient.entitlements.fips.{}Entitlement".format(
            fips_cls_name
        )

        with mock.patch(
            "{}.application_status".format(base_path)
        ) as m_fips_status:
            m_fips_status.return_value = (
                ApplicationStatus.DISABLED,
                "",
            )
            result, reason = entitlement.enable()
            assert not result
            expected_msg = """\
            Ubuntu Test does not provide a GCP optimized FIPS kernel"""
            assert expected_msg.strip() in reason.message.msg.strip()

    @pytest.mark.parametrize(
        "allow_default_fips_metapackage_on_gcp", ((True), (False))
    )
    @pytest.mark.parametrize("cloud_id", (("aws"), ("gce"), ("azure"), (None)))
    @pytest.mark.parametrize("series", (("xenial"), ("bionic")))
    @mock.patch("uaclient.util.is_config_value_true")
    def test_prevent_fips_on_xenial_or_focal_cloud_instances(
        self,
        m_is_config_value_true,
        series,
        cloud_id,
        allow_default_fips_metapackage_on_gcp,
        entitlement,
    ):
        def mock_config_value(config, path_to_value):
            if "allow_default_fips_metapackage_on_gcp" in path_to_value:
                return allow_default_fips_metapackage_on_gcp

            return False

        m_is_config_value_true.side_effect = mock_config_value
        actual_value = entitlement._allow_fips_on_cloud_instance(
            cloud_id=cloud_id, series=series
        )

        if cloud_id in ("azure", "aws") or cloud_id is None:
            assert actual_value
        elif all([cloud_id == "gce", allow_default_fips_metapackage_on_gcp]):
            assert actual_value
        elif all(
            [
                cloud_id == "gce",
                not allow_default_fips_metapackage_on_gcp,
                series == "xenial",
            ]
        ):
            assert not actual_value
        elif cloud_id == "gce":
            assert actual_value

    @pytest.mark.parametrize(
        "cfg_allow_default_fips_metapkg_on_gcp", ((True), (False))
    )
    @pytest.mark.parametrize(
        "additional_pkgs", (["ubuntu-fips"], ["ubuntu-gcp-fips", "test"])
    )
    @pytest.mark.parametrize("series", (("xenial"), ("bionic"), ("focal")))
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
                series not in ("bionic", "focal"),
            ]
        ):
            assert not actual_value
        else:
            assert actual_value

    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @mock.patch(
        "uaclient.entitlements.fips.FIPSCommonEntitlement._perform_enable"
    )
    @mock.patch(M_PATH + "get_cloud_type")
    def test_show_message_on_cloud_id_error(
        self,
        m_get_cloud_type,
        m_perform_enable,
        caplog_text,
        entitlement_factory,
    ):
        m_get_cloud_type.return_value = (
            None,
            NoCloudTypeReason.CLOUD_ID_ERROR,
        )
        fips_entitlement = entitlement_factory(FIPSEntitlement)
        fips_entitlement._perform_enable()
        logs = caplog_text()
        assert (
            "Could not determine cloud, defaulting to generic FIPS package."
            in logs
        )


class TestFIPSEntitlementRemovePackages:
    @pytest.mark.parametrize("installed_pkgs", (["sl"], ["ubuntu-fips", "sl"]))
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    @mock.patch(M_PATH + "system.subp")
    @mock.patch(M_PATH + "apt.get_installed_packages_names")
    def test_remove_packages_only_removes_if_package_is_installed(
        self,
        m_get_installed_packages,
        m_subp,
        _m_get_release_info,
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

    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="xenial"),
    )
    @mock.patch(M_PATH + "system.subp")
    @mock.patch(M_PATH + "apt.get_installed_packages_names")
    def test_remove_packages_output_message_when_fail(
        self,
        m_get_installed_packages,
        m_subp,
        _m_get_release_info,
        entitlement,
    ):
        m_get_installed_packages.return_value = ["ubuntu-fips"]
        m_subp.side_effect = exceptions.ProcessExecutionError(cmd="test")
        expected_msg = "Could not disable {}.".format(entitlement.title)

        with pytest.raises(exceptions.UserFacingError) as exc_info:
            entitlement.remove_packages()

        assert exc_info.value.msg.strip() == expected_msg


@mock.patch("uaclient.util.handle_message_operations", return_value=True)
@mock.patch("uaclient.system.should_reboot", return_value=True)
@mock.patch(
    "uaclient.system.get_release_info",
    return_value=mock.MagicMock(series="xenial"),
)
class TestFIPSEntitlementDisable:
    def test_disable_on_can_disable_true_removes_apt_config_and_packages(
        self,
        _m_get_release_info,
        _m_should_reboot,
        m_handle_message_operations,
        entitlement,
    ):
        """When can_disable, disable removes apt config and packages."""
        notice_ent_cls = NoticesManager()

        with mock.patch.object(
            entitlement, "can_disable", return_value=(True, None)
        ):
            with mock.patch.object(
                entitlement, "remove_apt_config"
            ) as m_remove_apt_config:
                with mock.patch.object(
                    entitlement, "remove_packages"
                ) as m_remove_packages:
                    assert entitlement.disable(True)
        assert [mock.call(silent=True)] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_remove_packages.call_args_list
        assert [
            messages.FIPS_DISABLE_REBOOT_REQUIRED,
        ] == notice_ent_cls.list()


@mock.patch("uaclient.system.should_reboot")
class TestFIPSEntitlementApplicationStatus:
    @pytest.mark.parametrize(
        "super_application_status",
        [s for s in ApplicationStatus if s is not ApplicationStatus.ENABLED],
    )
    def test_non_enabled_passed_through(
        self, _m_should_reboot, entitlement, super_application_status
    ):
        msg = "sure is some status here"
        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(super_application_status, msg),
        ):
            application_status = entitlement.application_status()

        assert (super_application_status, msg) == application_status

    @pytest.mark.parametrize(
        "super_application_status",
        [s for s in ApplicationStatus if s is not ApplicationStatus.ENABLED],
    )
    def test_non_root_does_not_fail(
        self, _m_should_reboot, super_application_status, FakeConfig
    ):
        cfg = FakeConfig()
        entitlement = FIPSUpdatesEntitlement(cfg)
        msg = "sure is some status here"
        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(super_application_status, msg),
        ):
            application_status = entitlement.application_status()

        assert (super_application_status, msg) == application_status

    @pytest.mark.parametrize("should_reboot", ((True), (False)))
    @pytest.mark.parametrize("path_exists", ((True), (False)))
    @pytest.mark.parametrize("proc_content", (("0"), ("1")))
    def test_proc_file_is_used_to_determine_application_status_message(
        self,
        m_should_reboot,
        proc_content,
        path_exists,
        should_reboot,
        entitlement,
    ):
        notice_ent_cls = NoticesManager()
        m_should_reboot.return_value = should_reboot
        orig_load_file = system.load_file

        def fake_load_file(path):
            if path == "/proc/sys/crypto/fips_enabled":
                return proc_content
            return orig_load_file(path)

        orig_exists = os.path.exists

        def fake_exists(path):
            if path == "/proc/sys/crypto/fips_enabled":
                return path_exists
            return orig_exists(path)

        msg = messages.NamedMessage("test-code", "sure is some status here")
        notice_ent_cls.add(
            Notice.FIPS_SYSTEM_REBOOT_REQUIRED,
            messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg,
        )

        if path_exists:
            notice_ent_cls.add(
                Notice.FIPS_REBOOT_REQUIRED,
                messages.FIPS_REBOOT_REQUIRED_MSG,
            )

        if proc_content == "0":
            notice_ent_cls.add(
                Notice.FIPS_DISABLE_REBOOT_REQUIRED,
                messages.FIPS_DISABLE_REBOOT_REQUIRED,
            )

        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(ApplicationStatus.ENABLED, msg),
        ):
            with mock.patch("uaclient.system.load_file") as m_load_file:
                m_load_file.side_effect = fake_load_file
                with mock.patch("os.path.exists") as m_path_exists:
                    m_path_exists.side_effect = fake_exists
                    (
                        actual_status,
                        actual_msg,
                    ) = entitlement.application_status()

        expected_status = ApplicationStatus.ENABLED
        expected_msg = msg
        if path_exists and should_reboot and proc_content == "1":
            expected_msg = msg
            assert [
                messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg,
                messages.FIPS_REBOOT_REQUIRED_MSG,
            ] == notice_ent_cls.list()
        elif path_exists and not should_reboot and proc_content == "1":
            expected_msg = msg
            # we do not delete the FIPS_REBOOT_REQUIRED notices
            # deleting will happen after rebooting
            assert notice_ent_cls.list() == [messages.FIPS_REBOOT_REQUIRED_MSG]
        elif path_exists and should_reboot and proc_content == "0":
            expected_msg = messages.FIPS_PROC_FILE_ERROR.format(
                file_name=entitlement.FIPS_PROC_FILE
            )
            expected_status = ApplicationStatus.DISABLED
            assert [
                messages.FIPS_DISABLE_REBOOT_REQUIRED,
                messages.NOTICE_FIPS_MANUAL_DISABLE_URL,
                messages.FIPS_SYSTEM_REBOOT_REQUIRED.msg,
                messages.FIPS_REBOOT_REQUIRED_MSG,
            ] == notice_ent_cls.list()
        elif path_exists and not should_reboot and proc_content == "0":
            expected_msg = messages.FIPS_PROC_FILE_ERROR.format(
                file_name=entitlement.FIPS_PROC_FILE
            )
            expected_status = ApplicationStatus.DISABLED
            assert [
                (
                    Notice.FIPS_MANUAL_DISABLE_URL.value.label,
                    messages.NOTICE_FIPS_MANUAL_DISABLE_URL,
                )
                == notice_ent_cls.list()
            ]
        else:
            expected_msg = messages.FIPS_REBOOT_REQUIRED

        assert actual_status == expected_status
        assert expected_msg.msg == actual_msg.msg
        assert expected_msg.name == actual_msg.name

    def test_fips_does_not_show_enabled_when_fips_updates_is(
        self, _m_should_reboot, entitlement
    ):
        with mock.patch("uaclient.apt.get_apt_cache_policy") as m_apt_policy:
            m_apt_policy.return_value = (
                "1001 http://FIPS-UPDATES/ubuntu"
                " xenial-updates/main amd64 Packages\n"
                ""
            )

            application_status, _ = entitlement.application_status()

        expected_status = ApplicationStatus.DISABLED
        if isinstance(entitlement, FIPSUpdatesEntitlement):
            expected_status = ApplicationStatus.ENABLED

        assert expected_status == application_status


class TestFipsEntitlementInstallPackages:
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_install_packages_fail_if_metapackage_not_installed(
        self, m_run_apt, entitlement
    ):
        m_run_apt.side_effect = exceptions.UserFacingError("error")
        with mock.patch.object(entitlement, "remove_apt_config"):
            with pytest.raises(exceptions.UserFacingError):
                entitlement.install_packages()

    @mock.patch(M_PATH + "apt.get_installed_packages_names")
    @mock.patch(M_PATH + "apt.run_apt_install_command")
    def test_install_packages_dont_fail_if_conditional_pkgs_not_installed(
        self,
        m_run_apt_install,
        m_installed_pkgs,
        fips_entitlement_factory,
        event,
    ):

        conditional_pkgs = ["b", "c"]
        m_installed_pkgs.return_value = conditional_pkgs
        packages = ["a"]
        entitlement = fips_entitlement_factory(additional_packages=packages)

        m_run_apt_install.side_effect = [
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
                    packages=[pkg],
                    apt_options=[
                        "--allow-downgrades",
                        '-o Dpkg::Options::="--force-confdef"',
                        '-o Dpkg::Options::="--force-confold"',
                    ],
                    error_msg="Could not enable {}.".format(entitlement.title),
                    env={"DEBIAN_FRONTEND": "noninteractive"},
                )
            )

        expected_msg = "\n".join(
            [
                "Installing {} packages".format(entitlement.title),
                messages.FIPS_PACKAGE_NOT_AVAILABLE.format(
                    service=entitlement.title, pkg="b"
                ),
                messages.FIPS_PACKAGE_NOT_AVAILABLE.format(
                    service=entitlement.title, pkg="c"
                ),
            ]
        )

        assert install_cmds == m_run_apt_install.call_args_list
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
            (
                "libgcrypt20\nlibgcrypt20-hmac\nwow\n",
                ["libgcrypt20", "libgcrypt20-hmac"],
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
        entitlement.setup_apt_config(silent=False)
        expected_calls = [
            mock.call(["apt-mark", "showholds"], "apt-mark showholds failed.")
        ]
        if unhold_packages:
            cmd = ["apt-mark", "unhold"] + unhold_packages
            expected_calls.append(mock.call(cmd, " ".join(cmd) + " failed."))
        assert expected_calls == run_apt_command.call_args_list
        assert [mock.call(silent=False)] == setup_apt_config.call_args_list


class TestFipsEntitlementPackages:
    @mock.patch(M_PATH + "apt.get_installed_packages_names", return_value=[])
    @mock.patch("uaclient.system.get_release_info")
    def test_packages_is_list(self, m_get_release_info, _mock, entitlement):
        """RepoEntitlement.enable will fail if it isn't"""

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_get_release_info.return_value = mock.MagicMock(series="test")

        assert isinstance(entitlement.packages, list)

    @mock.patch(M_PATH + "apt.get_installed_packages_names", return_value=[])
    @mock.patch("uaclient.system.get_release_info")
    def test_fips_required_packages_included(
        self, m_get_release_info, _mock, entitlement
    ):
        """The fips_required_packages should always be in .packages"""

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_get_release_info.return_value = mock.MagicMock(series="test")

        assert set(FIPS_ADDITIONAL_PACKAGES).issubset(
            set(entitlement.packages)
        )

    @mock.patch("uaclient.system.get_release_info")
    def test_currently_installed_packages_are_included_in_packages(
        self, m_get_release_info, entitlement
    ):
        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        # and xenial should not trigger that
        m_get_release_info.return_value = mock.MagicMock(series="xenial")

        assert sorted(FIPS_ADDITIONAL_PACKAGES) == sorted(entitlement.packages)

    @mock.patch(M_PATH + "apt.get_installed_packages_names")
    @mock.patch("uaclient.system.get_release_info")
    def test_multiple_packages_calls_dont_mutate_state(
        self, m_get_release_info, m_get_installed_packages, entitlement
    ):
        # Make it appear like all packages are installed
        m_get_installed_packages.return_value.__contains__.return_value = True

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_get_release_info.return_value = mock.MagicMock(series="test")

        before = copy.deepcopy(entitlement.conditional_packages)

        assert entitlement.packages

        after = copy.deepcopy(entitlement.conditional_packages)

        assert before == after


class TestFIPSUpdatesEntitlementEnable:
    @pytest.mark.parametrize("enable_ret", ((True), (False)))
    @mock.patch("uaclient.entitlements.fips.notices.NoticesManager.remove")
    @mock.patch(
        "uaclient.entitlements.fips.FIPSCommonEntitlement._perform_enable"
    )
    def test_fips_updates_enable_write_service_once_enable_file(
        self,
        m_perform_enable,
        m_remove_notice,
        enable_ret,
        entitlement_factory,
    ):
        m_perform_enable.return_value = enable_ret
        fake_file = mock.MagicMock()
        fake_file.read.return_value = None

        with mock.patch.object(
            fips, "services_once_enabled_file", fake_file
        ) as m_services_once_enabled:
            cfg = mock.MagicMock()
            fips_updates_ent = entitlement_factory(
                FIPSUpdatesEntitlement, cfg=cfg
            )
            assert fips_updates_ent._perform_enable() == enable_ret

        if enable_ret:
            assert 1 == m_services_once_enabled.write.call_count
        else:
            assert not m_services_once_enabled.write.call_count


class TestFIPSUpdatesEntitlementCanEnable:
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    def test_can_enable_false_if_fips_enabled(
        self, m_is_config_value_true, capsys, entitlement_factory
    ):
        """When entitlement is disabled, can_enable returns True."""
        entitlement = entitlement_factory(FIPSUpdatesEntitlement)
        with mock.patch.object(
            entitlement,
            "applicability_status",
            return_value=(ApplicabilityStatus.APPLICABLE, ""),
        ):
            with mock.patch.object(
                entitlement,
                "application_status",
                return_value=(ApplicationStatus.DISABLED, ""),
            ):
                with mock.patch(
                    M_PATH + "FIPSEntitlement.application_status"
                ) as m_fips_status:
                    m_fips_status.return_value = (
                        ApplicationStatus.ENABLED,
                        None,
                    )
                    actual_ret, reason = entitlement.can_enable()
                    assert actual_ret is False
                    assert (
                        reason.reason
                        == CanEnableFailureReason.INCOMPATIBLE_SERVICE
                    )
