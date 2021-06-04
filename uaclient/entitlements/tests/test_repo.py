import copy

import mock
import pytest
from types import MappingProxyType

from uaclient import apt
from uaclient.entitlements.repo import RepoEntitlement
from uaclient.entitlements.tests.conftest import machine_token
from uaclient import exceptions
from uaclient import status
from uaclient import util


M_PATH = "uaclient.entitlements.repo."
M_CONTRACT_PATH = "uaclient.entitlements.repo.contract.UAContractClient."

PLATFORM_INFO_SUPPORTED = MappingProxyType(
    {
        "arch": "x86_64",
        "kernel": "4.4.0-00-generic",
        "series": "xenial",
        "version": "16.04 LTS (Xenial Xerus)",
    }
)


class RepoTestEntitlement(RepoEntitlement):
    """Subclass so we can test shared repo functionality"""

    name = "repotest"
    title = "Repo Test Class"
    description = "Repo entitlement for testing"
    repo_key_file = "test.gpg"


class RepoTestEntitlementDisableAptAuthOnly(RepoTestEntitlement):
    disable_apt_auth_only = True


class RepoTestEntitlementDisableAptAuthOnlyFalse(RepoTestEntitlement):
    disable_apt_auth_only = False


class RepoTestEntitlementRepoPinInt(RepoTestEntitlement):
    repo_pin_priority = 1000


class RepoTestEntitlementRepoPinNever(RepoTestEntitlement):
    repo_pin_priority = "never"


@pytest.fixture
def entitlement(entitlement_factory):
    return entitlement_factory(
        RepoTestEntitlement, affordances={"series": ["xenial"]}
    )


class TestUserFacingStatus:
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_inapplicable_on_inapplicable_applicability_status(
        self, m_platform_info, entitlement
    ):
        """When applicability_status is INAPPLICABLE, return INAPPLICABLE."""
        platform_unsupported = copy.deepcopy(dict(PLATFORM_INFO_SUPPORTED))
        platform_unsupported["series"] = "trusty"
        platform_unsupported["version"] = "14.04 LTS (Trusty Tahr)"
        m_platform_info.return_value = platform_unsupported
        applicability, details = entitlement.applicability_status()
        assert status.ApplicabilityStatus.INAPPLICABLE == applicability
        expected_details = (
            "Repo Test Class is not available for Ubuntu 14.04"
            " LTS (Trusty Tahr)."
        )
        assert expected_details == details
        uf_status, _ = entitlement.user_facing_status()
        assert status.UserFacingStatus.INAPPLICABLE == uf_status

    @mock.patch(M_PATH + "util.get_platform_info")
    def test_unavailable_on_unentitled(self, m_platform_info, entitlement):
        """When unentitled, return UNAVAILABLE."""
        no_entitlements = copy.deepcopy(machine_token("blah"))
        # delete all enttlements
        no_entitlements["machineTokenInfo"]["contractInfo"][
            "resourceEntitlements"
        ].pop()
        entitlement.cfg.write_cache("machine-token", no_entitlements)
        m_platform_info.return_value = dict(PLATFORM_INFO_SUPPORTED)
        applicability, _details = entitlement.applicability_status()
        assert status.ApplicabilityStatus.APPLICABLE == applicability
        uf_status, uf_details = entitlement.user_facing_status()
        assert status.UserFacingStatus.UNAVAILABLE == uf_status
        assert "Repo Test Class is not entitled" == uf_details


class TestProcessContractDeltas:
    @pytest.mark.parametrize("orig_access", ({}, {"entitlement": {}}))
    def test_on_no_deltas(self, orig_access):
        """Return True when no deltas are available to process."""
        entitlement = RepoTestEntitlement()
        with mock.patch.object(
            entitlement, "remove_apt_config"
        ) as m_remove_apt_config:
            with mock.patch.object(
                entitlement, "setup_apt_config"
            ) as m_setup_apt_config:
                assert entitlement.process_contract_deltas(orig_access, {})
        assert [] == m_remove_apt_config.call_args_list
        assert [] == m_setup_apt_config.call_args_list

    @pytest.mark.parametrize("entitled", (False, util.DROPPED_KEY))
    @mock.patch.object(RepoTestEntitlement, "disable")
    @mock.patch.object(RepoTestEntitlement, "can_disable", return_value=True)
    @mock.patch.object(RepoTestEntitlement, "application_status")
    def test_disable_when_delta_to_unentitled(
        self,
        m_application_status,
        m_can_disable,
        m_disable,
        entitlement,
        entitled,
    ):
        """Disable the service on contract transitions to unentitled."""
        application_status = status.ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        assert entitlement.process_contract_deltas(
            {"entitlement": {"entitled": True}},
            {"entitlement": {"entitled": entitled}},
        )
        assert [mock.call()] == m_disable.call_args_list

    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "application_status")
    @mock.patch.object(RepoTestEntitlement, "applicability_status")
    def test_no_changes_when_service_inactive_and_not_enable_by_default(
        self,
        m_applicability_status,
        m_application_status,
        m_remove_apt_config,
        entitlement,
    ):
        """Noop when service is inactive and not enableByDefault."""
        m_application_status.return_value = (
            status.ApplicationStatus.DISABLED,
            "",
        )
        m_applicability_status.return_value = (
            status.ApplicabilityStatus.APPLICABLE,
            "",
        )
        assert entitlement.process_contract_deltas(
            {"entitlement": {"entitled": True}},
            {
                "entitlement": {"obligations": {"enableByDefault": False}},
                "resourceToken": "repotest-token",
            },
        )
        assert [] == m_remove_apt_config.call_args_list

    @mock.patch.object(RepoTestEntitlement, "enable")
    @mock.patch.object(RepoTestEntitlement, "application_status")
    @mock.patch.object(RepoTestEntitlement, "applicability_status")
    def test_allow_enable_when_inactive_enable_by_default_and_resource_token(
        self,
        m_applicability_status,
        m_application_status,
        m_enable,
        entitlement,
    ):
        """Update apt when inactive, enableByDefault and allow_enable."""
        m_application_status.return_value = (
            status.ApplicationStatus.DISABLED,
            "",
        )
        m_applicability_status.return_value = (
            status.ApplicabilityStatus.APPLICABLE,
            "",
        )
        assert entitlement.process_contract_deltas(
            {"entitlement": {"entitled": True}},
            {
                "entitlement": {"obligations": {"enableByDefault": True}},
                "resourceToken": "repotest-token",
            },
            allow_enable=True,
        )
        assert [mock.call()] == m_enable.call_args_list

    @mock.patch.object(RepoTestEntitlement, "enable")
    @mock.patch.object(RepoTestEntitlement, "application_status")
    @mock.patch.object(RepoTestEntitlement, "applicability_status")
    def test_not_allow_enable_logs_message_when_inactive_enable_by_default(
        self,
        m_applicability_status,
        m_application_status,
        m_enable,
        entitlement,
        caplog_text,
    ):
        """Log a message when inactive, enableByDefault and allow_enable."""
        m_application_status.return_value = (
            status.ApplicationStatus.DISABLED,
            "",
        )
        m_applicability_status.return_value = (
            status.ApplicabilityStatus.APPLICABLE,
            "",
        )
        assert entitlement.process_contract_deltas(
            {"entitlement": {"entitled": True}},
            {
                "entitlement": {"obligations": {"enableByDefault": True}},
                "resourceToken": "repotest-token",
            },
            allow_enable=False,
        )
        assert [] == m_enable.call_args_list
        expected_msg = status.MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
            name="repotest"
        )
        assert expected_msg in caplog_text()

    @pytest.mark.parametrize("packages", ([], ["extremetuxracer"]))
    @mock.patch.object(RepoTestEntitlement, "install_packages")
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch.object(RepoTestEntitlement, "setup_apt_config")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "application_status")
    @mock.patch.object(RepoTestEntitlement, "_check_apt_url_is_applied")
    def test_update_apt_config_and_install_packages_when_active(
        self,
        m_check_apt_url_applied,
        m_application_status,
        m_remove_apt_config,
        m_setup_apt_config,
        m_remove_auth_apt_repo,
        m_install_packages,
        packages,
        entitlement,
    ):
        """Update_apt_config and packages if active and not enableByDefault."""
        m_check_apt_url_applied.return_value = False
        application_status = status.ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        deltas = {
            "entitlement": {"obligations": {"enableByDefault": False}},
            "resourceToken": "repotest-token",
        }
        if packages:
            deltas["entitlement"] = {
                "directives": {"additionalPackages": packages}
            }

        assert entitlement.process_contract_deltas(
            {"entitlement": {"entitled": True}}, deltas
        )
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_setup_apt_config.call_args_list
        if packages:
            assert [
                mock.call(package_list=packages)
            ] == m_install_packages.call_args_list
        else:
            assert 0 == m_install_packages.call_count
        assert [] == m_remove_auth_apt_repo.call_args_list
        assert 1 == m_check_apt_url_applied.call_count

    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement.process_contract_deltas"
    )
    @mock.patch("uaclient.config.UAConfig.read_cache")
    @mock.patch(
        M_PATH + "util.get_platform_info", return_value={"series": "trusty"}
    )
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch.object(RepoTestEntitlement, "setup_apt_config")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "_check_apt_url_is_applied")
    def test_remove_old_auth_apt_repo_when_active_and_apt_url_delta(
        self,
        m_check_apt_url_applied,
        m_remove_apt_config,
        m_setup_apt_config,
        m_remove_auth_apt_repo,
        m_platform_info,
        m_read_cache,
        m_process_contract_deltas,
        entitlement,
    ):
        """Remove old apt url when aptURL delta occurs on active service."""
        m_check_apt_url_applied.return_value = False
        m_process_contract_deltas.return_value = False
        m_read_cache.return_value = {
            "services": [{"name": "repotest", "status": "enabled"}]
        }
        assert entitlement.process_contract_deltas(
            {
                "entitlement": {
                    "entitled": True,
                    "directives": {"aptURL": "http://old"},
                }
            },
            {
                "entitlement": {
                    "obligations": {"enableByDefault": False},
                    "directives": {"aptURL": "http://new"},
                },
                "resourceToken": "repotest-token",
            },
        )
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_setup_apt_config.call_args_list
        apt_auth_remove_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-repotest.list", "http://old"
            )
        ]
        assert apt_auth_remove_calls == m_remove_auth_apt_repo.call_args_list
        assert [
            mock.call("status-cache"),
            mock.call("status-cache"),
        ] == m_read_cache.call_args_list
        assert 1 == m_process_contract_deltas.call_count

        assert [
            mock.call("http://new")
        ] == m_check_apt_url_applied.call_args_list
        assert 1 == m_check_apt_url_applied.call_count

    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement.process_contract_deltas"
    )
    @mock.patch("uaclient.config.UAConfig.read_cache")
    @mock.patch(
        M_PATH + "util.get_platform_info", return_value={"series": "trusty"}
    )
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch.object(RepoTestEntitlement, "setup_apt_config")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "_check_apt_url_is_applied")
    def test_system_does_not_change_when_apt_url_delta_already_applied(
        self,
        m_check_apt_url_applied,
        m_remove_apt_config,
        m_setup_apt_config,
        m_remove_auth_apt_repo,
        m_platform_info,
        m_read_cache,
        m_process_contract_deltas,
        entitlement,
    ):
        """Do not change system if apt url delta is already applied."""
        m_check_apt_url_applied.return_value = True
        m_process_contract_deltas.return_value = False
        m_read_cache.return_value = {
            "services": [{"name": "repotest", "status": "enabled"}]
        }
        assert entitlement.process_contract_deltas(
            {
                "entitlement": {
                    "entitled": True,
                    "directives": {"aptURL": "http://old"},
                }
            },
            {
                "entitlement": {
                    "obligations": {"enableByDefault": False},
                    "directives": {"aptURL": "http://new"},
                },
                "resourceToken": "repotest-token",
            },
        )
        assert m_remove_apt_config.call_count == 0
        assert m_setup_apt_config.call_count == 0
        assert m_remove_auth_apt_repo.call_count == 0

        assert [
            mock.call("status-cache"),
            mock.call("status-cache"),
        ] == m_read_cache.call_args_list
        assert 1 == m_process_contract_deltas.call_count

        assert [
            mock.call("http://new")
        ] == m_check_apt_url_applied.call_args_list
        assert 1 == m_check_apt_url_applied.call_count


class TestRepoEnable:
    @pytest.mark.parametrize(
        "pre_enable_msg, output, can_enable_call_count",
        (
            (["msg1", (lambda: False, {}), "msg2"], "msg1\n", 0),
            (["msg1", (lambda: True, {}), "msg2"], "msg1\nmsg2\n", 1),
        ),
    )
    @mock.patch.object(
        RepoTestEntitlement,
        "can_enable",
        return_value=(False, status.CanEnableFailure(None)),
    )
    def test_enable_can_exit_on_pre_enable_messaging_hooks(
        self,
        m_can_enable,
        pre_enable_msg,
        output,
        can_enable_call_count,
        entitlement,
        capsys,
    ):
        with mock.patch(
            M_PATH + "RepoEntitlement.messaging",
            new_callable=mock.PropertyMock,
        ) as m_messaging:
            m_messaging.return_value = {"pre_enable": pre_enable_msg}
            with mock.patch.object(type(entitlement), "packages", []):
                entitlement.enable()
        stdout, _ = capsys.readouterr()
        assert output == stdout
        assert can_enable_call_count == m_can_enable.call_count

    @pytest.mark.parametrize(
        "pre_disable_msg,post_disable_msg,output,retval",
        (
            (
                ["pre1", (lambda: False, {}), "pre2"],
                ["post1"],
                "pre1\n",
                False,
            ),
            (["pre1", (lambda: True, {}), "pre2"], [], "pre1\npre2\n", True),
            (
                ["pre1", (lambda: True, {}), "pre2"],
                ["post1", (lambda: False, {}), "post2"],
                "pre1\npre2\npost1\n",
                False,
            ),
            (
                ["pre1", (lambda: True, {}), "pre2"],
                ["post1", (lambda: True, {}), "post2"],
                "pre1\npre2\npost1\npost2\n",
                True,
            ),
        ),
    )
    @mock.patch(M_PATH + "util.subp", return_value=("", ""))
    @mock.patch(M_PATH + "util.should_reboot")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "can_disable", return_value=True)
    def test_enable_can_exit_on_pre_or_post_disable_messaging_hooks(
        self,
        _can_disable,
        remove_apt_config,
        m_should_reboot,
        m_subp,
        pre_disable_msg,
        post_disable_msg,
        output,
        retval,
        entitlement,
        capsys,
    ):
        messaging = {
            "pre_disable": pre_disable_msg,
            "post_disable": post_disable_msg,
        }
        m_should_reboot.return_value = False
        with mock.patch.object(type(entitlement), "messaging", messaging):
            with mock.patch.object(type(entitlement), "packages", []):
                assert retval is entitlement.disable()
        stdout, _ = capsys.readouterr()
        assert output == stdout

    @pytest.mark.parametrize("should_reboot", (False, True))
    @pytest.mark.parametrize("with_pre_install_msg", (False, True))
    @pytest.mark.parametrize("packages", (["a"], [], None))
    @mock.patch(M_PATH + "util.should_reboot")
    @mock.patch(M_PATH + "util.subp", return_value=("", ""))
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "os.path.exists", return_value=True)
    @mock.patch(M_PATH + "util.get_platform_info")
    @mock.patch.object(
        RepoTestEntitlement, "can_enable", return_value=(True, None)
    )
    def test_enable_calls_adds_apt_repo_and_calls_apt_update(
        self,
        m_can_enable,
        m_platform,
        m_exists,
        m_apt_add,
        m_subp,
        m_should_reboot,
        entitlement,
        capsys,
        caplog_text,
        tmpdir,
        packages,
        with_pre_install_msg,
        should_reboot,
    ):
        """On enable add authenticated apt repo and refresh package lists."""
        m_platform.return_value = {"series": "xenial"}
        m_should_reboot.return_value = should_reboot

        pre_install_msgs = ["Some pre-install information", "Some more info"]
        if with_pre_install_msg:
            messaging_patch = mock.patch(
                M_PATH + "RepoEntitlement.messaging",
                new_callable=mock.PropertyMock,
                return_value={"pre_install": pre_install_msgs},
            )
        else:
            messaging_patch = mock.MagicMock()

        expected_apt_calls = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
                env={},
            )
        ]

        reboot_msg = "A reboot is required to complete install."
        expected_output = (
            "\n".join(
                ["Updating package lists", "Repo Test Class enabled"]
                + ([reboot_msg] if should_reboot else [])
            )
            + "\n"
        )

        if packages is not None:
            if len(packages) > 0:
                expected_apt_calls.append(
                    mock.call(
                        [
                            "apt-get",
                            "install",
                            "--assume-yes",
                            " ".join(packages),
                        ],
                        capture=True,
                        retry_sleeps=apt.APT_RETRIES,
                        env={},
                    )
                )
                expected_output = (
                    "\n".join(
                        ["Updating package lists"]
                        + (pre_install_msgs if with_pre_install_msg else [])
                        + [
                            "Installing Repo Test Class packages",
                            "Repo Test Class enabled",
                        ]
                        + ([reboot_msg] if should_reboot else [])
                    )
                    + "\n"
                )
        else:
            packages = entitlement.packages

        # We patch the type of entitlement because packages is a property
        with mock.patch.object(type(entitlement), "packages", packages):
            with messaging_patch:
                entitlement.enable()

        expected_calls = [
            mock.call(apt.APT_METHOD_HTTPS_FILE),
            mock.call(apt.CA_CERTIFICATES_FILE),
        ]
        assert expected_calls in m_exists.call_args_list
        assert expected_apt_calls == m_subp.call_args_list
        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-repotest.list",
                "http://REPOTEST",
                "repotest-token",
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]
        assert add_apt_calls == m_apt_add.call_args_list
        assert 1 == m_should_reboot.call_count
        stdout, _ = capsys.readouterr()
        assert expected_output == stdout

    @mock.patch(M_PATH + "util.subp")
    def test_failed_install_removes_apt_config_and_packages(
        self, m_subp, entitlement
    ):
        def fake_subp(args, *other_args, **kwargs):
            if "install" in args:
                raise util.ProcessExecutionError(args)

        m_subp.side_effect = fake_subp

        packages = ["fake_pkg", "and_another"]
        with mock.patch.object(entitlement, "setup_apt_config"):
            with mock.patch.object(
                entitlement, "can_enable", return_value=(True, None)
            ):
                with mock.patch.object(
                    type(entitlement), "packages", packages
                ):
                    with pytest.raises(exceptions.UserFacingError) as excinfo:
                        with mock.patch.object(
                            entitlement, "remove_apt_config"
                        ) as m_rac:
                            entitlement.enable()

        assert "Could not enable Repo Test Class." == excinfo.value.msg
        assert 1 == m_rac.call_count


class TestRemoveAptConfig:
    def test_missing_aptURL(self, entitlement_factory):
        # Make aptURL missing
        entitlement = entitlement_factory(RepoTestEntitlement, directives={})

        with pytest.raises(exceptions.MissingAptURLDirective) as excinfo:
            entitlement.remove_apt_config()

        assert "repotest" in str(excinfo.value)

    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_apt_get_update_called(
        self, m_run_apt_command, _m_apt1, _m_apt2, entitlement
    ):
        entitlement.remove_apt_config()

        expected_call = mock.call(["apt-get", "update"], mock.ANY)
        assert expected_call in m_run_apt_command.call_args_list

    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_disable_apt_auth_only_false_removes_all_apt_config(
        self,
        m_get_platform,
        _m_run_apt_command,
        m_remove_apt_list_files,
        m_remove_auth_apt_repo,
        entitlement_factory,
    ):
        """Remove all APT config when disable_apt_auth_only is False"""
        m_get_platform.return_value = {"series": "xenial"}

        entitlement = entitlement_factory(
            RepoTestEntitlementDisableAptAuthOnlyFalse,
            affordances={"series": ["xenial"]},
        )
        entitlement.remove_apt_config()

        assert [
            mock.call("http://REPOTEST", "xenial")
        ] == m_remove_apt_list_files.call_args_list
        assert [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-repotest.list",
                "http://REPOTEST",
                "test.gpg",
            )
        ] == m_remove_auth_apt_repo.call_args_list

    @mock.patch(M_PATH + "apt.remove_repo_from_apt_auth_file")
    @mock.patch(M_PATH + "apt.restore_commented_apt_list_file")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_disable_apt_auth_only_removes_authentication_for_repo(
        self,
        m_get_platform,
        _m_run_apt_command,
        m_restore_commented_apt_list_file,
        m_remove_repo_from_apt_auth_file,
        entitlement_factory,
    ):
        """Remove APT authentication for repos with disable_apt_auth_only.

        Any commented APT list entries are restored to uncommented lines.
        """
        m_get_platform.return_value = {"series": "xenial"}
        entitlement = entitlement_factory(
            RepoTestEntitlementDisableAptAuthOnly,
            affordances={"series": ["xenial"]},
        )
        entitlement.remove_apt_config()

        assert [
            mock.call("http://REPOTEST")
        ] == m_remove_repo_from_apt_auth_file.call_args_list
        assert [
            mock.call("/etc/apt/sources.list.d/ubuntu-repotest.list")
        ] == m_restore_commented_apt_list_file.call_args_list

    @mock.patch(M_PATH + "apt.add_ppa_pinning")
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_repo_pin_priority_never_configures_repo_pinning_on_remove(
        self,
        m_get_platform,
        _m_run_apt_command,
        _m_remove_apt_list_files,
        _m_remove_auth_apt_repo,
        m_add_ppa_pinning,
        entitlement_factory,
    ):
        """Pin the repo 'never' when repo_pin_priority is never."""
        m_get_platform.return_value = {"series": "xenial"}

        entitlement = entitlement_factory(
            RepoTestEntitlementRepoPinNever, affordances={"series": ["xenial"]}
        )
        entitlement.remove_apt_config()
        assert [
            mock.call(
                "/etc/apt/preferences.d/ubuntu-repotest",
                "http://REPOTEST",
                None,
                "never",
            )
        ] == m_add_ppa_pinning.call_args_list

    @mock.patch(M_PATH + "os.unlink")
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_repo_pin_priority_int_removes_apt_preferences(
        self,
        m_get_platform,
        _m_run_apt_command,
        _m_remove_apt_list_files,
        _m_remove_auth_apt_repo,
        m_unlink,
        entitlement_factory,
    ):
        """Remove apt preferences file when repo_pin_priority is an int."""
        m_get_platform.return_value = {"series": "xenial"}

        entitlement = entitlement_factory(
            RepoTestEntitlementRepoPinInt, affordances={"series": ["xenial"]}
        )

        assert 1000 == entitlement.repo_pin_priority
        with mock.patch(M_PATH + "os.path.exists") as m_exists:
            m_exists.return_value = True
            entitlement.remove_apt_config()
        expected_call = [mock.call("/etc/apt/preferences.d/ubuntu-repotest")]
        assert expected_call == m_exists.call_args_list
        assert expected_call == m_unlink.call_args_list


class TestSetupAptConfig:
    @pytest.mark.parametrize(
        "repo_cls,directives,exc_cls,err_msg",
        (
            (
                RepoTestEntitlement,
                {},
                exceptions.UserFacingError,
                "Ubuntu Advantage server provided no aptKey directive for"
                " repotest.",
            ),
            (
                RepoTestEntitlement,
                {"aptKey": "somekey"},
                exceptions.MissingAptURLDirective,
                "repotest",
            ),
            (
                RepoTestEntitlement,
                {"aptKey": "somekey", "aptURL": "someURL"},
                exceptions.UserFacingError,
                "Empty repotest apt suites directive from"
                " https://contracts.canonical.com",
            ),
        ),
    )
    def test_missing_directives(
        self, repo_cls, directives, exc_cls, err_msg, entitlement_factory
    ):
        """Raise an error when missing any required directives."""
        entitlement = entitlement_factory(repo_cls, directives=directives)

        with pytest.raises(exc_cls) as excinfo:
            entitlement.setup_apt_config()
        assert err_msg in str(excinfo.value)

    @pytest.mark.parametrize("enable_by_default", (True, False))
    @mock.patch(M_CONTRACT_PATH + "request_resource_machine_access")
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_setup_apt_config_request_machine_access_when_no_resource_token(
        self,
        run_apt_command,
        add_auth_apt_repo,
        request_resource_machine_access,
        enable_by_default,
        entitlement_factory,
        caplog_text,
    ):
        """request_machine_access routes when contract lacks resourceToken."""
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            obligations={"enableByDefault": enable_by_default},
        )
        machine_token = entitlement.cfg.read_cache("machine-token")
        # Drop resourceTokens values from base machine-token.
        machine_token["resourceTokens"] = []
        entitlement.cfg.write_cache("machine-token", machine_token)
        entitlement.setup_apt_config()
        expected_msg = (
            "No resourceToken present in contract for service Repo Test"
            " Class. Using machine token as credentials"
        )
        if enable_by_default:
            assert expected_msg in caplog_text()
            assert 0 == request_resource_machine_access.call_count
        else:
            assert expected_msg not in caplog_text()
            assert [
                mock.call("blah", "repotest")
            ] == request_resource_machine_access.call_args_list

    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_install_prerequisite_packages(
        self, m_run_apt_command, m_add_auth_repo, entitlement
    ):
        """Install apt-transport-https and ca-certificates debs if absent.

        Presence is determined based on checking known files from those debs.
        It avoids a costly round-trip shelling out to call dpkg -l.
        """
        with mock.patch(M_PATH + "os.path.exists") as m_exists:
            m_exists.return_value = False
            entitlement.setup_apt_config()
        assert [
            mock.call("/usr/lib/apt/methods/https"),
            mock.call("/usr/sbin/update-ca-certificates"),
        ] == m_exists.call_args_list
        install_call = mock.call(
            [
                "apt-get",
                "install",
                "--assume-yes",
                "apt-transport-https",
                "ca-certificates",
            ],
            "APT install failed.",
        )
        assert install_call in m_run_apt_command.call_args_list

    @mock.patch(M_PATH + "util.get_platform_info")
    def test_setup_error_with_repo_pin_priority_and_missing_origin(
        self, m_get_platform_info, entitlement_factory
    ):
        """Raise error when repo_pin_priority is set and origin is None."""
        m_get_platform_info.return_value = {"series": "xenial"}
        entitlement = entitlement_factory(
            RepoTestEntitlementRepoPinNever, affordances={"series": ["xenial"]}
        )
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            entitlement.setup_apt_config()
        assert (
            "Cannot setup apt pin. Empty apt repo origin value 'None'."
            in str(excinfo.value)
        )

    @mock.patch(M_PATH + "os.unlink")
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_setup_with_repo_pin_priority_never_removes_apt_preferences_file(
        self,
        m_get_platform_info,
        m_run_apt_command,
        m_add_auth_repo,
        m_unlink,
        entitlement_factory,
    ):
        """When repo_pin_priority is never, disable repo in apt preferences."""
        m_get_platform_info.return_value = {"series": "xenial"}
        entitlement = entitlement_factory(
            RepoTestEntitlementRepoPinNever, affordances={"series": ["xenial"]}
        )
        entitlement.origin = "RepoTestOrigin"  # don't error on origin = None
        with mock.patch(M_PATH + "os.path.exists") as m_exists:
            m_exists.return_value = True
            entitlement.setup_apt_config()
        assert [
            mock.call("/etc/apt/preferences.d/ubuntu-repotest"),
            mock.call("/usr/lib/apt/methods/https"),
            mock.call("/usr/sbin/update-ca-certificates"),
        ] == m_exists.call_args_list
        assert [
            mock.call("/etc/apt/preferences.d/ubuntu-repotest")
        ] == m_unlink.call_args_list

    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "apt.add_ppa_pinning")
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_setup_with_repo_pin_priority_int_adds_a_pins_repo_apt_preference(
        self,
        m_get_platform_info,
        m_add_ppa_pinning,
        m_run_apt_command,
        m_add_auth_repo,
        entitlement_factory,
    ):
        """When repo_pin_priority is an int, set pin in apt preferences."""
        m_get_platform_info.return_value = {"series": "xenial"}
        entitlement = entitlement_factory(
            RepoTestEntitlementRepoPinInt, affordances={"series": ["xenial"]}
        )
        entitlement.origin = "RepoTestOrigin"  # don't error on origin = None
        with mock.patch(M_PATH + "os.path.exists") as m_exists:
            m_exists.return_value = True  # Skip prerequisite pkg installs
            entitlement.setup_apt_config()
        assert [
            mock.call("/usr/lib/apt/methods/https"),
            mock.call("/usr/sbin/update-ca-certificates"),
        ] == m_exists.call_args_list
        assert [
            mock.call(
                "/etc/apt/preferences.d/ubuntu-repotest",
                "http://REPOTEST",
                "RepoTestOrigin",
                entitlement.repo_pin_priority,
            )
        ] == m_add_ppa_pinning.call_args_list
        assert [
            mock.call(["apt-get", "update"], "APT update failed.")
        ] == m_run_apt_command.call_args_list


class TestApplicationStatus:
    # TODO: Write tests for all functionality

    def test_missing_aptURL(self, entitlement_factory):
        # Make aptURL missing
        entitlement = entitlement_factory(RepoTestEntitlement, directives={})

        application_status, explanation = entitlement.application_status()

        assert status.ApplicationStatus.DISABLED == application_status
        assert (
            "Repo Test Class does not have an aptURL directive" == explanation
        )

    @pytest.mark.parametrize(
        "pin,policy_url,enabled",
        (
            (500, "https://esm.ubuntu.com/apps/ubuntu", False),
            (-32768, "https://esm.ubuntu.com/ubuntu", False),
            (500, "https://esm.ubuntu.com/ubuntu", True),
        ),
    )
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_enabled_status_by_apt_policy(
        self, m_run_apt_command, pin, policy_url, enabled, entitlement_factory
    ):
        """Report ENABLED when apt-policy lists specific aptURL and 500 pin."""
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            directives={"aptURL": "https://esm.ubuntu.com"},
        )

        policy_lines = [
            "{pin} {policy_url} bionic-security/main amd64 Packages".format(
                pin=pin, policy_url=policy_url
            ),
            " release v=18.04,o=UbuntuESMApps,...,n=bionic,l=UbuntuESMApps",
            "  origin esm.ubuntu.com",
        ]
        m_run_apt_command.return_value = "\n".join(policy_lines)

        application_status, explanation = entitlement.application_status()

        if enabled:
            expected_status = status.ApplicationStatus.ENABLED
            expected_explanation = "Repo Test Class is active"
        else:
            expected_status = status.ApplicationStatus.DISABLED
            expected_explanation = "Repo Test Class is not configured"
        assert expected_status == application_status
        assert expected_explanation == explanation


def success_call():
    print("success")
    return True


def fail_call(a=None):
    print("fail %s" % a)
    return False


class TestHandleMessageOperations:
    @pytest.mark.parametrize(
        "msg_ops, retval, output",
        (
            ([], True, ""),
            (["msg1", "msg2"], True, "msg1\nmsg2\n"),
            (
                [(success_call, {}), "msg1", (fail_call, {"a": 1}), "msg2"],
                False,
                "success\nmsg1\nfail 1\n",
            ),
        ),
    )
    def test_handle_message_operations_for_strings_and_callables(
        self, msg_ops, retval, output, capsys
    ):
        assert retval is util.handle_message_operations(msg_ops)
        out, _err = capsys.readouterr()
        assert output == out
