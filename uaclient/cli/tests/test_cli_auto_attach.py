import logging

import mock
import pytest

from uaclient import event_logger, exceptions, messages
from uaclient.api import exceptions as api_exceptions
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from uaclient.cli import main_error_handler
from uaclient.cli.auto_attach import auto_attach_command
from uaclient.testing import fakes

M_PATH = "uaclient.cli.auto_attach."


@mock.patch(M_PATH + "cli_util.util.we_are_currently_root", return_value=False)
def test_non_root_users_are_rejected(we_are_currently_root, FakeConfig):
    """Check that a UID != 0 will receive a message and exit non-zero"""

    cfg = FakeConfig()
    with pytest.raises(exceptions.NonRootUserError):
        auto_attach_command.action(mock.MagicMock(), cfg=cfg)


class TestActionAutoAttach:
    @mock.patch(M_PATH + "cli_util.post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_happy_path(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        FakeConfig,
    ):
        cfg = FakeConfig()

        assert 0 == auto_attach_command.action(mock.MagicMock(), cfg=cfg)

        assert [
            mock.call(
                FullAutoAttachOptions(enable=None, enable_beta=None),
                cfg=cfg,
                mode=event_logger.EventLoggerMode.CLI,
            )
        ] == m_full_auto_attach.call_args_list
        assert [mock.call(cfg)] == m_post_cli_attach.call_args_list

    @pytest.mark.parametrize(
        "api_side_effect,expected_err,expected_ret",
        (
            (
                exceptions.ConnectivityError(
                    cause=Exception("does-not-matter"), url="url"
                ),
                messages.E_ATTACH_FAILURE.msg,
                1,
            ),
        ),
    )
    @mock.patch(M_PATH + "event")
    @mock.patch(M_PATH + "cli_util.post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_handle_full_auto_attach_errors(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        m_event,
        api_side_effect,
        expected_err,
        expected_ret,
        FakeConfig,
    ):
        m_full_auto_attach.side_effect = (api_side_effect,)
        cfg = FakeConfig()

        assert expected_ret == auto_attach_command.action(
            mock.MagicMock(), cfg=cfg
        )

        assert [mock.call(expected_err)] == m_event.info.call_args_list
        assert [] == m_post_cli_attach.call_args_list

    @pytest.mark.parametrize(
        "api_side_effect,expected_err,expected_ret",
        [
            (fakes.FakeUbuntuProError(), "This is a test\n", 1),
            (
                exceptions.AlreadyAttachedError(account_name="foo"),
                "This machine is already attached to 'foo'\n"
                "To use a different subscription first run: sudo pro"
                " detach.\n",
                2,
            ),
            (
                api_exceptions.AutoAttachDisabledError,
                "features.disable_auto_attach set in config\n",
                1,
            ),
            (
                exceptions.EntitlementsNotEnabledError(
                    failed_services=[
                        ("esm-infra", messages.NamedMessage("test", "test")),
                        ("livepatch", messages.NamedMessage("test", "test")),
                    ]
                ),
                messages.E_ENTITLEMENTS_NOT_ENABLED_ERROR.msg + "\n",
                4,
            ),
        ],
    )
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch(M_PATH + "cli_util.post_cli_attach")
    @mock.patch(M_PATH + "_full_auto_attach")
    def test_uncaught_errors_are_handled(
        self,
        m_full_auto_attach,
        m_post_cli_attach,
        caplog_text,
        api_side_effect,
        expected_err,
        expected_ret,
        FakeConfig,
        capsys,
        event,
    ):
        m_full_auto_attach.side_effect = api_side_effect
        cfg = FakeConfig()
        with pytest.raises(SystemExit) as excinfo:
            main_error_handler(auto_attach_command.action)(
                mock.MagicMock(), cfg=cfg
            )
        assert expected_ret == excinfo.value.code
        _, err = capsys.readouterr()
        assert expected_err == err
        assert [] == m_post_cli_attach.call_args_list
