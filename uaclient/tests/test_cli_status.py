import copy
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

from uaclient import exceptions, messages, status
from uaclient.cli import action_status, get_parser, main, status_parser
from uaclient.event_logger import EventLoggerMode

M_PATH = "uaclient.cli."


RESPONSE_AVAILABLE_SERVICES = [
    {"name": "livepatch", "available": True},
    {"name": "fips", "available": False},
    {"name": "esm-infra", "available": True},
    {"name": "esm-apps", "available": True},
    {"name": "fips-updates", "available": False},
    {"name": "realtime-kernel", "available": False},
    {"name": "ros", "available": False},
    {"name": "ros-updates", "available": False},
]

RESPONSE_CONTRACT_INFO = {
    "accountInfo": {
        "createdAt": "2019-06-14T06:45:50Z",
        "id": "some_id",
        "name": "Name",
        "type": "paid",
    },
    "contractInfo": {
        "createdAt": "2021-05-21T20:00:53Z",
        "createdBy": "someone",
        "effectiveTo": "9999-12-31T00:00:00Z",
        "id": "some_id",
        "name": "Name",
        "products": ["uai-essential-virtual"],
        "resourceEntitlements": [
            {
                "type": "esm-infra",
                "entitled": True,
                "obligations": {"enableByDefault": True},
            },
            {
                "type": "esm-apps",
                "entitled": False,
                "obligations": {"enableByDefault": True},
            },
            {
                "type": "livepatch",
                "entitled": True,
                "obligations": {"enableByDefault": False},
            },
            {
                "type": "support",
                "entitled": True,
                "affordances": {"supportLevel": "essential"},
            },
        ],
    },
}

SIMULATED_STATUS_ALL = """\
SERVICE          AVAILABLE  ENTITLED   AUTO_ENABLED  DESCRIPTION
esm-apps         yes        no         yes           Expanded Security Maintenance for Applications
esm-infra        yes        yes        yes           Expanded Security Maintenance for Infrastructure
fips             no         no         no            NIST-certified core packages
fips-updates     no         no         no            NIST-certified core packages with priority security updates
livepatch        yes        yes        no            Canonical Livepatch service
realtime-kernel  no         no         no            Ubuntu kernel with PREEMPT_RT patches integrated
ros              no         no         no            Security Updates for the Robot Operating System
ros-updates      no         no         no            All Updates for the Robot Operating System
"""  # noqa: E501

SIMULATED_STATUS = """\
SERVICE          AVAILABLE  ENTITLED   AUTO_ENABLED  DESCRIPTION
esm-infra        yes        yes        yes           Expanded Security Maintenance for Infrastructure
livepatch        yes        yes        no            Canonical Livepatch service
"""  # noqa: E501

UNATTACHED_STATUS_ALL = """\
SERVICE          AVAILABLE  DESCRIPTION
esm-apps         yes        Expanded Security Maintenance for Applications
esm-infra        yes        Expanded Security Maintenance for Infrastructure
fips             no         NIST-certified core packages
fips-updates     no         NIST-certified core packages with priority security updates
livepatch        yes        Canonical Livepatch service
realtime-kernel  no         Ubuntu kernel with PREEMPT_RT patches integrated
ros              no         Security Updates for the Robot Operating System
ros-updates      no         All Updates for the Robot Operating System

This machine is not attached to an Ubuntu Pro subscription.
See https://ubuntu.com/pro
"""  # noqa: E501

UNATTACHED_STATUS = """\
SERVICE          AVAILABLE  DESCRIPTION
esm-infra        yes        Expanded Security Maintenance for Infrastructure
livepatch        yes        Canonical Livepatch service

This machine is not attached to an Ubuntu Pro subscription.
See https://ubuntu.com/pro
"""  # noqa: E501

ATTACHED_STATUS_ALL = """\
SERVICE          ENTITLED  STATUS    DESCRIPTION
esm-apps         no        {dash}         Expanded Security Maintenance for Applications
esm-infra        no        {dash}         Expanded Security Maintenance for Infrastructure
fips             no        {dash}         NIST-certified core packages
fips-updates     no        {dash}         NIST-certified core packages with priority security updates
livepatch        no        {dash}         Canonical Livepatch service
realtime-kernel  no        {dash}         Ubuntu kernel with PREEMPT_RT patches integrated
ros              no        {dash}         Security Updates for the Robot Operating System
ros-updates      no        {dash}         All Updates for the Robot Operating System
{notices}{features}
Enable services with: pro enable <service>

                Account: test_account
           Subscription: test_contract
            Valid until: formatteddate
Technical support level: n/a
"""  # noqa: E501

# Omit beta services from status
ATTACHED_STATUS = """\
SERVICE          ENTITLED  STATUS    DESCRIPTION
esm-infra        no        {dash}         Expanded Security Maintenance for Infrastructure
livepatch        no        {dash}         Canonical Livepatch service
{notices}{features}
Enable services with: pro enable <service>

                Account: test_account
           Subscription: test_contract
            Valid until: formatteddate
Technical support level: n/a
"""  # noqa: E501

BETA_SVC_NAMES = ["esm-apps", "realtime-kernel", "ros", "ros-updates"]

SERVICES_JSON_ALL = [
    {
        "description": "Expanded Security Maintenance for Applications",
        "description_override": None,
        "entitled": "no",
        "name": "esm-apps",
        "status": "—",
        "status_details": "",
        "available": "yes",
        "blocked_by": [],
    },
    {
        "description": "Expanded Security Maintenance for Infrastructure",
        "description_override": None,
        "entitled": "no",
        "name": "esm-infra",
        "status": "—",
        "status_details": "",
        "available": "yes",
        "blocked_by": [],
    },
    {
        "description": "NIST-certified core packages",
        "description_override": None,
        "entitled": "no",
        "name": "fips",
        "status": "—",
        "status_details": "",
        "available": "no",
        "blocked_by": [],
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
        "available": "no",
        "blocked_by": [],
    },
    {
        "description": "Canonical Livepatch service",
        "description_override": None,
        "entitled": "no",
        "name": "livepatch",
        "status": "—",
        "status_details": "",
        "available": "yes",
        "blocked_by": [],
    },
    {
        "description": "Ubuntu kernel with PREEMPT_RT patches integrated",
        "description_override": None,
        "entitled": "no",
        "name": "realtime-kernel",
        "status": "—",
        "status_details": "",
        "available": "no",
        "blocked_by": [],
    },
    {
        "description": "Security Updates for the Robot Operating System",
        "description_override": None,
        "entitled": "no",
        "name": "ros",
        "status": "—",
        "status_details": "",
        "available": "no",
        "blocked_by": [],
    },
    {
        "description": "All Updates for the Robot Operating System",
        "description_override": None,
        "entitled": "no",
        "name": "ros-updates",
        "status": "—",
        "status_details": "",
        "available": "no",
        "blocked_by": [],
    },
]

SERVICES_JSON = [
    {
        "description": "Expanded Security Maintenance for Infrastructure",
        "description_override": None,
        "entitled": "no",
        "name": "esm-infra",
        "status": "—",
        "status_details": "",
        "available": "yes",
        "blocked_by": [],
    },
    {
        "description": "Canonical Livepatch service",
        "description_override": None,
        "entitled": "no",
        "name": "livepatch",
        "status": "—",
        "status_details": "",
        "available": "yes",
        "blocked_by": [],
    },
]

HELP_OUTPUT = textwrap.dedent(
    """\
usage: pro status [flags]

Report current status of Ubuntu Pro services on system.

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

If --simulate-with-token is used, then the output has five
columns. SERVICE, AVAILABLE, ENTITLED and DESCRIPTION are the same
as mentioned above, and AUTO_ENABLED shows whether the service is set
to be enabled when that token is attached.

If the --all flag is set, beta and unavailable services are also
listed in the output.

Flags:
  -h, --help            show this help message and exit
  --wait                Block waiting on pro to complete
  --format {tabular,json,yaml}
                        output status in the specified format (default:
                        tabular)
  --simulate-with-token TOKEN
                        simulate the output status using a provided token
  --all                 Allow the visualization of beta services
"""
)


@mock.patch("uaclient.cli.contract.is_contract_changed", return_value=False)
@mock.patch("uaclient.files.NoticeFile.remove")
@mock.patch("uaclient.system.should_reboot", return_value=False)
@mock.patch(
    "uaclient.status.get_available_resources",
    return_value=RESPONSE_AVAILABLE_SERVICES,
)
@mock.patch(
    "uaclient.status.get_contract_information",
    return_value=RESPONSE_CONTRACT_INFO,
)
@mock.patch(M_PATH + "os.getuid", return_value=0)
class TestActionStatus:
    def test_status_help(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        capsys,
        FakeConfig,
    ):
        with pytest.raises(SystemExit):
            with mock.patch("sys.argv", ["/usr/bin/ua", "status", "--help"]):
                with mock.patch(
                    "uaclient.config.UAConfig",
                    return_value=FakeConfig(),
                ):
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
    @pytest.mark.parametrize(
        "features,feature_status",
        (
            ({}, ""),
            (
                {"one": True, "other": False, "some": "thing"},
                "\nFEATURES\none: True\nother: False\nsome: thing\n",
            ),
        ),
    )
    @mock.patch("uaclient.status.format_expires", return_value="formatteddate")
    def test_attached(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        _m_format_expires,
        notices,
        notice_status,
        features,
        feature_status,
        use_all,
        capsys,
        FakeConfig,
    ):
        """Check that root and non-root will emit attached status"""
        cfg = FakeConfig.for_attached_machine()
        cfg.write_cache("notices", notices)
        with mock.patch(
            "uaclient.config.UAConfig.features",
            new_callable=mock.PropertyMock,
            return_value=features,
        ):
            assert 0 == action_status(
                mock.MagicMock(all=use_all, simulate_with_token=None), cfg=cfg
            )
        # capsys already converts colorized non-printable chars to space
        # Strip non-printables from output
        printable_stdout = capsys.readouterr()[0].replace(" " * 17, " " * 8)

        # On older versions of pytest, capsys doesn't set sys.stdout.encoding
        # to something that Python parses as UTF-8 compatible, so we get the
        # ASCII dash; testing for the "wrong" dash here is OK, because we have
        # a specific test that the correct one is used in
        # test_unicode_dash_replacement_when_unprintable
        expected_dash = "-"
        status_tmpl = ATTACHED_STATUS_ALL if use_all else ATTACHED_STATUS

        if sys.stdout.encoding and "UTF-8" in sys.stdout.encoding.upper():
            expected_dash = "\u2014"
        assert (
            status_tmpl.format(
                dash=expected_dash,
                notices=notice_status,
                features=feature_status,
            )
            == printable_stdout
        )

    @pytest.mark.parametrize(
        "use_all",
        (
            (True),
            (False),
        ),
    )
    def test_unattached(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        use_all,
        capsys,
        FakeConfig,
    ):
        """Check that unattached status is emitted to console"""
        cfg = FakeConfig()

        expected = UNATTACHED_STATUS_ALL if use_all else UNATTACHED_STATUS
        assert 0 == action_status(
            mock.MagicMock(all=use_all, simulate_with_token=None), cfg=cfg
        )
        assert expected == capsys.readouterr()[0]

    @pytest.mark.parametrize(
        "use_all",
        (
            (True),
            (False),
        ),
    )
    def test_simulated(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        use_all,
        capsys,
        FakeConfig,
    ):
        """Check that a simulated status is emitted to console"""
        cfg = FakeConfig()
        expected = SIMULATED_STATUS_ALL if use_all else SIMULATED_STATUS

        assert 0 == action_status(
            mock.MagicMock(all=use_all, simulate_with_token="some_token"),
            cfg=cfg,
        )
        assert expected == capsys.readouterr()[0]

    @mock.patch("uaclient.version.get_version", return_value="test_version")
    @mock.patch("uaclient.system.subp")
    @mock.patch(M_PATH + "time.sleep")
    def test_wait_blocks_until_lock_released(
        self,
        m_sleep,
        _m_subp,
        _m_get_version,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        capsys,
        FakeConfig,
    ):
        """Check that --wait will will block and poll until lock released."""
        cfg = FakeConfig()
        lock_file = cfg.data_path("lock")
        cfg.write_cache("lock", "123:pro auto-attach")

        def fake_sleep(seconds):
            if m_sleep.call_count == 3:
                os.unlink(lock_file)
                os.unlink(cfg.notice_file.file.path)

        m_sleep.side_effect = fake_sleep

        assert 0 == action_status(
            mock.MagicMock(all=False, simulate_with_token=None), cfg=cfg
        )
        assert [mock.call(1)] * 3 == m_sleep.call_args_list
        assert "...\n" + UNATTACHED_STATUS == capsys.readouterr()[0]

    @pytest.mark.parametrize(
        "use_all",
        (
            (True),
            (False),
        ),
    )
    @pytest.mark.parametrize(
        "format_type,event_logger_mode",
        (("json", EventLoggerMode.JSON), ("yaml", EventLoggerMode.YAML)),
    )
    @pytest.mark.parametrize(
        "environ",
        (
            {},
            {
                "UA_DATA_DIR": "data_dir",
                "UA_TEST": "test",
                "UA_FEATURES_ALLOW_BETA": "true",
                "UA_CONFIG_FILE": "config_file",
            },
        ),
    )
    def test_unattached_formats(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        environ,
        format_type,
        event_logger_mode,
        use_all,
        capsys,
        FakeConfig,
        event,
    ):
        """Check that unattached status json output is emitted to console"""
        cfg = FakeConfig()

        args = mock.MagicMock(
            format=format_type, all=use_all, simulate_with_token=None
        )
        with mock.patch.object(os, "environ", environ):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger_mode
            ), mock.patch.object(event, "_command", "status"):
                assert 0 == action_status(args, cfg=cfg)

        expected_environment = []
        if environ:
            expected_environment = [
                {"name": "UA_CONFIG_FILE", "value": "config_file"},
                {"name": "UA_DATA_DIR", "value": "data_dir"},
                {"name": "UA_FEATURES_ALLOW_BETA", "value": "true"},
            ]

        services = SERVICES_JSON_ALL if use_all else SERVICES_JSON
        services = [
            {
                "name": service["name"],
                "description": service["description"],
                "available": service["available"],
            }
            for service in services
        ]

        expected = {
            "_doc": (
                "Content provided in json response is currently "
                "considered Experimental and may change"
            ),
            "_schema_version": "0.1",
            "version": mock.ANY,
            "execution_status": status.UserFacingConfigStatus.INACTIVE.value,
            "execution_details": messages.NO_ACTIVE_OPERATIONS,
            "attached": False,
            "machine_id": None,
            "effective": None,
            "expires": None,
            "features": {},
            "notices": [],
            "services": services,
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
            "simulated": False,
            "errors": [],
            "warnings": [],
            "result": "success",
        }

        if format_type == "json":
            assert expected == json.loads(capsys.readouterr()[0])
        else:
            assert expected == yaml.safe_load(capsys.readouterr()[0])

    @pytest.mark.parametrize(
        "format_type,event_logger_mode",
        (("json", EventLoggerMode.JSON), ("yaml", EventLoggerMode.YAML)),
    )
    @pytest.mark.parametrize(
        "environ",
        (
            {},
            {
                "UA_DATA_DIR": "data_dir",
                "UA_TEST": "test",
                "UA_FEATURES_ALLOW_BETA": "true",
                "UA_CONFIG_FILE": "config_file",
            },
        ),
    )
    @pytest.mark.parametrize("use_all", (True, False))
    def test_attached_formats(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        use_all,
        environ,
        format_type,
        event_logger_mode,
        capsys,
        FakeConfig,
        event,
    ):
        """Check that unattached status json output is emitted to console"""
        cfg = FakeConfig.for_attached_machine()

        args = mock.MagicMock(
            format=format_type, all=use_all, simulate_with_token=None
        )

        with mock.patch.object(os, "environ", environ):
            with mock.patch.object(
                event, "_event_logger_mode", event_logger_mode
            ), mock.patch.object(event, "_command", "status"):
                with mock.patch(
                    "uaclient.status._get_blocked_by_services", return_value=[]
                ):
                    assert 0 == action_status(args, cfg=cfg)

        expected_environment = []
        if environ:
            expected_environment = [
                {"name": "UA_CONFIG_FILE", "value": "config_file"},
                {"name": "UA_DATA_DIR", "value": "data_dir"},
                {"name": "UA_FEATURES_ALLOW_BETA", "value": "true"},
            ]

        services = SERVICES_JSON_ALL if use_all else SERVICES_JSON

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
            "version": mock.ANY,
            "execution_status": status.UserFacingConfigStatus.INACTIVE.value,
            "execution_details": messages.NO_ACTIVE_OPERATIONS,
            "attached": True,
            "machine_id": "test_machine_id",
            "effective": effective,
            "expires": expires,
            "features": {},
            "notices": [],
            "services": services,
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
                "external_account_ids": [{"IDs": ["id1"], "origin": "AWS"}],
            },
            "config_path": None,
            "config": {"data_dir": mock.ANY},
            "simulated": False,
            "errors": [],
            "warnings": [],
            "result": "success",
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

    @pytest.mark.parametrize(
        "format_type,event_logger_mode",
        (("json", EventLoggerMode.JSON), ("yaml", EventLoggerMode.YAML)),
    )
    @pytest.mark.parametrize("use_all", (True, False))
    def test_simulated_formats(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        use_all,
        format_type,
        event_logger_mode,
        capsys,
        FakeConfig,
        event,
    ):
        """Check that simulated status json output is emitted to console"""
        cfg = FakeConfig()

        args = mock.MagicMock(
            format=format_type, all=use_all, simulate_with_token="some_token"
        )

        with mock.patch.object(
            event, "_event_logger_mode", event_logger_mode
        ), mock.patch.object(event, "_command", "status"):
            assert 0 == action_status(args, cfg=cfg)

        beta_services = [
            {
                "auto_enabled": "yes",
                "available": "yes",
                "description": "Expanded Security Maintenance for Applications",  # noqa
                "entitled": "no",
                "name": "esm-apps",
            },
            {
                "auto_enabled": "no",
                "available": "no",
                "description": "Security Updates for the Robot Operating"
                " System",
                "entitled": "no",
                "name": "ros",
            },
            {
                "auto_enabled": "no",
                "available": "no",
                "description": "All Updates for the Robot Operating System",
                "entitled": "no",
                "name": "ros-updates",
            },
        ]

        services = [
            {
                "auto_enabled": "yes",
                "available": "yes",
                "description": "Expanded Security Maintenance for Infrastructure",  # noqa
                "entitled": "yes",
                "name": "esm-infra",
            },
            {
                "auto_enabled": "no",
                "available": "no",
                "description": "NIST-certified core packages",
                "entitled": "no",
                "name": "fips",
            },
            {
                "auto_enabled": "no",
                "available": "no",
                "description": "NIST-certified core packages with priority"
                " security updates",
                "entitled": "no",
                "name": "fips-updates",
            },
            {
                "auto_enabled": "no",
                "available": "yes",
                "description": "Canonical Livepatch service",
                "entitled": "yes",
                "name": "livepatch",
            },
            {
                "auto_enabled": "no",
                "available": "no",
                "description": "Ubuntu kernel with PREEMPT_RT patches"
                " integrated",
                "entitled": "no",
                "name": "realtime-kernel",
            },
        ]

        expected_services = sorted(
            services + beta_services, key=lambda x: x["name"]
        )
        if not use_all:
            expected_services = [
                service
                for service in services
                if service["available"] == "yes"
            ]

        expected = {
            "_doc": "Content provided in json response is currently considered"
            " Experimental and may change",
            "_schema_version": "0.1",
            "attached": False,
            "machine_id": None,
            "features": {},
            "notices": [],
            "account": {
                "created_at": "2019-06-14T06:45:50Z",
                "external_account_ids": [],
                "id": "some_id",
                "name": "Name",
            },
            "contract": {
                "created_at": "2021-05-21T20:00:53Z",
                "id": "some_id",
                "name": "Name",
                "products": ["uai-essential-virtual"],
                "tech_support_level": "essential",
            },
            "environment_vars": [],
            "execution_status": "inactive",
            "execution_details": "No Ubuntu Pro operations are running",
            "expires": "9999-12-31T00:00:00Z",
            "effective": None,
            "services": expected_services,
            "simulated": True,
            "version": mock.ANY,
            "config_path": None,
            "config": {"data_dir": mock.ANY},
            "errors": [],
            "warnings": [],
            "result": "success",
        }

        if format_type == "json":
            assert expected == json.loads(capsys.readouterr()[0])
        else:
            assert expected == yaml.safe_load(capsys.readouterr()[0])

    def test_error_on_connectivity_errors(
        self,
        _m_getuid,
        _m_get_contract_information,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        FakeConfig,
    ):
        """Raise UrlError on connectivity issues"""
        m_get_avail_resources.side_effect = exceptions.UrlError(
            socket.gaierror(-2, "Name or service not known")
        )

        cfg = FakeConfig()

        with pytest.raises(exceptions.UrlError):
            action_status(
                mock.MagicMock(all=False, simulate_with_token=None), cfg=cfg
            )

    @pytest.mark.parametrize("use_all", (True, False))
    @pytest.mark.parametrize(
        "encoding,expected_dash",
        (("utf-8", "\u2014"), ("UTF-8", "\u2014"), ("ascii", "-")),
    )
    @mock.patch("uaclient.status.format_expires", return_value="formatteddate")
    def test_unicode_dash_replacement_when_unprintable(
        self,
        _m_getuid,
        _m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        _m_format_expires,
        encoding,
        expected_dash,
        use_all,
        FakeConfig,
    ):
        # This test can't use capsys because it doesn't emulate sys.stdout
        # encoding accurately in older versions of pytest
        underlying_stdout = io.BytesIO()
        fake_stdout = io.TextIOWrapper(underlying_stdout, encoding=encoding)

        with mock.patch("sys.stdout", fake_stdout):
            action_status(
                mock.MagicMock(all=use_all, simulate_with_token=None),
                cfg=FakeConfig.for_attached_machine(),
            )

        fake_stdout.flush()  # Make sure all output is in underlying_stdout
        out = underlying_stdout.getvalue().decode(encoding)

        # Colour codes are converted to spaces, so strip them out for
        # comparison
        out = out.replace(" " * 17, " " * 8)

        if not use_all:
            expected_out = ATTACHED_STATUS.format(
                dash=expected_dash, notices="", features=""
            )
        else:
            expected_out = ATTACHED_STATUS_ALL.format(
                dash=expected_dash, notices="", features=""
            )

        assert expected_out == out

    @pytest.mark.parametrize(
        "exception_to_throw,exception_type,exception_message",
        (
            (
                exceptions.UrlError("Not found", 404),
                exceptions.UrlError,
                "Not found",
            ),
            (
                exceptions.ContractAPIError(
                    exceptions.UrlError("Unauthorized", 401),
                    {"message": "unauthorized"},
                ),
                exceptions.UserFacingError,
                "Invalid token. See https://ubuntu.com/pro",
            ),
        ),
    )
    def test_errors_are_raised_appropriately(
        self,
        _m_getuid,
        m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        exception_to_throw,
        exception_type,
        exception_message,
        capsys,
        FakeConfig,
    ):
        """Check that simulated status json/yaml output raises errors."""

        m_get_contract_information.side_effect = exception_to_throw

        cfg = FakeConfig()

        args = mock.MagicMock(
            format="json", all=False, simulate_with_token="some_token"
        )

        with pytest.raises(exception_type) as exc:
            action_status(args, cfg=cfg)

        assert exc.type == exception_type
        assert exception_message in getattr(exc.value, "msg", exc.value.args)

    @pytest.mark.parametrize(
        "token_to_use,warning_message,contract_field,date_value",
        (
            (
                "expired_token",
                'Contract "some_id" expired on December 31, 2019',
                "effectiveTo",
                "2019-12-31T00:00:00Z",
            ),
            (
                "token_not_valid_yet",
                'Contract "some_id" is not effective until December 31, 9999',
                "effectiveFrom",
                "9999-12-31T00:00:00Z",
            ),
        ),
    )
    @pytest.mark.parametrize(
        "format_type,event_logger_mode",
        (("json", EventLoggerMode.JSON), ("yaml", EventLoggerMode.YAML)),
    )
    def test_errors_for_token_dates(
        self,
        _m_getuid,
        m_get_contract_information,
        _m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        format_type,
        event_logger_mode,
        token_to_use,
        warning_message,
        contract_field,
        date_value,
        capsys,
        FakeConfig,
        event,
    ):
        """Check errors for expired tokens, and not valid yet tokens."""

        def contract_info_side_effect(cfg, token):
            response = copy.deepcopy(RESPONSE_CONTRACT_INFO)
            response["contractInfo"][contract_field] = date_value
            return response

        m_get_contract_information.side_effect = contract_info_side_effect

        cfg = FakeConfig()

        args = mock.MagicMock(
            format=format_type, all=False, simulate_with_token=token_to_use
        )

        with mock.patch.object(
            event, "_event_logger_mode", event_logger_mode
        ), mock.patch.object(event, "_command", "status"):
            assert 1 == action_status(args, cfg=cfg)

        if format_type == "json":
            output = json.loads(capsys.readouterr()[0])
        else:
            output = yaml.safe_load(capsys.readouterr()[0])

        assert output["errors"][0]["message"] == warning_message

    @pytest.mark.parametrize(
        "contract_changed,is_attached",
        (
            (False, True),
            (True, False),
            (True, True),
            (False, False),
        ),
    )
    @mock.patch("uaclient.files.NoticeFile.try_remove")
    @mock.patch("uaclient.files.NoticeFile.add")
    def test_is_contract_changed(
        self,
        m_add_notice,
        m_try_remove_notice,
        _m_getuid,
        _m_get_contract_information,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        _m_contract_changed,
        contract_changed,
        is_attached,
        capsys,
        FakeConfig,
    ):
        _m_contract_changed.return_value = contract_changed
        if is_attached:
            cfg = FakeConfig().for_attached_machine()
        else:
            cfg = FakeConfig()

        action_status(
            mock.MagicMock(all=False, simulate_with_token=None), cfg=cfg
        )

        if is_attached:
            if contract_changed:
                assert [
                    mock.call("", messages.NOTICE_REFRESH_CONTRACT_WARNING)
                ] == m_add_notice.call_args_list
            else:
                assert [
                    mock.call("", messages.NOTICE_REFRESH_CONTRACT_WARNING)
                ] not in m_add_notice.call_args_list
                assert [
                    mock.call("", messages.NOTICE_REFRESH_CONTRACT_WARNING)
                ] in m_try_remove_notice.call_args_list
        else:
            assert _m_contract_changed.call_count == 0


class TestStatusParser:
    @mock.patch(M_PATH + "contract.get_available_resources")
    def test_status_parser_updates_parser_config(
        self, _m_resources, FakeConfig
    ):
        """Update the parser configuration for 'status'."""
        m_parser = status_parser(mock.Mock())
        assert "status" == m_parser.prog

        full_parser = get_parser(FakeConfig())
        with mock.patch(
            "sys.argv",
            [
                "pro",
                "status",
                "--format",
                "json",
                "--simulate-with-token",
                "some_token",
                "--all",
            ],
        ):
            args = full_parser.parse_args()
        assert "status" == args.command
        assert True is args.all
        assert "json" == args.format
        assert "some_token" == args.simulate_with_token
        assert "action_status" == args.action.__name__
