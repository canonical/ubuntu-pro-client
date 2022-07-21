import mock
import pytest

from lib.auto_attach import check_cloudinit_userdata_for_ua_info, main
from uaclient.exceptions import (
    AlreadyAttachedOnPROError,
    ProcessExecutionError,
)


class TestCheckCloudinitUserdataForUAInfo:
    @mock.patch("lib.auto_attach.which")
    def test_check_cloudinit_data_returns_false_if_no_cloudinit(self, m_which):
        m_which.return_value = False
        assert False is check_cloudinit_userdata_for_ua_info()

    @mock.patch("lib.auto_attach.subp")
    @mock.patch("lib.auto_attach.which")
    def test_check_cloudinit_data_returns_false_if_query_error(
        self, m_which, m_subp
    ):
        m_which.return_value = True
        m_subp.side_effect = ProcessExecutionError("test")

        assert False is check_cloudinit_userdata_for_ua_info()

    @mock.patch("lib.auto_attach.subp")
    @mock.patch("lib.auto_attach.which")
    def test_check_cloudinit_data_returns_false_if_yaml_error(
        self, m_which, m_subp
    ):
        m_which.return_value = True
        m_subp.return_value = (
            """\
            [invalid, yaml]:
              - test
            """,
            "",
        )

        assert False is check_cloudinit_userdata_for_ua_info()

    @pytest.mark.parametrize(
        "expected,userdata",
        (
            (
                False,
                "",
            ),
            (
                False,
                """\
                #cloud-config
                runcmd:
                  - echo "test"
                """,
            ),
            (
                True,
                """\
                #cloud-config
                ubuntu_advantage:
                 - echo "test"
                """,
            ),
        ),
    )
    @mock.patch("lib.auto_attach.subp")
    @mock.patch("lib.auto_attach.which")
    def test_check_cloudinit_data(self, m_which, m_subp, expected, userdata):
        m_which.return_value = True
        m_subp.return_value = (userdata, "")

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
        m_cli_auto_attach.side_effect = AlreadyAttachedOnPROError(
            instance_id="inst"
        )
        main(cfg=FakeConfig())

        assert (
            "Skipping attach: Instance 'inst' is already attached."
            in caplog_text()
        )
