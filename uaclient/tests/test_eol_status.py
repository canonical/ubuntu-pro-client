import mock

from uaclient.entitlements.esm import ESMInfraEntitlement
from uaclient.jobs.eol_status import check_eol_and_update

M_ENT = "uaclient.entitlements.esm."


class TestEOLStatus:
    @mock.patch(M_ENT + "ESMBaseEntitlement.setup_unauthenticated_repo")
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.is_active_esm", return_value=False)
    def test_repo_not_set_on_attached_machine(
        self,
        _is_active_esm,
        get_platform_info,
        setup_unauthenticated_repo,
        FakeConfig,
    ):
        cfg = FakeConfig().for_attached_machine()
        with mock.patch("os.path.exists", return_value=False):
            check_eol_and_update(cfg)
        assert get_platform_info.call_count == 0
        assert setup_unauthenticated_repo.call_count == 0

    @mock.patch(M_ENT + "ESMBaseEntitlement.setup_unauthenticated_repo")
    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch("uaclient.util.is_active_esm", return_value=False)
    def test_repo_not_set_on_active_esm(
        self,
        _is_active_esm,
        get_platform_info,
        setup_unauthenticated_repo,
        FakeConfig,
    ):
        cfg = FakeConfig()
        with mock.patch("os.path.exists", return_value=False):
            check_eol_and_update(cfg)
        assert get_platform_info.call_count == 1
        assert setup_unauthenticated_repo.call_count == 0

    @mock.patch("uaclient.util.get_platform_info")
    @mock.patch(M_ENT + "apt.setup_unauthenticated_repo")
    @mock.patch("uaclient.util.is_active_esm", return_value=True)
    def test_esm_infra_repo_set_on_unattached(
        self,
        _is_active_esm,
        apt_setup_unauthenticated_repo,
        get_platform_info,
        FakeConfig,
    ):
        cfg = FakeConfig()
        series = "eol-series"
        get_platform_info.return_value = {"series": series}
        with mock.patch("os.path.exists", return_value=False):
            check_eol_and_update(cfg)
        suite_prefix = series + "-" + "infra"
        infra_repo_fn = "/etc/apt/sources.list.d/ubuntu-{name}.list".format(
            name=ESMInfraEntitlement.name
        )
        infra_repo_pref_fn = "/etc/apt/preferences.d/ubuntu-{name}".format(
            name=ESMInfraEntitlement.name
        )
        expected = [
            mock.call(
                repo_filename=infra_repo_fn,
                repo_pref_filename=infra_repo_pref_fn,
                repo_url="https://esm.ubuntu.com/{service}".format(
                    service=ESMInfraEntitlement.apt_repo_name
                ),
                keyring_file=ESMInfraEntitlement.repo_key_file,
                apt_origin=ESMInfraEntitlement.origin,
                suites=[
                    "{suite_prefix}-security".format(
                        suite_prefix=suite_prefix
                    ),
                    "{suite_prefix}-updates".format(suite_prefix=suite_prefix),
                ],
            )
        ]
        assert get_platform_info.call_count == 2
        assert apt_setup_unauthenticated_repo.call_count == 1
        assert expected == apt_setup_unauthenticated_repo.call_args_list
