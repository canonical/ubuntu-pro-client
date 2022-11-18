import logging

import mock
import pytest

from lib.auto_attach import check_cloudinit_userdata_for_ua_info, main
from uaclient import messages
from uaclient.api.exceptions import (
    AlreadyAttachedError,
    AutoAttachDisabledError,
)
from uaclient.daemon import AUTO_ATTACH_STATUS_MOTD_FILE


class TestCheckCloudinitUserdataForUAInfo:
    @mock.patch("lib.auto_attach.get_cloudinit_init_stage")
    def test_check_cloudinit_data_returns_false_if_no_cloudinit(
        self, m_get_cloudinit_stage
    ):
        m_get_cloudinit_stage.return_value = None
        assert False is check_cloudinit_userdata_for_ua_info()

    @pytest.mark.parametrize(
        "expected,cloud_cfg",
        (
            (
                False,
                "",
            ),
            (
                False,
                {
                    "runcmd": ["echo test", "echo test2"],
                    "cloud_config_modules": ["ubuntu-advantage", "test"],
                },
            ),
            (
                True,
                {
                    "ubuntu_advantage": {"token": "TOKEN"},
                    "cloud_config_modules": ["ubuntu-advantage", "test"],
                },
            ),
        ),
    )
    @mock.patch("lib.auto_attach.get_cloudinit_init_stage")
    def test_check_cloudinit_data(
        self, m_get_cloudinit_stage, expected, cloud_cfg
    ):
        init_mock = mock.MagicMock()
        type(init_mock).cfg = mock.PropertyMock(return_value=cloud_cfg)
        m_get_cloudinit_stage.return_value = init_mock
        assert expected is check_cloudinit_userdata_for_ua_info()


@mock.patch("lib.auto_attach.system.remove_file")
@mock.patch("lib.auto_attach.system.write_file")
class TestMain:
    @pytest.mark.parametrize(
        "ubuntu_advantage_in_userdata",
        (
            (True,),
            (False,),
        ),
    )
    @mock.patch("lib.auto_attach.check_cloudinit_userdata_for_ua_info")
    @mock.patch("lib.auto_attach.full_auto_attach")
    def test_main(
        self,
        m_api_full_auto_attach,
        m_check_cloudinit,
        m_write_file,
        m_remove_file,
        ubuntu_advantage_in_userdata,
        caplog_text,
        FakeConfig,
    ):
        m_check_cloudinit.return_value = ubuntu_advantage_in_userdata
        main(cfg=FakeConfig())

        if not ubuntu_advantage_in_userdata:
            assert [
                mock.call(
                    AUTO_ATTACH_STATUS_MOTD_FILE, messages.AUTO_ATTACH_RUNNING
                )
            ] == m_write_file.call_args_list
            assert 1 == m_api_full_auto_attach.call_count
            assert [
                mock.call(AUTO_ATTACH_STATUS_MOTD_FILE)
            ] == m_remove_file.call_args_list
        else:
            assert 0 == m_api_full_auto_attach.call_count
            assert (
                "cloud-init userdata has ubuntu-advantage key."
            ) in caplog_text()
            assert (
                "Skipping auto-attach and deferring to cloud-init "
                "to setup and configure auto-attach"
            ) in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize(
        "api_side_effect, log_msg",
        [
            (
                AlreadyAttachedError("test_account"),
                "This machine is already attached to 'test_account'",
            ),
            (
                AutoAttachDisabledError,
                "Skipping auto-attach. Config disable_auto_attach is set.\n",
            ),
        ],
    )
    @mock.patch("lib.auto_attach.check_cloudinit_userdata_for_ua_info")
    @mock.patch("lib.auto_attach.full_auto_attach")
    def test_main_handles_errors(
        self,
        m_api_full_auto_attach,
        m_check_cloudinit,
        m_write_file,
        m_remove_file,
        api_side_effect,
        log_msg,
        caplog_text,
        FakeConfig,
    ):
        cfg = FakeConfig.for_attached_machine()
        m_check_cloudinit.return_value = False
        m_api_full_auto_attach.side_effect = api_side_effect

        main(cfg=cfg)

        assert (
            mock.call(
                AUTO_ATTACH_STATUS_MOTD_FILE, messages.AUTO_ATTACH_RUNNING
            )
            in m_write_file.call_args_list
        )
        assert m_api_full_auto_attach.call_count == 1
        assert log_msg in caplog_text()
        assert (
            mock.call(AUTO_ATTACH_STATUS_MOTD_FILE)
            in m_remove_file.call_args_list
        )
