import io
import json
import mock
import socket

import pytest

from uaclient.testing.fakes import FakeConfig
from uaclient import util

from uaclient.cli import action_status

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
cc-eal        no        —         Common Criteria EAL2 Provisioning Packages
cis-audit     no        —         Center for Internet Security Audit Tools
esm-infra     no        —         UA Infra: Extended Security Maintenance
fips          no        —         NIST-certified FIPS modules
fips-updates  no        —         Uncertified security updates to FIPS modules
livepatch     no        —         Canonical Livepatch service

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
    def test_attached(self, m_getuid, m_get_avail_resources, capsys):
        """Check that root and non-root will emit attached status"""
        cfg = FakeConfig.for_attached_machine()
        assert 0 == action_status(mock.MagicMock(), cfg)
        # capsys already converts colorized non-printable chars to space
        # Strip non-printables from output
        printable_stdout = capsys.readouterr()[0].replace(" " * 17, " " * 8)
        assert ATTACHED_STATUS == printable_stdout

    def test_unattached(self, m_getuid, m_get_avail_resources, capsys):
        """Check that unattached status is emitted to console"""
        cfg = FakeConfig()

        assert 0 == action_status(mock.MagicMock(), cfg)
        assert UNATTACHED_STATUS == capsys.readouterr()[0]

    def test_unattached_json(self, m_getuid, m_get_avail_resources, capsys):
        """Check that unattached status json output is emitted to console"""
        cfg = FakeConfig()

        args = mock.MagicMock(format="json")
        assert 0 == action_status(args, cfg)
        expected = {
            "_doc": (
                "Content provided in json response is currently "
                "considered Experimental and may change"
            ),
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
        self, m_getuid, m_get_avail_resources, capsys
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
        self, _m_getuid, _m_get_avail_resources, encoding, expected_dash
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

        expected_out = ATTACHED_STATUS.replace("\u2014", expected_dash)
        assert expected_out == out
