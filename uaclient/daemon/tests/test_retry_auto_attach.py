from urllib import error

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import (
    FullAutoAttachOptions,
)
from uaclient.daemon import AUTO_ATTACH_STATUS_MOTD_FILE
from uaclient.daemon.retry_auto_attach import (
    full_auto_attach_exception_to_failure_reason,
    retry_auto_attach,
)
from uaclient.files import state_files
from uaclient.testing import fakes

M_PATH = "uaclient.daemon.retry_auto_attach."


class TestFullAutoAttachToFailureReason:
    @pytest.mark.parametrize(
        "e, expected_reason",
        [
            (
                exceptions.InvalidProImage(error_msg="invalid pro"),
                'Canonical servers did not recognize this machine as Ubuntu Pro: "invalid pro"',  # noqa: E501
            ),
            (
                exceptions.NonAutoAttachImageError(cloud_type="msg"),
                "Canonical servers did not recognize this image as Ubuntu Pro",
            ),
            (
                exceptions.LockHeldError(
                    lock_request="request", lock_holder="holder", pid=123
                ),
                "the pro lock was held by pid 123",
            ),
            (
                exceptions.ContractAPIError(
                    url="url", code=123, body="response"
                ),
                'an error from Canonical servers: "response"',
            ),
            (
                exceptions.ConnectivityError(),
                "a connectivity error",
            ),
            (
                exceptions.UrlError(error.URLError("urlerror"), "url"),
                'an error while reaching url: "urlerror"',
            ),
            (fakes.FakeUserFacingError(), '"This is a test"'),
            (Exception("hello"), "hello"),
            (Exception(), "an unknown error"),
        ],
    )
    def test(self, e, expected_reason):
        assert expected_reason == full_auto_attach_exception_to_failure_reason(
            e
        )


@mock.patch(M_PATH + "cleanup")
@mock.patch(M_PATH + "full_auto_attach")
@mock.patch(M_PATH + "state_files.retry_auto_attach_options_file.read")
@mock.patch(M_PATH + "time.sleep")
@mock.patch(M_PATH + "system.write_file")
@mock.patch(M_PATH + "state_files.retry_auto_attach_state_file.write")
@mock.patch(M_PATH + "state_files.retry_auto_attach_state_file.read")
class TestRetryAutoAttach:
    @pytest.mark.parametrize(
        "is_attached, expected_state_read_calls",
        [
            (False, [mock.call()]),
            (True, []),
        ],
    )
    def test_early_return_when_attached(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        is_attached,
        expected_state_read_calls,
        FakeConfig,
    ):
        if is_attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()
        retry_auto_attach(cfg)
        assert expected_state_read_calls == m_state_read.call_args_list

    def test_early_return_when_attached_during_sleep(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        FakeConfig,
    ):
        with mock.patch(
            "uaclient.daemon.retry_auto_attach._is_attached",
            new_callable=mock.PropertyMock,
            side_effect=[
                mock.MagicMock(is_attached=False),
                mock.MagicMock(is_attached=True),
                mock.MagicMock(is_attached=True),
            ],
        ):
            cfg = FakeConfig()
            retry_auto_attach(cfg)
            assert [mock.call(900)] == m_sleep.call_args_list

    @pytest.mark.parametrize(
        "state_read_content, expected_state_write_calls",
        [
            (
                None,
                [
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=0, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=1, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=2, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=3, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=4, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=5, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=6, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=7, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=8, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=9, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=10, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=11, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=12, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=13, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=14, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=15, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=16, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=17, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=18, failure_reason=mock.ANY
                        )
                    ),
                ],
            ),
            (
                state_files.RetryAutoAttachState(
                    interval_index=0, failure_reason=None
                ),
                [
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=0, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=1, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=2, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=3, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=4, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=5, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=6, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=7, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=8, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=9, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=10, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=11, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=12, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=13, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=14, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=15, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=16, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=17, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=18, failure_reason=mock.ANY
                        )
                    ),
                ],
            ),
            (
                state_files.RetryAutoAttachState(
                    interval_index=1, failure_reason=None
                ),
                [
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=1, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=2, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=3, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=4, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=5, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=6, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=7, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=8, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=9, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=10, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=11, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=12, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=13, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=14, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=15, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=16, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=17, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=18, failure_reason=mock.ANY
                        )
                    ),
                ],
            ),
            (
                state_files.RetryAutoAttachState(
                    interval_index=12, failure_reason=None
                ),
                [
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=12, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=13, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=14, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=15, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=16, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=17, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=18, failure_reason=mock.ANY
                        )
                    ),
                ],
            ),
            (
                state_files.RetryAutoAttachState(
                    interval_index=17, failure_reason=None
                ),
                [
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=17, failure_reason=mock.ANY
                        )
                    ),
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=18, failure_reason=mock.ANY
                        )
                    ),
                ],
            ),
            (
                state_files.RetryAutoAttachState(
                    interval_index=18, failure_reason=None
                ),
                [
                    mock.call(
                        state_files.RetryAutoAttachState(
                            interval_index=18, failure_reason=mock.ANY
                        )
                    ),
                ],
            ),
        ],
    )
    def test_state_file_is_used_and_updated(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        state_read_content,
        expected_state_write_calls,
        FakeConfig,
    ):
        # we want to test all state writes, so auto-attach can never succeed
        m_full_auto_attach.side_effect = Exception()
        m_state_read.return_value = state_read_content
        cfg = FakeConfig()
        retry_auto_attach(cfg)
        assert expected_state_write_calls == m_state_write.call_args_list

    def test_already_attached_error_ends_early(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        FakeConfig,
    ):
        cfg = FakeConfig()
        m_full_auto_attach.side_effect = exceptions.AlreadyAttachedError(
            account_name="test_account"
        )
        retry_auto_attach(cfg)
        assert [mock.call(mock.ANY)] == m_full_auto_attach.call_args_list

    @pytest.mark.parametrize(
        "full_auto_attach_side_effect," "expected_full_auto_attach_calls",
        [
            (
                [
                    Exception(),
                    None,
                ],
                [
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                ],
            ),
            (
                [
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    None,
                ],
                [
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                ],
            ),
            (
                [
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                    Exception(),
                ],
                [
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                ],
            ),
        ],
    )
    def test_multiple_attempts_on_errors_with_limit(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        full_auto_attach_side_effect,
        expected_full_auto_attach_calls,
        FakeConfig,
    ):
        m_full_auto_attach.side_effect = full_auto_attach_side_effect
        cfg = FakeConfig()
        retry_auto_attach(cfg)
        assert (
            expected_full_auto_attach_calls
            == m_full_auto_attach.call_args_list
        )

    @pytest.mark.parametrize(
        "is_attached_at_end, expected_cleanup_calls, expected_write_file_call",
        [
            (True, [mock.call(mock.ANY)], None),
            (
                False,
                [mock.call(mock.ANY)],
                mock.call(
                    AUTO_ATTACH_STATUS_MOTD_FILE,
                    "\n"
                    + messages.AUTO_ATTACH_RETRY_TOTAL_FAILURE_NOTICE.format(
                        num_attempts=19, reason="an unknown error"
                    )
                    + "\n\n",
                ),
            ),
        ],
    )
    def test_cleanup_and_total_fail_message(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        is_attached_at_end,
        expected_cleanup_calls,
        expected_write_file_call,
        FakeConfig,
    ):
        # skip all the attempts
        m_state_read.return_value = state_files.RetryAutoAttachState(
            interval_index=18, failure_reason=None
        )
        with mock.patch(
            "uaclient.daemon.retry_auto_attach._is_attached",
            new_callable=mock.PropertyMock,
            side_effect=[
                mock.MagicMock(is_attached=False),
                mock.MagicMock(is_attached=is_attached_at_end),
            ],
        ):
            cfg = FakeConfig()
            retry_auto_attach(cfg)
            assert expected_cleanup_calls == m_cleanup.call_args_list
            if expected_write_file_call:
                assert expected_write_file_call in m_write_file.call_args_list

    @pytest.mark.parametrize(
        [
            "option_file_contents",
            "expected_full_auto_attach_calls",
        ],
        [
            (None, [mock.call(FullAutoAttachOptions())]),
            (
                state_files.RetryAutoAttachOptions(),
                [mock.call(FullAutoAttachOptions())],
            ),
            (
                state_files.RetryAutoAttachOptions(enable=["one"]),
                [mock.call(FullAutoAttachOptions(enable=["one"]))],
            ),
            (
                state_files.RetryAutoAttachOptions(
                    enable=["one"], enable_beta=["two"]
                ),
                [
                    mock.call(
                        FullAutoAttachOptions(
                            enable=["one"], enable_beta=["two"]
                        )
                    )
                ],
            ),
        ],
    )
    def test_uses_options_file(
        self,
        m_state_read,
        m_state_write,
        m_write_file,
        m_sleep,
        m_options_read,
        m_full_auto_attach,
        m_cleanup,
        option_file_contents,
        expected_full_auto_attach_calls,
        FakeConfig,
    ):
        m_options_read.return_value = option_file_contents
        cfg = FakeConfig()
        retry_auto_attach(cfg)
        assert (
            expected_full_auto_attach_calls
            == m_full_auto_attach.call_args_list
        )
