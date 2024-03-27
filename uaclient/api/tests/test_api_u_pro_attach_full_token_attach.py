import mock
import pytest

from uaclient import exceptions, messages
from uaclient.api.data_types import ErrorWarningObject
from uaclient.api.u.pro.attach.token.full_token_attach.v1 import (
    FullTokenAttachResult,
    _full_token_attach,
)

M_PATH = "uaclient.api.u.pro.attach.token.full_token_attach.v1."


@mock.patch("uaclient.lock.RetryLock.__enter__")
class TestFullTokenAttach:
    @mock.patch("uaclient.util.we_are_currently_root")
    def test_full_token_attach_non_root_user(
        self, m_we_are_currently_root, _m_lock_enter
    ):
        m_we_are_currently_root.return_value = False

        with pytest.raises(exceptions.NonRootUserError):
            _full_token_attach(None, None)

    @mock.patch(M_PATH + "_is_attached")
    def test_full_token_attach_when_already_attached(
        self, m_is_attached, _m_lock_enter
    ):
        m_is_attached.return_value = mock.MagicMock(is_attached=True)
        assert FullTokenAttachResult(
            enabled=[], reboot_required=False
        ) == _full_token_attach(None, None)

    @pytest.mark.parametrize(
        "test_exception,expected_result,expected_warnings",
        (
            (
                exceptions.AttachFailureDefaultServices(
                    failed_services=[
                        ("ent1", messages.E_ATTACH_FAILURE_DEFAULT_SERVICES),
                        ("ent2", messages.E_ATTACH_FAILURE_DEFAULT_SERVICES),
                    ]
                ),
                FullTokenAttachResult(
                    enabled=["ent3"],
                    reboot_required=True,
                ),
                [
                    ErrorWarningObject(
                        title=messages.E_ATTACH_FAILURE_DEFAULT_SERVICES.msg,
                        code=messages.E_ATTACH_FAILURE_DEFAULT_SERVICES.name,
                        meta={"service": "ent1"},
                    ),
                    ErrorWarningObject(
                        title=messages.E_ATTACH_FAILURE_DEFAULT_SERVICES.msg,
                        code=messages.E_ATTACH_FAILURE_DEFAULT_SERVICES.name,
                        meta={"service": "ent2"},
                    ),
                ],
            ),
            (
                exceptions.AttachFailureUnknownError(
                    failed_services=[
                        (
                            "ent1",
                            messages.UNEXPECTED_ERROR.format(
                                error_msg="error",
                                log_path="path",
                            ),
                        )
                    ]
                ),
                FullTokenAttachResult(
                    enabled=["ent3"],
                    reboot_required=True,
                ),
                [
                    ErrorWarningObject(
                        title=messages.UNEXPECTED_ERROR.format(
                            error_msg="error",
                            log_path="path",
                        ).msg,
                        code=messages.UNEXPECTED_ERROR.name,
                        meta={"service": "ent1"},
                    ),
                ],
            ),
        ),
    )
    @mock.patch(M_PATH + "_is_attached")
    @mock.patch(M_PATH + "_enabled_services")
    @mock.patch(M_PATH + "_reboot_required")
    @mock.patch(M_PATH + "attach_with_token")
    def test_failed_services_during_attach(
        self,
        m_attach_with_token,
        m_reboot_required,
        m_enabled_services,
        m_is_attached,
        _m_lock_enter,
        test_exception,
        expected_result,
        expected_warnings,
    ):
        m_reboot_required.return_value = mock.MagicMock(reboot_required="yes")
        m_is_attached.return_value = mock.MagicMock(is_attached=False)
        m_ent = mock.MagicMock()
        type(m_ent).name = mock.PropertyMock(return_value="ent3")
        m_enabled_services.return_value = mock.MagicMock(
            enabled_services=[m_ent]
        )
        m_attach_with_token.side_effect = test_exception

        actual_result = _full_token_attach(
            options=mock.MagicMock(token="token", auto_enable_services=True),
            cfg=None,
        )

        assert expected_result == actual_result
        assert expected_warnings == actual_result.warnings
