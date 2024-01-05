import os.path

import mock
import pytest

from uaclient import apt
from uaclient.entitlements.esm import ESMAppsEntitlement, ESMInfraEntitlement
from uaclient.util import set_filename_extension

M_PATH = "uaclient.entitlements.esm.ESMInfraEntitlement."
M_REPOPATH = "uaclient.entitlements.repo."


@pytest.fixture(params=[ESMAppsEntitlement, ESMInfraEntitlement])
def entitlement(request, entitlement_factory):
    return entitlement_factory(request.param, suites=["xenial"])


@mock.patch("uaclient.timer.update_messaging.update_motd_messages")
@mock.patch(
    "uaclient.system.get_release_info",
    return_value=mock.MagicMock(series="xenial"),
)
class TestESMEntitlementDisable:
    @pytest.mark.parametrize("silent", [False, True])
    @mock.patch(M_PATH + "can_disable", return_value=(False, None))
    def test_disable_returns_false_on_can_disable_false_and_does_nothing(
        self,
        m_can_disable,
        _m_get_release_info,
        m_update_apt_and_motd_msgs,
        silent,
    ):
        """When can_disable is false disable returns false and noops."""
        entitlement = ESMInfraEntitlement({})

        with mock.patch(
            "uaclient.apt.remove_auth_apt_repo"
        ) as m_remove_apt, mock.patch.object(
            entitlement, "setup_local_esm_repo"
        ) as m_setup_repo:
            ret, fail = entitlement.disable(silent)
            assert ret is False
            assert fail is None

        assert [mock.call()] == m_can_disable.call_args_list
        assert 0 == m_remove_apt.call_count
        assert 0 == m_update_apt_and_motd_msgs.call_count
        assert 0 == m_setup_repo.call_count

    @pytest.mark.parametrize("is_active_esm", (True, False))
    @pytest.mark.parametrize("is_lts", (True, False))
    @mock.patch("uaclient.entitlements.esm.system.is_current_series_lts")
    @mock.patch(
        "uaclient.entitlements.esm.system.is_current_series_active_esm"
    )
    def test_disable_removes_config_and_updates_cache_and_messages(
        self,
        m_active_esm,
        m_lts,
        _m_get_release_info,
        m_update_apt_and_motd_msgs,
        is_active_esm,
        is_lts,
        entitlement,
    ):
        """When can_disable, disable removes apt configuration.
        Also updates messaging and sets up a local repository.
        """
        m_active_esm.return_value = is_active_esm
        m_lts.return_value = is_lts

        with mock.patch.object(
            entitlement, "can_disable", return_value=(True, None)
        ), mock.patch.object(
            entitlement, "remove_apt_config"
        ) as m_remove_apt_config, mock.patch.object(
            entitlement, "setup_local_esm_repo"
        ) as m_setup_repo:
            assert entitlement.disable(True)

        assert [mock.call(silent=True)] == m_remove_apt_config.call_args_list
        assert [
            mock.call(entitlement.cfg)
        ] == m_update_apt_and_motd_msgs.call_args_list
        if (
            not is_lts
            and entitlement.__class__ == ESMAppsEntitlement
            or not is_active_esm
            and entitlement.__class__ == ESMInfraEntitlement
        ):
            assert m_setup_repo.call_count == 0
        else:
            assert [mock.call()] == m_setup_repo.call_args_list


class TestUpdateESMCaches:
    @pytest.mark.parametrize("file_exists", (False, True))
    @mock.patch("uaclient.apt.os.path.exists")
    @mock.patch("uaclient.apt.system.get_release_info")
    @mock.patch("uaclient.apt.system.write_file")
    def test_setup_local_esm_repo(
        self,
        m_write_file,
        m_get_release_info,
        m_exists,
        file_exists,
        entitlement,
    ):
        m_get_release_info.return_value = mock.MagicMock(series="example")
        m_exists.return_value = file_exists

        entitlement.setup_local_esm_repo()

        if file_exists:
            assert m_write_file.call_count == 0

        else:
            suites = "{series}-{name}-security {series}-{name}-updates".format(
                name=entitlement.name[4:], series="example"
            )
            assert m_write_file.call_args_list == [
                mock.call(
                    set_filename_extension(
                        os.path.normpath(
                            apt.ESM_APT_ROOTDIR + entitlement.repo_file,
                        ),
                        "sources",
                    ),
                    apt.DEB822_REPO_FILE_CONTENT.format(
                        url="https://esm.ubuntu.com/{name}/ubuntu".format(
                            name=entitlement.name[4:]
                        ),
                        suites=suites,
                        keyrings_dir=apt.KEYRINGS_DIR,
                        keyring_file=entitlement.repo_key_file,
                        deb_src="",
                    ),
                )
            ]

    @mock.patch("uaclient.apt.system.ensure_file_absent")
    def test_disable_local_esm_repo(self, m_ensure_file_absent, entitlement):
        entitlement.disable_local_esm_repo()
        assert m_ensure_file_absent.call_args_list == [
            mock.call(
                os.path.normpath(
                    apt.ESM_APT_ROOTDIR
                    + apt.APT_KEYS_DIR
                    + entitlement.repo_key_file
                )
            ),
            mock.call(
                set_filename_extension(
                    os.path.normpath(
                        apt.ESM_APT_ROOTDIR + entitlement.repo_file,
                    ),
                    "sources",
                ),
            ),
            mock.call(
                set_filename_extension(
                    os.path.normpath(
                        apt.ESM_APT_ROOTDIR + entitlement.repo_file,
                    ),
                    "list",
                ),
            ),
        ]
