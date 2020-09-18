import io
import json
import os
import mock
import socket
import sys

import pytest

from uaclient import util

from uaclient.cli import action_status
from uaclient import status

M_PATH = "uaclient.cli."


RESPONSE_LIVEPATCH_AVAILABLE = [{"name": "livepatch", "available": True}]
UNATTACHED_STATUS = """\
SERVICE       AVAILABLE  DESCRIPTION
livepatch     yes        Canonical Livepatch service

This machine is not attached to a UA subscription.
See https://ubuntu.com/advantage
"""

ATTACHED_STATUS = """\
SERVICE       ENTITLED  STATUS    DESCRIPTION
cc-eal        no        {dash}         Common Criteria EAL2 Provisioning\
 Packages
cis-audit     no        {dash}         Center for Internet Security Audit Tools
esm-apps      no        {dash}         UA Apps: Extended Security Maintenance
esm-infra     no        {dash}         UA Infra: Extended Security Maintenance
fips          no        {dash}         NIST-certified FIPS modules
fips-updates  no        {dash}         Uncertified security updates to FIPS\
 modules
livepatch     no        {dash}         Canonical Livepatch service

Enable services with: ua enable <service>

                Account: test_account
           Subscription: test_contract
            Valid until: n/a
Technical support level: n/a
"""


@mock.patch(
    M_PATH + "contract.get_available_resources",
    return_value=RESPONSE_LIVEPATCH_AVAILABLE,
)
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionStatus:
    def test_attached(
        self, m_getuid, m_get_avail_resources, capsys, FakeConfig
    ):
        """Check that root and non-root will emit attached status"""
        cfg = FakeConfig.for_attached_machine()
        assert 0 == action_status(mock.MagicMock(), cfg)
        # capsys already converts colorized non-printable chars to space
        # Strip non-printables from output
        printable_stdout = capsys.readouterr()[0].replace(" " * 17, " " * 8)

        # On older versions of pytest, capsys doesn't set sys.stdout.encoding
        # to something that Python parses as UTF-8 compatible, so we get the
        # ASCII dash; testing for the "wrong" dash here is OK, because we have
        # a specific test that the correct one is used in
        # test_unicode_dash_replacement_when_unprintable
        expected_dash = "-"
        if sys.stdout.encoding and "UTF-8" in sys.stdout.encoding.upper():
            expected_dash = "\u2014"
        assert ATTACHED_STATUS.format(dash=expected_dash) == printable_stdout

    def test_unattached(
        self, m_getuid, m_get_avail_resources, capsys, FakeConfig
    ):
        """Check that unattached status is emitted to console"""
        cfg = FakeConfig()

        assert 0 == action_status(mock.MagicMock(), cfg)
        assert UNATTACHED_STATUS == capsys.readouterr()[0]

    @mock.patch(M_PATH + "util.should_reboot", return_value=False)
    def test_unattached_json(
        self,
        m_getuid,
        m_get_avail_resources,
        m_should_reboot,
        capsys,
        FakeConfig,
    ):
        """Check that unattached status json output is emitted to console"""
        cfg = FakeConfig()

        args = mock.MagicMock(format="json")
        assert 0 == action_status(args, cfg)

        expected = {
            "_doc": (
                "Content provided in json response is currently "
                "considered Experimental and may change"
            ),
            "configStatus": status.UserFacingConfigStatus.INACTIVE.value,
            "configStatusDetails": status.MESSAGE_NO_ACTIVE_OPERATIONS,
            "attached": False,
            "expires": "n/a",
            "origin": None,
            "services": [
                {
                    "name": "livepatch",
                    "description": "Canonical Livepatch service",
                    "available": "yes",
                }
            ],
            "techSupportLevel": "n/a",
        }
        assert expected == json.loads(capsys.readouterr()[0])

    def test_error_on_connectivity_errors(
        self, m_getuid, m_get_avail_resources, capsys, FakeConfig
    ):
        """Raise UrlError on connectivity issues"""
        m_get_avail_resources.side_effect = util.UrlError(
            socket.gaierror(-2, "Name or service not known")
        )

        cfg = FakeConfig()

        with pytest.raises(util.UrlError):
            action_status(mock.MagicMock(), cfg)

    @pytest.mark.parametrize(
        "encoding,expected_dash",
        (("utf-8", "\u2014"), ("UTF-8", "\u2014"), ("ascii", "-")),
    )
    def test_unicode_dash_replacement_when_unprintable(
        self,
        _m_getuid,
        _m_get_avail_resources,
        encoding,
        expected_dash,
        FakeConfig,
    ):
        # This test can't use capsys because it doesn't emulate sys.stdout
        # encoding accurately in older versions of pytest
        underlying_stdout = io.BytesIO()
        fake_stdout = io.TextIOWrapper(underlying_stdout, encoding=encoding)

        with mock.patch("sys.stdout", fake_stdout):
            action_status(mock.MagicMock(), FakeConfig.for_attached_machine())

        fake_stdout.flush()  # Make sure all output is in underlying_stdout
        out = underlying_stdout.getvalue().decode(encoding)

        # Colour codes are converted to spaces, so strip them out for
        # comparison
        out = out.replace(" " * 17, " " * 8)

        expected_out = ATTACHED_STATUS.format(dash=expected_dash)
        assert expected_out == out
