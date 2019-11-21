import copy
from textwrap import dedent

import mock
import pytest
from types import MappingProxyType

from uaclient import apt
from uaclient import config
from uaclient.entitlements.repo import RepoEntitlement
from uaclient.entitlements.tests.conftest import machine_token
from uaclient import exceptions
from uaclient import status
from uaclient import util


M_PATH = "uaclient.entitlements.repo."

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
        no_entitlements = copy.deepcopy(machine_token(RepoTestEntitlement))
        # delete all enttlements
        no_entitlements["machineTokenInfo"]["contractInfo"][
            "resourceEntitlements"
        ].pop()
        entitlement.cfg.write_cache("machine-token", no_entitlements)
        entitlement.cfg.delete_cache_key("machine-access-repotest")
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
                "resourceToken": "TOKEN",
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
                "resourceToken": "TOKEN",
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
                "resourceToken": "TOKEN",
            },
            allow_enable=False,
        )
        assert [] == m_enable.call_args_list
        expected_msg = status.MESSAGE_ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
            name="repotest"
        )
        assert expected_msg in caplog_text()

    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch.object(RepoTestEntitlement, "setup_apt_config")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "application_status")
    def test_update_apt_config_when_active(
        self,
        m_application_status,
        m_remove_apt_config,
        m_setup_apt_config,
        m_remove_auth_apt_repo,
        entitlement,
    ):
        """Update_apt_config when service is active and not enableByDefault."""
        application_status = status.ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
        assert entitlement.process_contract_deltas(
            {"entitlement": {"entitled": True}},
            {
                "entitlement": {"obligations": {"enableByDefault": False}},
                "resourceToken": "TOKEN",
            },
        )
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_setup_apt_config.call_args_list
        assert [] == m_remove_auth_apt_repo.call_args_list

    @mock.patch(
        M_PATH + "util.get_platform_info", return_value={"series": "trusty"}
    )
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch.object(RepoTestEntitlement, "setup_apt_config")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(RepoTestEntitlement, "application_status")
    def test_remove_old_auth_apt_repo_when_active_and_apt_url_delta(
        self,
        m_application_status,
        m_remove_apt_config,
        m_setup_apt_config,
        m_remove_auth_apt_repo,
        m_platform_info,
        entitlement,
    ):
        """Remove old apt url when aptURL delta occurs on active service."""
        application_status = status.ApplicationStatus.ENABLED
        m_application_status.return_value = (application_status, "")
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
                "resourceToken": "TOKEN",
            },
        )
        assert [mock.call()] == m_remove_apt_config.call_args_list
        assert [mock.call()] == m_setup_apt_config.call_args_list
        apt_auth_remove_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-repotest-trusty.list",
                "http://old",
            )
        ]
        assert apt_auth_remove_calls == m_remove_auth_apt_repo.call_args_list
        apt_auth_remove_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-repotest-trusty.list",
                "http://old",
            )
        ]
        assert apt_auth_remove_calls == m_remove_auth_apt_repo.call_args_list


class TestRepoEnable:
    @pytest.mark.parametrize("silent_if_inapplicable", (True, False, None))
    @mock.patch.object(RepoTestEntitlement, "can_enable", return_value=False)
    def test_enable_passes_silent_if_inapplicable_through(
        self, m_can_enable, caplog_text, tmpdir, silent_if_inapplicable
    ):
        """When can_enable returns False enable returns False."""
        cfg = config.UAConfig(cfg={"data_dir": tmpdir.strpath})
        entitlement = RepoTestEntitlement(cfg)

        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs["silent_if_inapplicable"] = silent_if_inapplicable
        entitlement.enable(**kwargs)

        expected_call = mock.call(silent=bool(silent_if_inapplicable))
        assert [expected_call] == m_can_enable.call_args_list

    @pytest.mark.parametrize("with_pre_install_msg", (False, True))
    @pytest.mark.parametrize("packages", (["a"], [], None))
    @mock.patch(M_PATH + "util.subp", return_value=("", ""))
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "os.path.exists", return_value=True)
    @mock.patch(M_PATH + "util.get_platform_info")
    @mock.patch.object(RepoTestEntitlement, "can_enable", return_value=True)
    def test_enable_calls_adds_apt_repo_and_calls_apt_update(
        self,
        m_can_enable,
        m_platform,
        m_exists,
        m_apt_add,
        m_subp,
        entitlement,
        capsys,
        caplog_text,
        tmpdir,
        packages,
        with_pre_install_msg,
    ):
        """On enable add authenticated apt repo and refresh package lists."""
        m_platform.return_value = {"series": "xenial"}

        pre_install_msgs = ["Some pre-install information", "Some more info"]
        if with_pre_install_msg:
            messaging_patch = mock.patch.object(
                entitlement, "messaging", {"pre_install": pre_install_msgs}
            )
        else:
            messaging_patch = mock.MagicMock()

        expected_apt_calls = [
            mock.call(
                ["apt-get", "update"],
                capture=True,
                retry_sleeps=apt.APT_RETRIES,
            )
        ]
        expected_output = dedent(
            """\
        Updating package lists
        Repo Test Class enabled
        """
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
                    )
                )
                expected_output = (
                    "\n".join(
                        [
                            "Updating package lists",
                            "Installing Repo Test Class packages",
                        ]
                        + (pre_install_msgs if with_pre_install_msg else [])
                        + ["Repo Test Class enabled"]
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
                "/etc/apt/sources.list.d/ubuntu-repotest-xenial.list",
                "http://REPOTEST",
                "TOKEN",
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]
        assert add_apt_calls == m_apt_add.call_args_list
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
                entitlement, "can_enable", return_value=True
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
        expected_call = mock.call(
            ["apt-get", "remove", "--assume-yes"] + packages
        )
        assert expected_call in m_subp.call_args_list
        assert 1 == m_rac.call_count


class TestRemoveAptConfig:
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_apt_get_update_called(
        self, m_run_apt_command, _m_apt1, _m_apt2, entitlement
    ):
        entitlement.remove_apt_config()

        expected_call = mock.call(["apt-get", "update"], mock.ANY)
        assert expected_call in m_run_apt_command.call_args_list

    def test_missing_aptURL(self, entitlement_factory):
        # Make aptURL missing
        entitlement = entitlement_factory(RepoTestEntitlement, directives={})

        with pytest.raises(exceptions.MissingAptURLDirective) as excinfo:
            entitlement.remove_apt_config()

        assert "repotest" in str(excinfo.value)


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
