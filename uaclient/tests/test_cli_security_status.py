import re
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
usage: security-status \[-h\] --format {json,yaml} \[--version {0.1,0.2}\]

Show security updates for packages in the system, including all
available ESM related content.

Besides the list of security updates, it also shows a summary of the
installed packages based on the origin.
- main/restricted/universe/multiverse: packages from the Ubuntu archive
- ESM Infra/Apps: packages from ESM
- third-party: packages installed from non-Ubuntu sources
- unknown: packages which don't have an installation source \(like local
  deb packages or packages for which the source was removed\)

The summary contains basic information about UA and ESM. For a complete
status on UA services, run 'ua status'

(optional arguments|options):
  -h, --help            show this help message and exit
  --format {json,yaml}  Format for the output \(json or yaml\)
  --version {0.1,0.2}   Version of the output data
"""  # noqa
)


@mock.patch(M_PATH + "security_status.security_status")
@mock.patch(M_PATH + "contract.get_available_resources")
class TestActionSecurityStatus:
    def test_security_status_help(
        self, _m_resources, _m_security_status, capsys
    ):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "security-status", "--help"]
            ):
                main()

        out, _err = capsys.readouterr()
        assert re.match(HELP_OUTPUT, out)

    @pytest.mark.parametrize("version", (None, 0.1, 0.2))
    @mock.patch(M_PATH + "yaml.safe_dump")
    @mock.patch(M_PATH + "json.dumps")
    def test_version_flag_is_passed(
        self,
        _m_json,
        _m_yaml,
        _m_resources,
        m_security_status,
        version,
        FakeConfig,
    ):
        cfg = FakeConfig()
        args = mock.MagicMock()
        args.version = version

        action_security_status(args, cfg=cfg)

        assert m_security_status.call_args_list == [mock.call(cfg, version)]

    @pytest.mark.parametrize("output_format", ("json", "yaml"))
    @mock.patch(M_PATH + "yaml.safe_dump")
    @mock.patch(M_PATH + "json.dumps")
    def test_action_security_status(
        self,
        m_dumps,
        m_safe_dump,
        _m_resources,
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
    def test_require_format_flag(
        self,
        _m_resources,
        _m_security_status,
        with_wrong_format,
        FakeConfig,
        capsys,
    ):
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
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_security_status_parser_updates_parser_config(
        self, _m_resources, FakeConfig
    ):
        """Update the parser configuration for 'security-status'."""
        m_parser = security_status_parser(mock.Mock())
        assert "security-status" == m_parser.prog

        full_parser = get_parser(FakeConfig())
        with mock.patch(
            "sys.argv", ["ua", "security-status", "--format", "json"]
        ):
            args = full_parser.parse_args()
        assert "security-status" == args.command
        assert "json" == args.format
        assert "action_security_status" == args.action.__name__
        # Default version should be 0.1 for compatibility reasons
        assert "0.1" == args.version
