import datetime
import io
import json
import os
import socket
import sys
import textwrap

import mock
import pytest
import yaml

from uaclient import status, util, version
from uaclient.cli import action_status, main

M_PATH = "uaclient.cli."


RESPONSE_AVAILABLE_SERVICES = [
    {"name": "livepatch", "available": True},
    {"name": "fips", "available": False},
]
UNATTACHED_STATUS = """\
SERVICE       AVAILABLE  DESCRIPTION
fips          no         NIST-certified core packages
livepatch     yes        Canonical Livepatch service

This machine is not attached to a UA subscription.
See https://ubuntu.com/advantage
"""

# TODO-ROS add the following lines to ATTACHED_STATUS below livepatch
# ros           no        {dash}         Security Updates for the Robot\
#  Operating System
# ros-updates   no        {dash}         All Updates for the Robot Operating\
#  System
ATTACHED_STATUS = """\
SERVICE       ENTITLED  STATUS    DESCRIPTION
cc-eal        no        {dash}         Common Criteria EAL2 Provisioning\
 Packages
cis           no        {dash}         Center for Internet Security Audit Tools
esm-apps      no        {dash}         UA Apps: Extended Security Maintenance\
 (ESM)
esm-infra     no        {dash}         UA Infra: Extended Security Maintenance\
 (ESM)
fips          no        {dash}         NIST-certified core packages
fips-updates  no        {dash}         NIST-certified core packages with\
 priority security updates
livepatch     no        {dash}         Canonical Livepatch service
{notices}
Enable services with: ua enable <service>

                Account: test_account
           Subscription: test_contract
            Valid until: 2040-05-08 19:02:26+00:00
Technical support level: n/a
"""

# Omit beta services from status
ATTACHED_STATUS_NOBETA = """\
SERVICE       ENTITLED  STATUS    DESCRIPTION
cis           no        {dash}         Center for Internet Security Audit Tools
esm-infra     no        {dash}         UA Infra: Extended Security Maintenance\
 (ESM)
fips          no        {dash}         NIST-certified core packages
fips-updates  no        {dash}         NIST-certified core packages with\
 priority security updates
livepatch     no        {dash}         Canonical Livepatch service
{notices}
Enable services with: ua enable <service>

                Account: test_account
           Subscription: test_contract
            Valid until: 2040-05-08 19:02:26+00:00
Technical support level: n/a
"""

# TODO-ROS add "ros" and "ros-updates" to BETA_SVC_NAMES
BETA_SVC_NAMES = ["cc-eal", "esm-apps"]

SERVICES_JSON_ALL = [
    {
        "description": "Common Criteria EAL2 Provisioning Packages",
        "description_override": None,
        "entitled": "no",
        "name": "cc-eal",
        "status": "—",
        "status_details": "",
        "available": "yes",
    },
    {
        "description": "Center for Internet Security Audit Tools",
        "description_override": None,
        "entitled": "no",
        "name": "cis",
        "status": "—",
        "status_details": "",
        "available": "yes",
    },
    {
        "description": "UA Apps: Extended Security Maintenance (ESM)",
        "description_override": None,
        "entitled": "no",
        "name": "esm-apps",
        "status": "—",
        "status_details": "",
        "available": "yes",
    },
    {
        "description": "UA Infra: Extended Security Maintenance (ESM)",
        "description_override": None,
        "entitled": "no",
        "name": "esm-infra",
        "status": "—",
        "status_details": "",
        "available": "yes",
    },
    {
        "description": "NIST-certified core packages",
        "description_override": None,
        "entitled": "no",
        "name": "fips",
        "status": "—",
        "status_details": "",
        "available": "no",
    },
    {
        "description": (
            "NIST-certified core packages with priority security updates"
        ),
        "description_override": None,
        "entitled": "no",
        "name": "fips-updates",
        "status": "—",
        "status_details": "",
        "available": "yes",
    },
    {
        "description": "Canonical Livepatch service",
        "description_override": None,
        "entitled": "no",
        "name": "livepatch",
        "status": "—",
        "status_details": "",
        "available": "yes",
    },
    # TODO-ROS uncomment these
    # {
    #     "description": "Security Updates for the Robot Operating System",
    #     "description_override": None,
    #     "entitled": "no",
    #     "name": "ros",
    #     "status": "—",
    #     "status_details": "",
    #     "available": "yes",
    # },
    # {
    #     "description": "All Updates for the Robot Operating System",
    #     "description_override": None,
    #     "entitled": "no",
    #     "name": "ros-updates",
    #     "status": "—",
    #     "status_details": "",
    #     "available": "yes",
    # },
]

HELP_OUTPUT = textwrap.dedent(
    """\
usage: ua status [flags]

Report current status of Ubuntu Advantage services on system.

This shows whether this machine is attached to an Ubuntu Advantage
support contract. When attached, the report includes the specific
support contract details including contract name, expiry dates, and the
status of each service on this system.

The attached status output has four columns:

* SERVICE: name of the service
* ENTITLED: whether the contract to which this machine is attached
  entitles use of this service. Possible values are: yes or no
* STATUS: whether the service is enabled on this machine. Possible
  values are: enabled, disabled, n/a (if your contract entitles
  you to the service, but it isn't available for this machine) or — (if
  you aren't entitled to this service)
* DESCRIPTION: a brief description of the service

The unattached status output instead has three columns. SERVICE
and DESCRIPTION are the same as above, and there is the addition
of:

* AVAILABLE: whether this service would be available if this machine
  were attached. The possible values are yes or no.

Flags:
  -h, --help            show this help message and exit
  --wait                Block waiting on ua to complete
  --format {tabular,json,yaml}
                        output status in the specified format (default:
                        tabular)
  --all                 Allow the visualization of beta services
"""
)


@mock.patch("uaclient.util.should_reboot", return_value=False)
@mock.patch("uaclient.config.UAConfig.remove_notice")
@mock.patch(
    M_PATH + "contract.get_available_resources",
    return_value=RESPONSE_AVAILABLE_SERVICES,
)
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionStatus:
    def test_status_help(
        self,
        _getuid,
        _get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        capsys,
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "status", "--help"]):
                main()
        out, _err = capsys.readouterr()
        assert HELP_OUTPUT == out

    @pytest.mark.parametrize("use_all", (True, False))
    @pytest.mark.parametrize(
        "notices,notice_status",
        (
            ([], ""),
            (
                [["a", "adesc"], ["b2", "bdesc"]],
                "\nNOTICES\n a: adesc\nb2: bdesc\n",
            ),
        ),
    )
    def test_attached(
        self,
        m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        notices,
        notice_status,
        use_all,
        capsys,
        FakeConfig,
    ):
        """Check that root and non-root will emit attached status"""
        cfg = FakeConfig.for_attached_machine()
        cfg.write_cache("notices", notices)
        assert 0 == action_status(mock.MagicMock(all=use_all), cfg=cfg)
        # capsys already converts colorized non-printable chars to space
        # Strip non-printables from output
        printable_stdout = capsys.readouterr()[0].replace(" " * 17, " " * 8)

        # On older versions of pytest, capsys doesn't set sys.stdout.encoding
        # to something that Python parses as UTF-8 compatible, so we get the
        # ASCII dash; testing for the "wrong" dash here is OK, because we have
        # a specific test that the correct one is used in
        # test_unicode_dash_replacement_when_unprintable
        expected_dash = "-"
        status_tmpl = ATTACHED_STATUS if use_all else ATTACHED_STATUS_NOBETA

        if sys.stdout.encoding and "UTF-8" in sys.stdout.encoding.upper():
            expected_dash = "\u2014"
        assert (
            status_tmpl.format(dash=expected_dash, notices=notice_status)
            == printable_stdout
        )

    def test_unattached(
        self,
        m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        capsys,
        FakeConfig,
    ):
        """Check that unattached status is emitted to console"""
        cfg = FakeConfig()

        assert 0 == action_status(mock.MagicMock(all=False), cfg=cfg)
        assert UNATTACHED_STATUS == capsys.readouterr()[0]

    @mock.patch("uaclient.version.get_version", return_value="test_version")
    @mock.patch("uaclient.util.subp")
    @mock.patch(M_PATH + "time.sleep")
    def test_wait_blocks_until_lock_released(
        self,
        m_sleep,
        m_subp,
        _m_get_version,
        m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        capsys,
        FakeConfig,
    ):
        """Check that --wait will will block and poll until lock released."""
        cfg = FakeConfig()
        lock_file = cfg.data_path("lock")
        cfg.write_cache("lock", "123:ua auto-attach")

        def fake_sleep(seconds):
            if m_sleep.call_count == 3:
                os.unlink(lock_file)

        m_sleep.side_effect = fake_sleep

        assert 0 == action_status(mock.MagicMock(all=False), cfg=cfg)
        assert [mock.call(1)] * 3 == m_sleep.call_args_list
        assert "...\n" + UNATTACHED_STATUS == capsys.readouterr()[0]

    @pytest.mark.parametrize("format_type", (("json"), ("yaml")))
    @pytest.mark.parametrize(
        "environ",
        (
            {},
            {
                "UA_DATA_DIR": "data_dir",
                "UA_TEST": "test",
                "UA_FEATURES_ALLOW_BETA": True,
                "UA_CONFIG_FILE": "config_file",
            },
        ),
    )
    @pytest.mark.parametrize("use_all", (True, False))
    def test_unattached_formats(
        self,
        m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        use_all,
        environ,
        format_type,
        capsys,
        FakeConfig,
    ):
        """Check that unattached status json output is emitted to console"""
        cfg = FakeConfig()

        args = mock.MagicMock(format=format_type, all=use_all)
        with mock.patch.object(os, "environ", environ):
            assert 0 == action_status(args, cfg=cfg)

        expected_environment = []
        if environ:
            expected_environment = [
                {"name": "UA_CONFIG_FILE", "value": "config_file"},
                {"name": "UA_DATA_DIR", "value": "data_dir"},
                {"name": "UA_FEATURES_ALLOW_BETA", "value": True},
            ]

        expected = {
            "_doc": (
                "Content provided in json response is currently "
                "considered Experimental and may change"
            ),
            "_schema_version": "0.1",
            "version": version.get_version(features=cfg.features),
            "execution_status": status.UserFacingConfigStatus.INACTIVE.value,
            "execution_details": status.MESSAGE_NO_ACTIVE_OPERATIONS,
            "attached": False,
            "machine_id": None,
            "effective": None,
            "expires": None,
            "notices": [],
            "services": [
                {
                    "name": "livepatch",
                    "description": "Canonical Livepatch service",
                    "available": "yes",
                }
            ],
            "environment_vars": expected_environment,
            "contract": {
                "id": "",
                "name": "",
                "created_at": "",
                "products": [],
                "tech_support_level": "n/a",
            },
            "account": {
                "name": "",
                "id": "",
                "created_at": "",
                "external_account_ids": [],
            },
            "config_path": None,
            "config": {"data_dir": mock.ANY},
        }

        if format_type == "json":
            assert expected == json.loads(capsys.readouterr()[0])
        else:
            assert expected == yaml.safe_load(capsys.readouterr()[0])

    @pytest.mark.parametrize("format_type", (("json"), ("yaml")))
    @pytest.mark.parametrize(
        "environ",
        (
            {},
            {
                "UA_DATA_DIR": "data_dir",
                "UA_TEST": "test",
                "UA_FEATURES_ALLOW_BETA": True,
                "UA_CONFIG_FILE": "config_file",
            },
        ),
    )
    @pytest.mark.parametrize("use_all", (True, False))
    def test_attached_formats(
        self,
        m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        use_all,
        environ,
        format_type,
        capsys,
        FakeConfig,
    ):
        """Check that unattached status json output is emitted to console"""
        cfg = FakeConfig.for_attached_machine()

        args = mock.MagicMock(format=format_type, all=use_all)

        with mock.patch.object(os, "environ", environ):
            assert 0 == action_status(args, cfg=cfg)

        expected_environment = []
        if environ:
            expected_environment = [
                {"name": "UA_CONFIG_FILE", "value": "config_file"},
                {"name": "UA_DATA_DIR", "value": "data_dir"},
                {"name": "UA_FEATURES_ALLOW_BETA", "value": True},
            ]

        if use_all:
            services = SERVICES_JSON_ALL
        else:
            services = [
                svc
                for svc in SERVICES_JSON_ALL
                if svc["name"] not in BETA_SVC_NAMES
            ]

        inapplicable_services = [
            service["name"]
            for service in RESPONSE_AVAILABLE_SERVICES
            if not service["available"]
        ]

        filtered_services = [
            service
            for service in services
            if service["name"] not in inapplicable_services
        ]

        if format_type == "json":
            contract_created_at = "2020-05-08T19:02:26+00:00"
            account_created_at = "2019-06-14T06:45:50+00:00"
            expires = "2040-05-08T19:02:26+00:00"
            effective = "2000-05-08T19:02:26+00:00"
        else:
            contract_created_at = datetime.datetime(
                2020, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
            )
            account_created_at = datetime.datetime(
                2019, 6, 14, 6, 45, 50, tzinfo=datetime.timezone.utc
            )
            expires = datetime.datetime(
                2040, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
            )
            effective = datetime.datetime(
                2000, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
            )

        tech_support_level = status.UserFacingStatus.INAPPLICABLE.value
        expected = {
            "_doc": (
                "Content provided in json response is currently "
                "considered Experimental and may change"
            ),
            "_schema_version": "0.1",
            "version": version.get_version(features=cfg.features),
            "execution_status": status.UserFacingConfigStatus.INACTIVE.value,
            "execution_details": status.MESSAGE_NO_ACTIVE_OPERATIONS,
            "attached": True,
            "machine_id": "test_machine_id",
            "effective": effective,
            "expires": expires,
            "notices": [],
            "services": filtered_services,
            "environment_vars": expected_environment,
            "contract": {
                "id": "cid",
                "name": "test_contract",
                "created_at": contract_created_at,
                "products": ["free"],
                "tech_support_level": tech_support_level,
            },
            "account": {
                "id": "acct-1",
                "name": "test_account",
                "created_at": account_created_at,
                "external_account_ids": [{"IDs": ["id1"], "Origin": "AWS"}],
            },
            "config_path": None,
            "config": {"data_dir": mock.ANY},
        }

        if format_type == "json":
            assert expected == json.loads(capsys.readouterr()[0])
        else:
            yaml_output = yaml.safe_load(capsys.readouterr()[0])

            # On earlier versions of pyyaml, we don't add the timezone
            # info when converting a date string into a datetime object.
            # Since we only want to test if we are producing a valid
            # yaml file in the status output, we can manually add
            # the timezone info to make the test work as expected
            for key, value in yaml_output.items():
                if isinstance(value, datetime.datetime):
                    yaml_output[key] = value.replace(
                        tzinfo=datetime.timezone.utc
                    )

                elif isinstance(value, dict):
                    for inner_key, inner_value in value.items():
                        if isinstance(inner_value, datetime.datetime):
                            yaml_output[key][inner_key] = inner_value.replace(
                                tzinfo=datetime.timezone.utc
                            )

            assert expected == yaml_output

    def test_error_on_connectivity_errors(
        self,
        m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        capsys,
        FakeConfig,
    ):
        """Raise UrlError on connectivity issues"""
        m_get_avail_resources.side_effect = util.UrlError(
            socket.gaierror(-2, "Name or service not known")
        )

        cfg = FakeConfig()

        with pytest.raises(util.UrlError):
            action_status(mock.MagicMock(all=False), cfg=cfg)

    @pytest.mark.parametrize(
        "encoding,expected_dash",
        (("utf-8", "\u2014"), ("UTF-8", "\u2014"), ("ascii", "-")),
    )
    def test_unicode_dash_replacement_when_unprintable(
        self,
        _m_getuid,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        encoding,
        expected_dash,
        FakeConfig,
    ):
        # This test can't use capsys because it doesn't emulate sys.stdout
        # encoding accurately in older versions of pytest
        underlying_stdout = io.BytesIO()
        fake_stdout = io.TextIOWrapper(underlying_stdout, encoding=encoding)

        with mock.patch("sys.stdout", fake_stdout):
            action_status(
                mock.MagicMock(all=True), cfg=FakeConfig.for_attached_machine()
            )

        fake_stdout.flush()  # Make sure all output is in underlying_stdout
        out = underlying_stdout.getvalue().decode(encoding)

        # Colour codes are converted to spaces, so strip them out for
        # comparison
        out = out.replace(" " * 17, " " * 8)

        expected_out = ATTACHED_STATUS.format(dash=expected_dash, notices="")
        assert expected_out == out
