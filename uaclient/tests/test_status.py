import mock
import pytest
import string

from uaclient import config
from uaclient.status import (
    format_tabular,
    TxtColor,
    colorize_commands,
    UserFacingStatus,
)


@pytest.fixture(params=[True, False])
def status_dict_attached(request):
    status = config.DEFAULT_STATUS.copy()

    # The following are required so we don't get an "unattached" error
    status["attached"] = True
    status["expires"] = "expires"
    status["account"] = {"name": ""}
    status["contract"] = {
        "name": "",
        "tech_support_level": UserFacingStatus.INAPPLICABLE.value,
    }

    if request.param:
        status["account"]["name"] = "account"
        status["contract"]["name"] = "subscription"

    return status


@pytest.fixture
def status_dict_unattached():
    status = config.DEFAULT_STATUS.copy()

    status["services"] = [
        {
            "name": "cc-eal",
            "description": "Common Criteria EAL2 Provisioning Packages",
            "available": "no",
        }
    ]

    return status


class TestColorizeCommands:
    @pytest.mark.parametrize(
        "commands,expected",
        [
            (
                [
                    ["apt", "update"],
                    ["apt", "install", "--only-upgrade", "-y", "pkg"],
                ],
                TxtColor.DISABLEGREY
                + "{ apt update && apt install --only-upgrade -y pkg }"
                + TxtColor.ENDC,
            ),
            (
                [
                    ["apt", "update"],
                    [
                        "apt",
                        "install",
                        "--only-upgrade",
                        "-y",
                        "longpackagename1",
                        "longpackagename2",
                        "longpackagename3",
                        "longpackagename4",
                        "longpackagename5",
                        "longpackagename6",
                        "longpackagename7",
                        "longpackagename8",
                        "longpackagename9",
                        "longpackagename10",
                    ],
                ],
                TxtColor.DISABLEGREY
                + "{\n"
                + "  apt update && apt install --only-upgrade -y longpackagename1 \\\n"  # noqa: E501
                + "  longpackagename2 longpackagename3 longpackagename4 longpackagename5 \\\n"  # noqa: E501
                + "  longpackagename6 longpackagename7 longpackagename8 longpackagename9 \\\n"  # noqa: E501
                + "  longpackagename10"
                + "\n}"
                + TxtColor.ENDC,
            ),
        ],
    )
    def test_colorize_commands(self, commands, expected):
        assert colorize_commands(commands) == expected


class TestFormatTabular:
    @pytest.mark.parametrize(
        "support_level,expected_colour,istty",
        [
            ("n/a", TxtColor.DISABLEGREY, True),
            ("essential", TxtColor.OKGREEN, True),
            ("standard", TxtColor.OKGREEN, True),
            ("advanced", TxtColor.OKGREEN, True),
            ("something else", None, True),
            ("n/a", TxtColor.DISABLEGREY, True),
            ("essential", None, False),
            ("standard", None, False),
            ("advanced", None, False),
            ("something else", None, False),
            ("n/a", None, False),
        ],
    )
    @mock.patch("sys.stdout.isatty")
    def test_support_colouring(
        self,
        m_isatty,
        support_level,
        expected_colour,
        istty,
        status_dict_attached,
    ):
        status_dict_attached["contract"]["tech_support_level"] = support_level

        m_isatty.return_value = istty
        tabular_output = format_tabular(status_dict_attached)

        expected_string = "Technical support level: {}".format(
            support_level
            if not expected_colour
            else expected_colour + support_level + TxtColor.ENDC
        )
        assert expected_string in tabular_output

    @pytest.mark.parametrize("origin", ["free", "not-free"])
    def test_header_alignment(self, origin, status_dict_attached):
        status_dict_attached["origin"] = origin
        tabular_output = format_tabular(status_dict_attached)
        colon_idx = None
        for line in tabular_output.splitlines():
            if ":" not in line or "Enable services" in line:
                # This isn't a header line
                continue
            if colon_idx is None:
                # This is the first header line, record where the colon is
                colon_idx = line.index(":")
                continue
            # Ensure that the colon in this line is aligned with previous ones
            assert line.index(":") == colon_idx

    @pytest.mark.parametrize(
        "origin,expected_headers",
        [
            ("free", ()),
            ("not-free", ("Valid until", "Technical support level")),
        ],
    )
    def test_correct_header_keys_included(
        self, origin, expected_headers, status_dict_attached
    ):
        status_dict_attached["origin"] = origin

        if status_dict_attached["contract"].get("name"):
            expected_headers = ("Subscription",) + expected_headers
        if status_dict_attached["account"].get("name"):
            expected_headers = ("Account",) + expected_headers

        tabular_output = format_tabular(status_dict_attached)

        headers = [
            line.split(":")[0].strip()
            for line in tabular_output.splitlines()
            if ":" in line and "Enable services" not in line
        ]
        assert list(expected_headers) == headers

    def test_correct_unattached_column_alignment(self, status_dict_unattached):
        tabular_output = format_tabular(status_dict_unattached)
        [header, eal_service_line] = [
            line
            for line in tabular_output.splitlines()
            if "eal" in line or "AVAILABLE" in line
        ]
        printable_eal_line = "".join(
            filter(lambda x: x in string.printable, eal_service_line)
        )
        assert header.find("AVAILABLE") == printable_eal_line.find("no")
        assert header.find("DESCRIPTION") == printable_eal_line.find("Common")

    @pytest.mark.parametrize("attached", [True, False])
    def test_no_leading_newline(
        self, attached, status_dict_attached, status_dict_unattached
    ):
        if attached:
            status_dict = status_dict_attached
        else:
            status_dict = status_dict_unattached

        assert not format_tabular(status_dict).startswith("\n")

    @pytest.mark.parametrize(
        "description_override, uf_status, uf_descr",
        (
            ("", "n/a", "Common Criteria EAL2 default descr"),
            ("Custom descr", "n/a", "Custom descr"),
            ("Custom call to action", "enabled", "Custom call to action"),
        ),
    )
    def test_custom_descr(
        self, description_override, uf_status, uf_descr, status_dict_attached
    ):
        """Services can provide a custom call to action if present."""
        default_descr = "Common Criteria EAL2 default descr"
        status_dict_attached["services"] = [
            {
                "name": "cc-eal",
                "description": default_descr,
                "available": "no",
                "status": uf_status,
                "entitled": True,
                "description_override": description_override,
            }
        ]
        if not description_override:
            # Remove key to test upgrade path from older ua-tools
            status_dict_attached["services"][0].pop("description_override")
        assert uf_descr in format_tabular(status_dict_attached)
