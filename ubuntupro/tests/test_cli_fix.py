import textwrap

import mock
import pytest

from uaclient import exceptions
from uaclient.cli import action_fix, main
from uaclient.security import FixStatus

M_PATH = "uaclient.cli."

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro fix <CVE-yyyy-nnnn+>|<USN-nnnn-d+> [flags]

Inspect and resolve CVEs and USNs (Ubuntu Security Notices) on this machine.

positional arguments:
  security_issue  Security vulnerability ID to inspect and resolve on this
                  system. Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-
                  dd

Flags:
  -h, --help      show this help message and exit
  --dry-run       If used, fix will not actually run but will display
                  everything that will happen on the machine during the
                  command.
  --no-related    If used, when fixing a USN, the command will not try to also
                  fix related USNs to the target USN.
"""
)


class TestActionFix:
    @mock.patch("uaclient.cli.setup_logging")
    @mock.patch("uaclient.cli.contract.get_available_resources")
    def test_fix_help(
        self, _m_resources, _m_setup_logging, capsys, FakeConfig
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "fix", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
                    main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @pytest.mark.parametrize(
        "issue,is_valid",
        (
            ("CVE-2020-1234", True),
            ("cve-2020-12345", True),
            ("cve-1234-123456", True),
            ("CVE-2020-1234567", True),
            ("USN-1234-1", True),
            ("usn-1234-12", True),
            ("USN-12345-1", True),
            ("usn-12345-12", True),
            ("lsn-1234-1", True),
            ("LSN-1234-12", True),
            ("LSN-1234-123", False),
            ("cve-1234-123", False),
            ("CVE-1234-12345678", False),
            ("USA-1234-12345678", False),
        ),
    )
    @mock.patch("uaclient.security.fix_security_issue_id")
    def test_attached(
        self, m_fix_security_issue_id, issue, is_valid, FakeConfig
    ):
        """Check that root and non-root will emit attached status"""
        cfg = FakeConfig()
        args = mock.MagicMock(
            security_issue=issue, dry_run=False, no_related=False
        )
        m_fix_security_issue_id.return_value = FixStatus.SYSTEM_NON_VULNERABLE
        if is_valid:
            assert 0 == action_fix(args, cfg=cfg)
            assert [
                mock.call(
                    cfg=cfg, issue_id=issue, dry_run=False, no_related=False
                )
            ] == m_fix_security_issue_id.call_args_list
        else:
            with pytest.raises(exceptions.UserFacingError) as excinfo:
                action_fix(args, cfg=cfg)

            expected_msg = (
                'Error: issue "{}" is not recognized.\n'
                'Usage: "pro fix CVE-yyyy-nnnn" or "pro fix USN-nnnn"'
            ).format(issue)

            assert expected_msg == str(excinfo.value)
            assert 0 == m_fix_security_issue_id.call_count
