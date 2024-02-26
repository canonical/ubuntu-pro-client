import mock
import pytest

from uaclient import apt, exceptions, messages, util
from uaclient.entitlements.entitlement_status import (
    ApplicabilityStatus,
    ApplicationStatus,
)
from uaclient.entitlements.repo import RepoEntitlement

M_PATH = "uaclient.entitlements.repo."
M_CONTRACT_PATH = "uaclient.entitlements.repo.contract.UAContractClient."


class RepoTestEntitlement(RepoEntitlement):
    """Subclass so we can test shared repo functionality"""

    name = "repotest"
    title = "Repo Test Class"
    description = "Repo entitlement for testing"
    repo_key_file = "test.gpg"


class RepoTestEntitlementRepoWithPin(RepoTestEntitlement):
    repo_pin_priority = 1000


class RepoTestEntitlementRepoWithRemovePackages(RepoTestEntitlement):
    def remove_packages(self):
        pass


@pytest.fixture
def entitlement(entitlement_factory):
    return entitlement_factory(
        RepoTestEntitlement, affordances={"series": ["xenial"]}
    )


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
    @mock.patch.object(
        RepoTestEntitlement, "can_disable", return_value=(True, None)
    )
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
        application_status = ApplicationStatus.ENABLED
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
            ApplicationStatus.DISABLED,
            "",
        )
        m_applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
            "",
        )
        assert not entitlement.process_contract_deltas(
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
            ApplicationStatus.DISABLED,
            "",
        )
        m_applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
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
        capsys,
        event,
    ):
        """Log a message when inactive, enableByDefault and allow_enable."""
        m_application_status.return_value = (
            ApplicationStatus.DISABLED,
            "",
        )
        m_applicability_status.return_value = (
            ApplicabilityStatus.APPLICABLE,
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
        expected_msg = messages.ENABLE_BY_DEFAULT_MANUAL_TMPL.format(
            name="repotest"
        )
        assert expected_msg in capsys.readouterr()[1]

    @pytest.mark.parametrize("packages", ([], ["extremetuxracer"]))
    @mock.patch(
        "uaclient.files.state_files.status_cache_file.read", return_value=None
    )
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
        _m_status_cache,
        packages,
        entitlement,
    ):
        """Update_apt_config and packages if active and not enableByDefault."""
        m_check_apt_url_applied.return_value = False
        application_status = ApplicationStatus.ENABLED
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

    @pytest.mark.parametrize(
        "series,file_extension", (("jammy", "list"), ("noble", "sources"))
    )
    @mock.patch("uaclient.files.state_files.status_cache_file.read")
    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement.process_contract_deltas"
    )
    @mock.patch(M_PATH + "system.get_release_info")
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
        m_release_info,
        m_process_contract_deltas,
        m_status_cache_read,
        series,
        file_extension,
        entitlement,
    ):
        """Remove old apt url when aptURL delta occurs on active service."""
        m_check_apt_url_applied.return_value = False
        m_process_contract_deltas.return_value = False
        m_status_cache_read.return_value = {
            "services": [{"name": "repotest", "status": "enabled"}]
        }
        m_release_info.return_value.series = series
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
                "/etc/apt/sources.list.d/ubuntu-repotest.{}".format(
                    file_extension
                ),
                "http://old",
            )
        ]
        assert apt_auth_remove_calls == m_remove_auth_apt_repo.call_args_list
        assert [
            mock.call(),
            mock.call(),
        ] == m_status_cache_read.call_args_list
        assert 1 == m_process_contract_deltas.call_count

        assert [
            mock.call("http://new")
        ] == m_check_apt_url_applied.call_args_list
        assert 1 == m_check_apt_url_applied.call_count

    @mock.patch(
        "uaclient.entitlements.base.UAEntitlement.process_contract_deltas"
    )
    @mock.patch("uaclient.files.state_files.status_cache_file.read")
    @mock.patch(M_PATH + "system.get_release_info")
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
        m_release_info,
        m_status_cache_read,
        m_process_contract_deltas,
        entitlement,
    ):
        """Do not change system if apt url delta is already applied."""
        m_check_apt_url_applied.return_value = True
        m_process_contract_deltas.return_value = False
        m_status_cache_read.return_value = {
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
            mock.call(),
            mock.call(),
        ] == m_status_cache_read.call_args_list
        assert 1 == m_process_contract_deltas.call_count

        assert [
            mock.call("http://new")
        ] == m_check_apt_url_applied.call_args_list
        assert 1 == m_check_apt_url_applied.call_count


class TestRepoEnable:
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
    @mock.patch(M_PATH + "system.subp", return_value=("", ""))
    @mock.patch(M_PATH + "system.should_reboot")
    @mock.patch.object(RepoTestEntitlement, "remove_apt_config")
    @mock.patch.object(
        RepoTestEntitlement, "can_disable", return_value=(True, None)
    )
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
        event,
    ):
        messaging = {
            "pre_disable": pre_disable_msg,
            "post_disable": post_disable_msg,
        }
        m_should_reboot.return_value = False
        with mock.patch.object(type(entitlement), "messaging", messaging):
            with mock.patch.object(type(entitlement), "packages", []):
                ret, fail = entitlement.disable()
                assert retval == ret
        stdout, _ = capsys.readouterr()
        assert output == stdout

    @pytest.mark.parametrize("should_reboot", (False, True))
    @pytest.mark.parametrize("with_pre_install_msg", (False, True))
    @pytest.mark.parametrize("packages", (["a"], [], None))
    @pytest.mark.parametrize(
        "series,file_extension", (("xenial", "list"), ("noble", "sources"))
    )
    @mock.patch("uaclient.apt.update_sources_list")
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_PATH + "system.should_reboot")
    @mock.patch(M_PATH + "system.subp", return_value=("", ""))
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "exists", return_value=True)
    @mock.patch(M_PATH + "system.get_release_info")
    @mock.patch.object(
        RepoTestEntitlement, "can_enable", return_value=(True, None)
    )
    def test_enable_calls_adds_apt_repo_and_calls_apt_update(
        self,
        m_can_enable,
        m_release_info,
        m_exists,
        m_apt_add,
        m_subp,
        m_should_reboot,
        m_setup_apt_proxy,
        m_update_sources_list,
        entitlement,
        capsys,
        caplog_text,
        event,
        packages,
        series,
        file_extension,
        with_pre_install_msg,
        should_reboot,
    ):
        """On enable add authenticated apt repo and refresh package lists."""
        m_release_info.return_value = mock.MagicMock(series=series)
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

        expected_apt_calls = []

        reboot_msg = "A reboot is required to complete install."
        expected_output = (
            "\n".join(
                [
                    "Updating Repo Test Class package lists",
                    "Repo Test Class enabled",
                ]
                + ([reboot_msg] if should_reboot else [])
            )
            + "\n"
        )

        update_sources_list_call_count = 1
        if packages is not None:
            if len(packages) > 0:
                update_sources_list_call_count += 1
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
                        override_env_vars=None,
                    )
                )
                expected_output = (
                    "\n".join(
                        ["Updating Repo Test Class package lists"]
                        + (pre_install_msgs if with_pre_install_msg else [])
                        + ["Updating standard Ubuntu package lists"]
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
        assert (
            update_sources_list_call_count == m_update_sources_list.call_count
        )
        add_apt_calls = [
            mock.call(
                "/etc/apt/sources.list.d/ubuntu-repotest.{}".format(
                    file_extension
                ),
                "http://REPOTEST/ubuntu",
                "repotest-token",
                ["xenial"],
                entitlement.repo_key_file,
            )
        ]
        assert add_apt_calls == m_apt_add.call_args_list
        assert 1 == m_should_reboot.call_count
        assert 1 == m_setup_apt_proxy.call_count
        stdout, _ = capsys.readouterr()
        assert expected_output == stdout

    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_PATH + "system.subp")
    def test_failed_install_removes_apt_config_and_packages(
        self, m_subp, _m_setup_apt_proxy, entitlement
    ):
        def fake_subp(args, *other_args, **kwargs):
            if "install" in args:
                raise exceptions.ProcessExecutionError(args)

        m_subp.side_effect = fake_subp

        packages = ["fake_pkg", "and_another"]
        with mock.patch.object(entitlement, "setup_apt_config"):
            with mock.patch.object(
                entitlement, "can_enable", return_value=(True, None)
            ):
                with mock.patch.object(
                    type(entitlement), "packages", packages
                ):
                    with pytest.raises(exceptions.UbuntuProError) as excinfo:
                        with mock.patch.object(
                            entitlement, "remove_apt_config"
                        ) as m_rac:
                            entitlement.enable()

        assert (
            "Unexpected APT error.\n"
            "Invalid command specified '['apt-get', 'install', "
            "'--assume-yes', 'fake_pkg', 'and_another']'.\n"
            "See /var/log/ubuntu-advantage.log"
        ) == excinfo.value.msg
        assert 1 == m_rac.call_count


class TestPerformEnable:
    @pytest.mark.parametrize(
        [
            "supports_access_only",
            "access_only",
            "expected_setup_apt_calls",
            "expected_install_calls",
            "expected_check_for_reboot_calls",
        ],
        [
            (
                False,
                False,
                [mock.call(silent=mock.ANY)],
                [mock.call()],
                [mock.call(operation="install")],
            ),
            (
                False,
                True,
                [mock.call(silent=mock.ANY)],
                [mock.call()],
                [mock.call(operation="install")],
            ),
            (
                True,
                False,
                [mock.call(silent=mock.ANY)],
                [mock.call()],
                [mock.call(operation="install")],
            ),
            (
                True,
                True,
                [mock.call(silent=mock.ANY)],
                [],
                [],
            ),
        ],
    )
    @mock.patch(M_PATH + "RepoEntitlement._check_for_reboot_msg")
    @mock.patch(M_PATH + "RepoEntitlement.install_packages")
    @mock.patch(M_PATH + "RepoEntitlement.setup_apt_config")
    def test_perform_enable(
        self,
        m_setup_apt_config,
        m_install_packages,
        m_check_for_reboot_msg,
        supports_access_only,
        access_only,
        expected_setup_apt_calls,
        expected_install_calls,
        expected_check_for_reboot_calls,
        entitlement_factory,
    ):
        with mock.patch.object(
            RepoTestEntitlement, "supports_access_only", supports_access_only
        ):
            entitlement = entitlement_factory(
                RepoTestEntitlement,
                affordances={"series": ["xenial"]},
                access_only=access_only,
            )
            assert entitlement._perform_enable(silent=True) is True
            assert (
                m_setup_apt_config.call_args_list == expected_setup_apt_calls
            )
            assert m_install_packages.call_args_list == expected_install_calls
            assert (
                m_check_for_reboot_msg.call_args_list
                == expected_check_for_reboot_calls
            )


class TestRepoPerformDisable:
    @pytest.mark.parametrize("purge_value", (True, False))
    @mock.patch(M_PATH + "apt.get_installed_packages_by_origin")
    @mock.patch(M_PATH + "apt.get_remote_versions_for_package")
    @mock.patch(M_PATH + "RepoEntitlement.prompt_for_purge")
    @mock.patch(M_PATH + "RepoEntitlement.execute_removal")
    @mock.patch(M_PATH + "RepoEntitlement.execute_reinstall")
    @mock.patch(M_PATH + "RepoEntitlement.remove_apt_config")
    def test_purge_functions_are_called(
        self,
        m_remove_apt_config,
        m_execute_reinstall,
        m_execute_removal,
        m_prompt_for_purge,
        m_get_remote_versions,
        m_get_installed_packages,
        purge_value,
        entitlement_factory,
    ):

        m_packages = []
        for i in range(1, 6):
            package = mock.MagicMock()
            type(package).name = mock.PropertyMock(return_value=str(i))
            m_packages.append(package)

        m_get_installed_packages.return_value = m_packages

        def return_alternatives(p, exclude_origin):
            if not int(p.name) % 2:
                return [int(p.name)]
            return []

        m_get_remote_versions.side_effect = return_alternatives

        with mock.patch.object(RepoTestEntitlement, "origin", "TestOrigin"):
            entitlement = entitlement_factory(
                RepoTestEntitlement,
                affordances={"series": ["xenial"]},
                purge=purge_value,
            )
            assert entitlement._perform_disable() is True
            assert m_remove_apt_config.call_args_list == [
                mock.call(silent=mock.ANY)
            ]

            if purge_value:
                assert m_get_installed_packages.call_args_list == [
                    mock.call("TestOrigin")
                ]
                assert m_get_remote_versions.call_args_list == [
                    mock.call(m_packages[0], exclude_origin="TestOrigin"),
                    mock.call(m_packages[1], exclude_origin="TestOrigin"),
                    mock.call(m_packages[2], exclude_origin="TestOrigin"),
                    mock.call(m_packages[3], exclude_origin="TestOrigin"),
                    mock.call(m_packages[4], exclude_origin="TestOrigin"),
                ]
                assert m_prompt_for_purge.call_args_list == [
                    mock.call(
                        [m_packages[0], m_packages[2], m_packages[4]],
                        [(m_packages[1], 2), (m_packages[3], 4)],
                    )
                ]
                assert m_execute_removal.call_args_list == [
                    mock.call([m_packages[0], m_packages[2], m_packages[4]])
                ]
                assert m_execute_reinstall.call_args_list == [
                    mock.call([(m_packages[1], 2), (m_packages[3], 4)])
                ]
            else:
                assert m_get_installed_packages.call_args_list == []
                assert m_get_remote_versions.call_args_list == []
                assert m_prompt_for_purge.call_args_list == []
                assert m_execute_removal.call_args_list == []
                assert m_execute_reinstall.call_args_list == []

    @pytest.mark.parametrize(
        "repo_cls",
        (
            (RepoTestEntitlement),
            (RepoTestEntitlementRepoWithRemovePackages),
        ),
    )
    @mock.patch("uaclient.system.should_reboot", return_value=False)
    def test_disable_on_can_disable_true_removes_apt_config_and_packages(
        self,
        _m_should_reboot,
        repo_cls,
        entitlement_factory,
    ):
        """When can_disable, disable removes apt config and packages."""
        entitlement = entitlement_factory(repo_cls)

        if isinstance(entitlement, RepoTestEntitlementRepoWithRemovePackages):
            mock_remove_packages = mock.patch.object(
                entitlement, "remove_packages"
            )
        else:
            mock_remove_packages = mock.MagicMock()

        with mock.patch.object(
            entitlement, "can_disable", return_value=(True, None)
        ):
            with mock.patch.object(
                entitlement, "remove_apt_config"
            ) as m_remove_apt_config:
                with mock_remove_packages as m_remove_packages:
                    assert entitlement.disable(True)

        assert [mock.call(silent=True)] == m_remove_apt_config.call_args_list

        if isinstance(entitlement, RepoTestEntitlementRepoWithRemovePackages):
            assert [mock.call()] == m_remove_packages.call_args_list
        else:
            assert 0 == m_remove_packages.call_count


class TestPurge:
    # This circular import should NOT exist, test_apt needs a refactor.
    from uaclient.tests.test_apt import mock_package, mock_version

    packages_to_remove = [
        mock_package("remove1", mock_version("1.0")),
        mock_package("remove2", mock_version("1.0")),
    ]
    packages_to_reinstall = [
        (mock_package("reinstall1", mock_version("1.0")), mock_version("2.0")),
        (mock_package("reinstall2", mock_version("1.0")), mock_version("2.0")),
    ]
    mock_kernel_package = [mock_package("linux-image-1.2.3-4-fake")]

    def test_purge_kernel_check_true_if_no_kernel(self, entitlement_factory):
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            purge=True,
        )

        assert entitlement.purge_kernel_check(self.packages_to_remove) is True

    @mock.patch(
        M_PATH + "system.get_installed_ubuntu_kernels", return_value=[]
    )
    @mock.patch(M_PATH + "system.get_kernel_info")
    def test_purge_kernel_check_false_when_no_other_kernels(
        self, _m_kernel_info, _m_installed_kernels, entitlement_factory, capsys
    ):
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            purge=True,
        )

        assert (
            entitlement.purge_kernel_check(self.mock_kernel_package) is False
        )
        out, _err = capsys.readouterr()
        assert "No other valid Ubuntu kernel was found in the system" in out

    @pytest.mark.parametrize("prompt_answer", (True, False))
    @pytest.mark.parametrize(
        "current_kernel", ("1.2.3-4-fake", "2.3.4-5-fake")
    )
    @mock.patch(M_PATH + "util.prompt_for_confirmation")
    @mock.patch(
        M_PATH + "system.get_installed_ubuntu_kernels",
        return_value=["2.3.4-5-fake"],
    )
    @mock.patch(M_PATH + "system.get_kernel_info")
    def test_purge_kernel_check_prompts_if_other_kernels(
        self,
        m_kernel_info,
        _m_installed_kernels,
        m_confirmation,
        prompt_answer,
        current_kernel,
        entitlement_factory,
        capsys,
    ):
        m_kernel_info.return_value.uname_release = current_kernel
        m_confirmation.return_value = prompt_answer
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            purge=True,
        )

        assert (
            entitlement.purge_kernel_check(self.mock_kernel_package)
            is prompt_answer
        )

        out, _err = capsys.readouterr()
        assert "would uninstall the following kernel(s):" in out
        assert (
            "{} is the current running kernel.".format(current_kernel) in out
        )

    @pytest.mark.parametrize(
        "remove,reinstall,expected_print,expected_prompt",
        (
            (
                packages_to_remove,
                packages_to_reinstall,
                [
                    mock.call(["remove1", "remove2"]),
                    mock.call(["reinstall1", "reinstall2"]),
                ],
                [mock.call(messages.PROCEED_YES_NO)],
            ),
            (
                packages_to_remove,
                [],
                [mock.call(["remove1", "remove2"])],
                [mock.call(messages.PROCEED_YES_NO)],
            ),
            (
                [],
                packages_to_reinstall,
                [mock.call(["reinstall1", "reinstall2"])],
                [mock.call(messages.PROCEED_YES_NO)],
            ),
            ([], [], [], []),
        ),
    )
    @mock.patch(M_PATH + "util.print_package_list")
    @mock.patch(M_PATH + "util.prompt_for_confirmation")
    def test_prompt_for_purge(
        self,
        m_confirmation,
        m_print_packages,
        remove,
        reinstall,
        expected_print,
        expected_prompt,
        entitlement_factory,
    ):
        m_confirmation.return_value = True
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            purge=True,
        )

        assert entitlement.prompt_for_purge(remove, reinstall) is True
        assert m_print_packages.call_args_list == expected_print
        assert m_confirmation.call_args_list == expected_prompt

    @pytest.mark.parametrize(
        "remove,expected_remove",
        (
            (
                packages_to_remove,
                [
                    mock.call(
                        ["remove1", "remove2"],
                        messages.UNINSTALLING_PACKAGES_FAILED.format(
                            packages=["remove1", "remove2"]
                        ),
                    ),
                ],
            ),
            (
                [],
                [],
            ),
        ),
    )
    @mock.patch(M_PATH + "apt.purge_packages")
    @mock.patch(M_PATH + "apt.get_installed_packages_names")
    def test_execute_removal(
        self,
        m_installed_packages,
        m_apt_purge,
        remove,
        expected_remove,
        entitlement_factory,
    ):
        m_installed_packages.return_value = ["remove1", "remove2"]
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            purge=True,
        )
        entitlement.execute_removal(remove)

        assert m_apt_purge.call_args_list == expected_remove

    @pytest.mark.parametrize(
        "reinstall,expected_install",
        (
            (
                packages_to_reinstall,
                [
                    mock.call(
                        ["reinstall1=2.0", "reinstall2=2.0"],
                        apt_options=[
                            "--allow-downgrades",
                            '-o Dpkg::Options::="--force-confdef"',
                            '-o Dpkg::Options::="--force-confold"',
                        ],
                        override_env_vars={
                            "DEBIAN_FRONTEND": "noninteractive"
                        },
                    ),
                ],
            ),
            ([], []),
        ),
    )
    @mock.patch(M_PATH + "apt.run_apt_install_command")
    @mock.patch(M_PATH + "apt.get_installed_packages_names")
    def test_execute_reinstall(
        self,
        m_installed_packages,
        m_apt_install,
        reinstall,
        expected_install,
        entitlement_factory,
    ):
        m_installed_packages.return_value = ["reinstall1", "reinstall2"]
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            affordances={"series": ["xenial"]},
            purge=True,
        )
        entitlement.execute_reinstall(reinstall)

        assert m_apt_install.call_args_list == expected_install


class TestRemoveAptConfig:
    def test_missing_aptURL(self, entitlement_factory):
        # Make aptURL missing
        entitlement = entitlement_factory(RepoTestEntitlement, directives={})

        with pytest.raises(exceptions.MissingAptURLDirective) as excinfo:
            entitlement.remove_apt_config()

        assert "repotest" in str(excinfo.value)

    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_update_command")
    def test_apt_get_update_called(
        self, m_run_apt_update_command, _m_apt1, _m_apt2, entitlement
    ):
        entitlement.remove_apt_config()

        assert mock.call() in m_run_apt_update_command.call_args_list

    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "system.get_release_info")
    def test_disable_removes_all_apt_config(
        self,
        m_get_release_info,
        _m_run_apt_command,
        m_remove_apt_list_files,
        m_remove_auth_apt_repo,
        entitlement_factory,
    ):
        """Remove all APT config when disable_apt_auth_only is False"""
        m_get_release_info.return_value = mock.MagicMock(series="xenial")

        entitlement = entitlement_factory(
            RepoTestEntitlement,
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

    @mock.patch(M_PATH + "system.ensure_file_absent")
    @mock.patch(M_PATH + "apt.remove_auth_apt_repo")
    @mock.patch(M_PATH + "apt.remove_apt_list_files")
    @mock.patch(M_PATH + "apt.run_apt_command")
    @mock.patch(M_PATH + "system.get_release_info")
    @mock.patch(M_PATH + "contract.apply_contract_overrides")
    def test_repo_pin_priority_int_removes_apt_preferences(
        self,
        _m_contract_overrides,
        m_get_release_info,
        _m_run_apt_command,
        _m_remove_apt_list_files,
        _m_remove_auth_apt_repo,
        m_ensure_file_absent,
        entitlement_factory,
    ):
        """Remove apt preferences file when repo_pin_priority is an int."""
        m_get_release_info.return_value = mock.MagicMock(series="xenial")

        entitlement = entitlement_factory(
            RepoTestEntitlementRepoWithPin, affordances={"series": ["xenial"]}
        )

        assert 1000 == entitlement.repo_pin_priority
        entitlement.remove_apt_config()
        assert [
            mock.call("/etc/apt/preferences.d/ubuntu-repotest")
        ] == m_ensure_file_absent.call_args_list


class TestSetupAptConfig:
    @pytest.mark.parametrize(
        "repo_cls,directives,exc_cls,err_msg",
        (
            (
                RepoTestEntitlement,
                {},
                exceptions.UbuntuProError,
                "Ubuntu Pro server provided no aptKey directive for"
                " repotest",
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
                exceptions.UbuntuProError,
                "Ubuntu Pro server provided no suites directive for"
                " repotest",
            ),
        ),
    )
    @mock.patch("uaclient.apt.setup_apt_proxy")
    def test_missing_directives(
        self,
        _setup_apt_proxy,
        repo_cls,
        directives,
        exc_cls,
        err_msg,
        entitlement_factory,
    ):
        """Raise an error when missing any required directives."""
        entitlement = entitlement_factory(repo_cls, directives=directives)

        with pytest.raises(exc_cls) as excinfo:
            entitlement.setup_apt_config()
        assert err_msg in str(excinfo.value)

    @pytest.mark.parametrize("enable_by_default", (True, False))
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_CONTRACT_PATH + "get_resource_machine_access")
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_command")
    def test_setup_apt_config_request_machine_access_when_no_resource_token(
        self,
        run_apt_command,
        add_auth_apt_repo,
        _m_get_resource_machine_access,
        _setup_apt_proxy,
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
        machine_token = entitlement.cfg.machine_token_file.machine_token
        # Drop resourceTokens values from base machine-token.
        machine_token["resourceTokens"] = []
        entitlement.cfg.machine_token_file.write(machine_token)
        entitlement.setup_apt_config()
        expected_msg = (
            "No resourceToken present in contract for service Repo Test"
            " Class. Using machine token as credentials"
        )
        if enable_by_default:
            assert expected_msg in caplog_text()
            assert 0 == _m_get_resource_machine_access.call_count
        else:
            assert expected_msg not in caplog_text()
            assert [
                mock.call("blah", "repotest")
            ] == _m_get_resource_machine_access.call_args_list

    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch("os.path.exists", return_value=False)
    @mock.patch("uaclient.apt.add_auth_apt_repo")
    @mock.patch("uaclient.apt.run_apt_command")
    def test_calls_setup_apt_proxy(
        self,
        _m_run_apt_command,
        _m_add_auth_repo,
        _m_exists,
        m_setup_apt_proxy,
        entitlement,
    ):
        """Calls apt.setup_apt_proxy()"""
        entitlement.setup_apt_config()
        assert [
            mock.call(http_proxy=None, https_proxy=None, proxy_scope=None)
        ] == m_setup_apt_proxy.call_args_list

    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_install_command")
    @mock.patch(M_PATH + "contract.apply_contract_overrides")
    def test_install_prerequisite_packages(
        self,
        _m_contract_overrides,
        m_run_apt_install_command,
        m_add_auth_repo,
        _m_setup_apt_proxy,
        entitlement,
    ):
        """Install apt-transport-https and ca-certificates debs if absent.

        Presence is determined based on checking known files from those debs.
        It avoids a costly round-trip shelling out to call dpkg -l.
        """
        with mock.patch(M_PATH + "exists") as m_exists:
            m_exists.return_value = False
            entitlement.setup_apt_config()
        assert [
            mock.call("/usr/lib/apt/methods/https"),
            mock.call("/usr/sbin/update-ca-certificates"),
        ] == m_exists.call_args_list
        install_call = mock.call(
            packages=["apt-transport-https", "ca-certificates"]
        )
        assert install_call in m_run_apt_install_command.call_args_list

    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_PATH + "system.get_release_info")
    def test_setup_error_with_repo_pin_priority_and_missing_origin(
        self, m_get_release_info, _setup_apt_proxy, entitlement_factory
    ):
        """Raise error when repo_pin_priority is set and origin is None."""
        m_get_release_info.return_value = mock.MagicMock(series="xenial")
        entitlement = entitlement_factory(
            RepoTestEntitlementRepoWithPin, affordances={"series": ["xenial"]}
        )
        with pytest.raises(exceptions.UbuntuProError) as excinfo:
            entitlement.setup_apt_config()
        assert (
            "Cannot setup apt pin. Empty apt repo origin value for repotest"
            in str(excinfo.value)
        )

    @mock.patch("uaclient.apt.update_sources_list")
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch(M_PATH + "apt.add_auth_apt_repo")
    @mock.patch(M_PATH + "apt.run_apt_update_command")
    @mock.patch(M_PATH + "apt.add_ppa_pinning")
    @mock.patch(M_PATH + "system.get_release_info")
    @mock.patch(M_PATH + "contract.apply_contract_overrides")
    def test_setup_with_repo_pin_priority_int_adds_a_pins_repo_apt_preference(
        self,
        _m_apply_overrides,
        m_get_release_info,
        m_add_ppa_pinning,
        m_run_apt_update_command,
        m_add_auth_repo,
        m_update_sources_list,
        _m_setup_apt_proxy,
        entitlement_factory,
    ):
        """When repo_pin_priority is an int, set pin in apt preferences."""
        m_get_release_info.return_value = mock.MagicMock(series="xenial")
        entitlement = entitlement_factory(
            RepoTestEntitlementRepoWithPin, affordances={"series": ["xenial"]}
        )
        entitlement.origin = "RepoTestOrigin"  # don't error on origin = None
        with mock.patch(M_PATH + "exists") as m_exists:
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
        assert [] == m_run_apt_update_command.call_args_list
        assert 1 == m_update_sources_list.call_count


class TestCheckAptURLIsApplied:
    @pytest.mark.parametrize("apt_url", (("test"), (None)))
    @mock.patch("uaclient.system.load_file")
    def test_check_apt_url_for_commented_apt_source_file(
        self, m_load_file, apt_url, entitlement
    ):
        m_load_file.return_value = "#test1\n#test2\n"
        assert not entitlement._check_apt_url_is_applied(apt_url)

    @mock.patch("uaclient.system.load_file")
    def test_check_apt_url_when_delta_apt_url_is_none(
        self, m_load_file, entitlement
    ):
        m_load_file.return_value = "test1\n#test2\n"
        assert entitlement._check_apt_url_is_applied(apt_url=None)

    @pytest.mark.parametrize(
        "apt_url,expected", (("test", True), ("blah", False))
    )
    @mock.patch("uaclient.system.load_file")
    def test_check_apt_url_inspects_apt_source_file(
        self, m_load_file, apt_url, expected, entitlement
    ):
        m_load_file.return_value = "test\n#test2\n"
        assert expected == entitlement._check_apt_url_is_applied(apt_url)


class TestApplicationStatus:
    # TODO: Write tests for all functionality
    # 🤔

    def test_missing_aptURL(self, entitlement_factory):
        # Make aptURL missing
        entitlement = entitlement_factory(RepoTestEntitlement, directives={})

        application_status, explanation = entitlement.application_status()

        assert ApplicationStatus.DISABLED == application_status
        assert (
            "Repo Test Class does not have an aptURL directive"
            == explanation.msg
        )

    @pytest.mark.parametrize(
        "policy_url,enabled",
        (
            ("https://esm.ubuntu.com/apps/ubuntu", False),
            ("https://esm.ubuntu.com/ubuntu", True),
        ),
    )
    @mock.patch(M_PATH + "apt.get_apt_cache_policy")
    def test_enabled_status_by_apt_policy(
        self, m_run_apt_policy, policy_url, enabled, entitlement_factory
    ):
        """Report ENABLED when apt-policy lists specific aptURL."""
        entitlement = entitlement_factory(
            RepoTestEntitlement,
            directives={
                "aptURL": "https://esm.ubuntu.com",
                "suites": ["bionic-updates", "bionic-security"],
            },
        )

        policy_lines = [
            "500 {policy_url} bionic-security/main amd64 Packages".format(
                policy_url=policy_url
            ),
            " release v=18.04,o=UbuntuESMApps,...,n=bionic,l=UbuntuESMApps",
            "  origin esm.ubuntu.com",
        ]
        m_run_apt_policy.return_value = "\n".join(policy_lines)

        application_status, explanation = entitlement.application_status()

        if enabled:
            expected_status = ApplicationStatus.ENABLED
            expected_explanation = "Repo Test Class is active"
        else:
            expected_status = ApplicationStatus.DISABLED
            expected_explanation = "Repo Test Class is not configured"
        assert expected_status == application_status
        assert expected_explanation == explanation.msg


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
