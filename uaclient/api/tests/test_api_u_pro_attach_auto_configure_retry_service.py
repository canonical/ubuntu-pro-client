import mock
import pytest

from uaclient.api.u.pro.attach.auto.configure_retry_service.v1 import (
    ConfigureRetryServiceOptions,
    _configure_retry_service,
)
from uaclient.daemon import retry_auto_attach
from uaclient.files import state_files

M_PATH = "uaclient.api.u.pro.attach.auto.configure_retry_service.v1."


@mock.patch(M_PATH + "system.create_file")
@mock.patch(M_PATH + "state_files.retry_auto_attach_options_file.write")
class TestConfigureRetryServiceV1:
    @pytest.mark.parametrize(
        "options, expected_options_write_calls, expected_create_file_calls",
        [
            (
                ConfigureRetryServiceOptions(),
                [mock.call(state_files.RetryAutoAttachOptions())],
                [mock.call(retry_auto_attach.FLAG_FILE_PATH)],
            ),
            (
                ConfigureRetryServiceOptions(enable=["cis"]),
                [
                    mock.call(
                        state_files.RetryAutoAttachOptions(enable=["cis"])
                    )
                ],
                [mock.call(retry_auto_attach.FLAG_FILE_PATH)],
            ),
            (
                ConfigureRetryServiceOptions(
                    enable=["cis"], enable_beta=["esm-infra"]
                ),
                [
                    mock.call(
                        state_files.RetryAutoAttachOptions(
                            enable=["cis"], enable_beta=["esm-infra"]
                        )
                    )
                ],
                [mock.call(retry_auto_attach.FLAG_FILE_PATH)],
            ),
        ],
    )
    def test_configure_retry_service(
        self,
        m_options_write,
        m_create_file,
        options,
        expected_options_write_calls,
        expected_create_file_calls,
        FakeConfig,
    ):
        _configure_retry_service(options, FakeConfig())
        assert expected_options_write_calls == m_options_write.call_args_list
        assert expected_create_file_calls == m_create_file.call_args_list
