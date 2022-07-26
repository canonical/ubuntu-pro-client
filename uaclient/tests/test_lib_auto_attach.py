import mock
import pytest

from lib.auto_attach import check_cloudinit_userdata_for_ua_info, main
from uaclient.exceptions import AlreadyAttachedOnPROError


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


class TestMain:
    @pytest.mark.parametrize(
        "ubuntu_advantage_in_userdata",
        (
            (True,),
            (False,),
        ),
    )
    @mock.patch("lib.auto_attach.check_cloudinit_userdata_for_ua_info")
    @mock.patch("lib.auto_attach.action_auto_attach")
    def test_main(
        self,
        m_cli_auto_attach,
        m_check_cloudinit,
        ubuntu_advantage_in_userdata,
        caplog_text,
        FakeConfig,
    ):
        m_check_cloudinit.return_value = ubuntu_advantage_in_userdata
        main(cfg=FakeConfig())

        if not ubuntu_advantage_in_userdata:
            assert 1 == m_cli_auto_attach.call_count
        else:
            assert 0 == m_cli_auto_attach.call_count
            assert (
                "cloud-init userdata has ubuntu-advantage key."
            ) in caplog_text()
            assert (
                "Skipping auto-attach and deferring to cloud-init "
                "to setup and configure auto-attach"
            ) in caplog_text()

    @mock.patch("lib.auto_attach.check_cloudinit_userdata_for_ua_info")
    @mock.patch("lib.auto_attach.action_auto_attach")
    def test_main_when_already_attached(
        self,
        m_cli_auto_attach,
        m_check_cloudinit,
        FakeConfig,
        caplog_text,
    ):
        m_check_cloudinit.return_value = False
        m_cli_auto_attach.side_effect = AlreadyAttachedOnPROError()
        main(cfg=FakeConfig())

        assert (
            "Skipping auto-attach: Instance is already attached."
            in caplog_text()
        )
