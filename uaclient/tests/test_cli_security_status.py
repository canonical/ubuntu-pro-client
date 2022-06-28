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
usage: security-status \[-h\] --format {json,yaml}

Show security updates for packages in the system, including all
available ESM related content.

Besides the list of security updates, it also shows a summary of the
installed packages based on the origin.
- main/restricted/universe/multiverse: packages from the Ubuntu archive
- ESM Infra/Apps: packages from ESM
- third-party: packages installed from non-Ubuntu sources
- unknown: packages which don't have an installation source \(like local
  deb packages or packages for which the source was removed\)

The summary contains basic information about Ubuntu Pro and ESM. For a
complete status on Ubuntu Pro services, run 'pro status'

(optional arguments|options):
  -h, --help            show this help message and exit
  --format {json,yaml}  Format for the output \(json or yaml\)
"""  # noqa
)


@mock.patch("uaclient.api.u.pro.security.status.v1.status")
@mock.patch(M_PATH + "contract.get_available_resources")
class TestActionSecurityStatus:
    def test_security_status_help(
        self, _m_resources, _m_security_status, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch(
                "sys.argv", ["/usr/bin/ua", "security-status", "--help"]
            ):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()

        out, _err = capsys.readouterr()
        assert re.match(HELP_OUTPUT, out)

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
        m_security_status.return_value = mock.MagicMock()
        m_security_status.return_value.to_dict = lambda: {"test": "test"}

        expected_dict = {
            "test": "test",
            "deprecated": "Instead use `ua api u.pro.security.status.v2`",
        }

        action_security_status(args, cfg=cfg)

        if output_format == "json":
            assert m_dumps.call_args_list == [mock.call(expected_dict)]
            assert m_safe_dump.call_count == 0
        else:
            assert m_safe_dump.call_args_list == [
                mock.call(expected_dict, default_flow_style=False)
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
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
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
            "sys.argv", ["pro", "security-status", "--format", "json"]
        ):
            args = full_parser.parse_args()
        assert "security-status" == args.command
        assert "action_security_status" == args.action.__name__
