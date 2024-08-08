import mock
import pytest

from uaclient import exceptions, messages
from uaclient.cli.api import api_command

M_PATH = "uaclient.cli."


class TestActionAPI:
    @pytest.mark.parametrize(
        ["show_progress", "result", "expected_return"],
        ((True, "success", 0), (False, "failure", 1)),
    )
    @mock.patch(M_PATH + "api.call_api")
    def test_api_action(
        self, m_call_api, show_progress, result, expected_return, FakeConfig
    ):
        m_call_api.return_value.result = result
        args = mock.MagicMock()
        args.endpoint_path = "example_endpoint"
        args.options = []
        args.data = ""
        args.show_progress = show_progress
        cfg = FakeConfig()
        return_code = api_command.action(args, cfg=cfg)

        if show_progress:
            expected_progress = mock.ANY
        else:
            expected_progress = None
        assert m_call_api.call_count == 1
        assert m_call_api.call_args_list == [
            mock.call("example_endpoint", [], "", cfg, expected_progress)
        ]
        assert m_call_api.return_value.to_json.call_count == 1
        assert return_code == expected_return

    def test_api_error_out_if_options_and_data_are_provided(self):
        args = mock.MagicMock()
        args.endpoint_path = "example_endpoint"
        args.options = ["test=123"]
        args.data = '{"test": ["123"]}'

        with pytest.raises(exceptions.UbuntuProError) as e:
            api_command.action(args, cfg=mock.MagicMock())

        assert e.value.msg == messages.E_API_ERROR_ARGS_AND_DATA_TOGETHER.msg
        assert (
            e.value.msg_code
            == messages.E_API_ERROR_ARGS_AND_DATA_TOGETHER.name
        )
