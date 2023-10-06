import re
import textwrap

import mock
import pytest

from uaclient import exceptions, messages
from uaclient.cli import action_api, api_parser, get_parser, main

HELP_OUTPUT = textwrap.dedent(
    """\
usage: api \[-h\] \[--args \[OPTIONS .*\]\] \[--data DATA\] endpoint

Calls the Client API endpoints.

positional arguments:
  endpoint              API endpoint to call

(optional arguments|options):
  -h, --help            show this help message and exit
  --args \[OPTIONS .*\](.|\n)*Options to pass to the API endpoint, formatted as(.|\n)*
                        key=value
  --data DATA           arguments in JSON format to the API endpoint
"""  # noqa
)


class TestActionAPI:
    @mock.patch("uaclient.cli.entitlements.valid_services", return_value=[])
    @mock.patch("uaclient.log.setup_cli_logging")
    def test_api_help(self, _m_setup_logging, valid_services, capsys):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "api", "--help"]):
                main()

        out, _err = capsys.readouterr()
        assert re.match(HELP_OUTPUT, out)

    @pytest.mark.parametrize(
        "result,expected_return", (("success", 0), ("failure", 1))
    )
    @mock.patch("uaclient.cli.call_api")
    def test_api_action(self, m_call_api, result, expected_return, FakeConfig):
        m_call_api.return_value.result = result
        args = mock.MagicMock()
        args.endpoint_path = "example_endpoint"
        args.options = []
        args.data = ""
        cfg = FakeConfig()
        return_code = action_api(args, cfg=cfg)
        assert m_call_api.call_count == 1
        assert m_call_api.call_args_list == [
            mock.call("example_endpoint", [], "", cfg)
        ]
        assert m_call_api.return_value.to_json.call_count == 1
        assert return_code == expected_return

    def test_api_error_out_if_options_and_data_are_provided(self):
        args = mock.MagicMock()
        args.endpoint_path = "example_endpoint"
        args.options = ["test=123"]
        args.data = '{"test": ["123"]}'

        with pytest.raises(exceptions.UbuntuProError) as e:
            action_api(args, cfg=mock.MagicMock())

        assert e.value.msg == messages.E_API_ERROR_ARGS_AND_DATA_TOGETHER.msg
        assert (
            e.value.msg_code
            == messages.E_API_ERROR_ARGS_AND_DATA_TOGETHER.name
        )


class TestParser:
    def test_security_status_parser_updates_parser_config(self, FakeConfig):
        """Update the parser configuration for 'api'."""
        m_parser = api_parser(mock.Mock())
        assert "api" == m_parser.prog

        full_parser = get_parser(FakeConfig())
        with mock.patch("sys.argv", ["pro", "api", "some.endpoint"]):
            args = full_parser.parse_args()
        assert "api" == args.command
        assert "action_api" == args.action.__name__
