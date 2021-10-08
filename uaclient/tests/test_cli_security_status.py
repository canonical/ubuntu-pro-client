import textwrap

import mock
import pytest

from uaclient.cli import (
    action_security_status,
    get_parser,
    main,
    security_status_parser,
)

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: security-status [-h] --format {json,yaml}

Show security updates for packages in the system, including all available ESM
related content.

optional arguments:
  -h, --help            show this help message and exit
  --format {json,yaml}  Format for the output (json or yaml)
"""
)


class TestActionSecurityStatus:
    def test_security_status_help(self, capsys):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "security-status", "--help"]
            ):
                main()

        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @pytest.mark.parametrize("output_format", ("json", "yaml"))
    @mock.patch(M_PATH + "security_status.security_status")
    @mock.patch(M_PATH + "yaml.safe_dump")
    @mock.patch(M_PATH + "json.dumps")
    def test_action_security_status(
        self,
        m_dumps,
        m_safe_dump,
        m_security_status,
        output_format,
        FakeConfig,
    ):
        cfg = FakeConfig()
        args = mock.MagicMock()
        args.format = output_format
        action_security_status(args, cfg=cfg)

        if output_format == "json":
            assert m_dumps.call_args_list == [
                mock.call(m_security_status.return_value)
            ]
            assert m_safe_dump.call_count == 0
        else:
            assert m_safe_dump.call_args_list == [
                mock.call(
                    m_security_status.return_value, default_flow_style=False
                )
            ]
            assert m_dumps.call_count == 0

    # Remove this once we have human-readable text
    @pytest.mark.parametrize("with_wrong_format", (False, True))
    def test_require_format_flag(self, with_wrong_format, FakeConfig, capsys):
        cmdline_args = ["/usr/bin/ua", "security-status"]
        if with_wrong_format:
            cmdline_args.extend(["--format", "unsupported"])

        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", cmdline_args):
                main()

        _, err = capsys.readouterr()

        assert "usage: security-status [-h] --format {json,yaml}" in err

        if with_wrong_format:
            assert (
                "argument --format: invalid choice: 'unsupported'"
                " (choose from 'json', 'yaml')"
            ) in err
        else:
            assert "the following arguments are required: --format" in err


class TestParser:
    def test_security_status_parser_updates_parser_config(self):
        """Update the parser configuration for 'security-status'."""
        m_parser = security_status_parser(mock.Mock())
        assert "security-status" == m_parser.prog

        full_parser = get_parser()
        with mock.patch(
            "sys.argv", ["ua", "security-status", "--format", "json"]
        ):
            args = full_parser.parse_args()
        assert "security-status" == args.command
        assert "action_security_status" == args.action.__name__
