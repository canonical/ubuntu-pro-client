"""Tests related to uaclient.entitlement.base module."""

import copy
import logging
import os
from functools import partial

import mock
import pytest

import uaclient.entitlements.fips as fips
from uaclient import apt, exceptions, messages, system, util
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
    FIPSPreviewEntitlement,
    FIPSUpdatesEntitlement,
)
from uaclient.files.notices import Notice, NoticesManager
from uaclient.testing import fakes

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

    @pytest.mark.parametrize(
        "fips_version, assume_yes, expected_continue",
        (
            (
                "0",
                True,
                True,
            ),
            (
                "0",
                False,
                False,
            ),
            (
                "999",
                True,
                True,
            ),
            (
                "999",
                False,
                True,
            ),
        ),
    )
    @mock.patch(M_PATH + "apt.get_pkg_candidate_version")
    @mock.patch(M_PATH + "util.prompt_for_confirmation")
    def test_kernel_downgrade(
        self,
        m_prompt_for_confirmation,
        m_pkg_candidate_version,
        fips_version,
        assume_yes,
        expected_continue,
        entitlement,
    ):
        """Test kernel downgrades block install if user denies prompt"""
        # if user is prompted for confirmation assume they say no
        if not assume_yes:
            m_prompt_for_confirmation.return_value = False
        else:
            m_prompt_for_confirmation.return_value = True
        m_pkg_candidate_version.return_value = fips_version
        install_continues = entitlement.prompt_if_kernel_downgrade(
            assume_yes=assume_yes
        )
        assert install_continues == expected_continue

    def test_default_repo_key_file(self, entitlement):
        """GPG keyring file is the same for both FIPS and FIPS with Updates"""
        assert entitlement.repo_key_file == "ubuntu-pro-fips.gpg"

    def test_default_repo_pinning(self, entitlement):
        """FIPS and FIPS with Updates repositories are pinned."""
        assert entitlement.repo_pin_priority == 1001

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
                            "msg": messages.PROMPT_FIPS_CONTAINER_PRE_ENABLE.format(  # noqa: E501
                                title="FIPS"
                            ),
                        },
                    )
                ],
                "pre_install": [
                    (
                        entitlement.prompt_if_kernel_downgrade,
                        {},
                    )
                ],
                "post_enable": [messages.FIPS_RUN_APT_UPGRADE],
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "msg": messages.PROMPT_FIPS_PRE_DISABLE.format(
                                title="FIPS"
                            ),
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
                        },
                    )
                ],
                "pre_install": [
                    (
                        entitlement.prompt_if_kernel_downgrade,
                        {},
                    )
                ],
                "post_enable": [messages.FIPS_RUN_APT_UPGRADE],
                "pre_disable": [
                    (
                        util.prompt_for_confirmation,
                        {
                            "msg": messages.PROMPT_FIPS_PRE_DISABLE.format(
                                title="FIPS Updates"
                            ),
                        },
                    )
                ],
            },
        }

        if entitlement.name in expected_msging:
            assert expected_msging[entitlement.name] == entitlement.messaging
        else:
            assert False, "Unknown entitlement {}".format(entitlement.name)


class TestFIPSEntitlementEnable:
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
            is fips_entitlement._perform_enable(mock.MagicMock())
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
            assert repo_enable_return_value is entitlement._perform_enable(
                mock.MagicMock()
            )
        assert (
            expected_remove_notice_calls == m_remove_notice.call_args_list[:2]
        )

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
                result, reason = fips_entitlement.enable(mock.MagicMock())
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
                result, reason = fips_entitlement.enable(mock.MagicMock())
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
            result, reason = entitlement.enable(mock.MagicMock())
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
            result, reason = entitlement.enable(mock.MagicMock())
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
        fips_entitlement._perform_enable(mock.MagicMock())
        logs = caplog_text()
        assert (
            "Could not determine cloud, defaulting to generic FIPS package."
            in logs
        )


class TestFIPSEntitlementRemovePackages:
    @pytest.mark.parametrize("installed_pkgs", (["sl"], ["ubuntu-fips", "sl"]))
    @mock.patch(M_PATH + "system.is_container", return_value=False)
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
        _m_is_container,
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
            override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
        )
        if "ubuntu-fips" in installed_pkgs:
            assert [remove_cmd] == m_subp.call_args_list
        else:
            assert [] == m_subp.call_args_list

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
        expected_msg = (
            "Unexpected APT error.\nCould not disable {}.\nSee "
            "/var/log/ubuntu-advantage.log"
        ).format(entitlement.title)

        with pytest.raises(exceptions.UbuntuProError) as exc_info:
            entitlement.remove_packages()

        assert exc_info.value.msg.strip() == expected_msg


class TestFIPSCheckForRebootMsg:
    @pytest.mark.parametrize(
        "operation,expected",
        (
            (
                "disable operation",
                messages.FIPS_DISABLE_REBOOT_REQUIRED,
            ),
        ),
    )
    @mock.patch("uaclient.system.should_reboot", return_value=True)
    def test_check_for_reboot_message(
        self,
        _m_should_reboot,
        operation,
        expected,
        entitlement,
    ):
        """When can_disable, disable removes apt config and packages."""
        notice_ent_cls = NoticesManager()
        entitlement._check_for_reboot_msg(operation=operation)
        assert [expected] == notice_ent_cls.list()


@mock.patch("uaclient.system.should_reboot")
class TestFIPSEntitlementApplicationStatus:
    @pytest.mark.parametrize(
        "super_application_status",
        [s for s in ApplicationStatus if s is not ApplicationStatus.ENABLED],
    )
    @mock.patch("uaclient.system.is_container", return_value=False)
    @mock.patch("os.path.exists", return_value=False)
    def test_non_enabled_passed_through(
        self,
        _m_path_exists,
        _m_is_container,
        _m_should_reboot,
        entitlement,
        super_application_status,
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
    @mock.patch("uaclient.system.is_container", return_value=False)
    @mock.patch("os.path.exists", return_value=False)
    def test_non_root_does_not_fail(
        self,
        _m_path_exists,
        _m_is_container,
        _m_should_reboot,
        super_application_status,
        FakeConfig,
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
    @mock.patch("uaclient.system.is_container", return_value=False)
    def test_proc_file_is_used_to_determine_application_status_message(
        self,
        _m_is_container,
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
            messages.FIPS_SYSTEM_REBOOT_REQUIRED,
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
                messages.FIPS_SYSTEM_REBOOT_REQUIRED,
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
                messages.FIPS_SYSTEM_REBOOT_REQUIRED,
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

    @mock.patch("uaclient.system.is_container", return_value=True)
    def test_application_status_inside_container(
        self,
        _m_is_container,
        m_should_reboot,
        entitlement,
    ):
        m_should_reboot.return_value = False
        notice_ent_cls = NoticesManager()
        notice_ent_cls.add(
            Notice.FIPS_SYSTEM_REBOOT_REQUIRED,
            messages.FIPS_SYSTEM_REBOOT_REQUIRED,
        )
        expected_status = ApplicationStatus.ENABLED
        expected_msg = "test"

        with mock.patch(
            M_PATH + "repo.RepoEntitlement.application_status",
            return_value=(
                expected_status,
                messages.NamedMessage("test", expected_msg),
            ),
        ):
            actual_status, actual_message = entitlement.application_status()

        assert expected_status == actual_status
        assert expected_msg == actual_message.msg
        assert [] == notice_ent_cls.list()

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
        m_run_apt.side_effect = fakes.FakeUbuntuProError()
        with mock.patch.object(entitlement, "remove_apt_config"):
            with pytest.raises(exceptions.UbuntuProError):
                entitlement.install_packages(mock.MagicMock())

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
            fakes.FakeUbuntuProError(),
            fakes.FakeUbuntuProError(),
        ]

        progress_mock = mock.MagicMock()
        with mock.patch.object(
            type(entitlement), "conditional_packages", conditional_pkgs
        ):
            entitlement.install_packages(progress_mock)

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
                    override_env_vars={"DEBIAN_FRONTEND": "noninteractive"},
                )
            )

        assert [
            mock.call("message_operation", mock.ANY),
            mock.call("info", "Updating standard Ubuntu package lists"),
            mock.call(
                "info",
                messages.FIPS_PACKAGE_NOT_AVAILABLE.format(
                    service=entitlement.title, pkg="b"
                ),
            ),
            mock.call(
                "info",
                messages.FIPS_PACKAGE_NOT_AVAILABLE.format(
                    service=entitlement.title, pkg="c"
                ),
            ),
        ] == progress_mock.emit.call_args_list
        assert [
            mock.call("Installing {} packages".format(entitlement.title)),
        ] == progress_mock.progress.call_args_list

        assert install_cmds == m_run_apt_install.call_args_list


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
        entitlement.setup_apt_config(mock.MagicMock())
        expected_calls = [
            mock.call(
                ["apt-mark", "showholds"],
                messages.EXECUTING_COMMAND_FAILED.format(
                    command="apt-mark showholds"
                ),
            )
        ]
        if unhold_packages:
            cmd = ["apt-mark", "unhold"] + unhold_packages
            expected_calls.append(
                mock.call(
                    cmd,
                    messages.EXECUTING_COMMAND_FAILED.format(
                        command=" ".join(cmd)
                    ),
                )
            )
        assert expected_calls == run_apt_command.call_args_list
        assert [mock.call(mock.ANY)] == setup_apt_config.call_args_list


class TestFipsEntitlementPackages:
    @mock.patch(M_PATH + "apt.get_installed_packages_names", return_value=[])
    @mock.patch("uaclient.system.get_release_info")
    def test_packages_is_list(self, m_get_release_info, _mock, entitlement):
        """RepoEntitlement.enable will fail if it isn't"""

        # Do not trigger metapackage override by
        # _replace_metapackage_on_cloud_instance
        m_get_release_info.return_value = mock.MagicMock(series="test")

        assert isinstance(entitlement.packages, list)

    @mock.patch("uaclient.system.is_container", return_value=True)
    def test_packages_is_empty_if_running_on_container(
        self, _m_is_container, entitlement
    ):
        assert [] == entitlement.packages

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
            assert (
                fips_updates_ent._perform_enable(mock.MagicMock())
                == enable_ret
            )

        if enable_ret:
            assert 1 == m_services_once_enabled.write.call_count
        else:
            assert not m_services_once_enabled.write.call_count


class TestFIPSEntitlementCanEnable:
    @pytest.mark.parametrize(
        "fips_cls",
        (
            (FIPSUpdatesEntitlement),
            (FIPSPreviewEntitlement),
        ),
    )
    @mock.patch("uaclient.util.is_config_value_true", return_value=False)
    def test_can_enable_false_if_fips_enabled(
        self, m_is_config_value_true, fips_cls, capsys, entitlement_factory
    ):
        """When entitlement is disabled, can_enable returns True."""
        entitlement = entitlement_factory(fips_cls)
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


class TestFipsPreview:
    def test_allow_fips_on_cloud_is_always_true(self, entitlement_factory):
        entitlement = entitlement_factory(FIPSPreviewEntitlement)
        assert entitlement._allow_fips_on_cloud_instance(
            series="test", cloud_id="test"
        )
