import mock

import pytest

from uaclient import exceptions

from uaclient.cli import action_fix

M_PATH = "uaclient.cli."


class TestActionFix:
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
        args = mock.MagicMock(security_issue=issue)
        if is_valid:
            assert 0 == action_fix(args, cfg)
            assert [
                mock.call(cfg, issue)
            ] == m_fix_security_issue_id.call_args_list
        else:
            with pytest.raises(exceptions.UserFacingError) as excinfo:
                action_fix(args, cfg)
            assert "Invalid issue format: {}".format(issue) == str(
                excinfo.value
            )
            assert 0 == m_fix_security_issue_id.call_count
