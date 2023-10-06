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
from uaclient.util import DatetimeAwareJSONEncoder

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: security-status \[-h\] \[--format {json,yaml,text}\]
                       \[--thirdparty \| --unavailable \| --esm-infra\ \| --esm-apps]

Show security updates for packages in the system, including all
available Expanded Security Maintenance \(ESM\) related content.

Shows counts of how many packages are supported for security updates
in the system.

If called with --format json\|yaml it shows a summary of the
installed packages based on the origin:
- main/restricted/universe/multiverse: packages from the Ubuntu archive
- esm-infra/esm-apps: packages from the ESM archive
- third-party: packages installed from non-Ubuntu sources
- unknown: packages which don't have an installation source \(like local
  deb packages or packages for which the source was removed\)

The output contains basic information about Ubuntu Pro. For a
complete status on Ubuntu Pro services, run 'pro status'.

(optional arguments|options):
  -h, --help            show this help message and exit
  --format {json,yaml,text}
                        output in the specified format \(default: text\)
  --thirdparty          List and present information about third-party
                        packages
  --unavailable         List and present information about unavailable
                        packages
  --esm-infra           List and present information about esm-infra packages
  --esm-apps            List and present information about esm-apps packages
"""  # noqa
)


@mock.patch(M_PATH + "security_status.security_status")
@mock.patch(M_PATH + "security_status.security_status_dict")
@mock.patch(M_PATH + "contract.get_available_resources")
class TestActionSecurityStatus:
    @mock.patch(M_PATH + "log.setup_cli_logging")
    def test_security_status_help(
        self,
        _m_setup_logging,
        _m_resources,
        _m_security_status_dict,
        _m_security_status,
        capsys,
        FakeConfig,
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

    @pytest.mark.parametrize("output_format", ("json", "yaml", "text"))
    @mock.patch(M_PATH + "safe_dump")
    @mock.patch(M_PATH + "json.dumps")
    def test_action_security_status(
        self,
        m_dumps,
        m_safe_dump,
        _m_resources,
        m_security_status_dict,
        m_security_status,
        output_format,
        FakeConfig,
    ):
        cfg = FakeConfig()
        args = mock.MagicMock()
        args.format = output_format
        args.thirdparty = False
        args.unavailable = False
        args.esm_infra = False
        args.esm_apps = False
        action_security_status(args, cfg=cfg)

        if output_format == "json":
            assert m_dumps.call_args_list == [
                mock.call(
                    m_security_status_dict.return_value,
                    sort_keys=True,
                    cls=DatetimeAwareJSONEncoder,
                ),
            ]
            assert m_safe_dump.call_count == 0
        elif output_format == "yaml":
            assert m_safe_dump.call_args_list == [
                mock.call(
                    m_security_status_dict.return_value,
                    default_flow_style=False,
                )
            ]
            assert m_dumps.call_count == 0
        else:
            assert m_dumps.call_count == 0
            assert m_safe_dump.call_count == 0
            assert m_security_status.call_args_list == [mock.call(cfg)]
            assert m_security_status.call_count == 1

    @mock.patch(M_PATH + "log.setup_cli_logging")
    def test_error_on_wrong_format(
        self,
        _m_setup_logging,
        _m_resources,
        _m_security_status_dict,
        _m_security_status,
        FakeConfig,
        capsys,
    ):
        cmdline_args = [
            "/usr/bin/ua",
            "security-status",
            "--format",
            "unsupported",
        ]

        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", cmdline_args):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()

        _, err = capsys.readouterr()

        assert "usage: security-status [-h] [--format {json,yaml,text}]" in err
        assert (
            "argument --format: invalid choice: 'unsupported'"
            " (choose from 'json', 'yaml', 'text')"
        ) in err


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
