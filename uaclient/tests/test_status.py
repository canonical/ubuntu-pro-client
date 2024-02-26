import copy
import datetime
import string

import mock
import pytest

from uaclient import messages, status
from uaclient.entitlements import (
    ENTITLEMENT_CLASSES,
    entitlement_factory,
    valid_services,
)
from uaclient.entitlements.base import EntitlementWithMessage
from uaclient.entitlements.entitlement_status import (
    ApplicationStatus,
    ContractStatus,
    UserFacingConfigStatus,
    UserFacingStatus,
)
from uaclient.entitlements.fips import FIPSEntitlement
from uaclient.entitlements.ros import ROSEntitlement
from uaclient.entitlements.tests.test_base import ConcreteTestEntitlement
from uaclient.files.notices import Notice, NoticesManager
from uaclient.status import (
    DEFAULT_STATUS,
    TxtColor,
    colorize_commands,
    format_tabular,
)

DEFAULT_CFG_STATUS = {
    "execution_status": DEFAULT_STATUS["execution_status"],
    "execution_details": DEFAULT_STATUS["execution_details"],
}
M_PATH = "uaclient.entitlements."


@pytest.fixture
def all_resources_available(FakeConfig):
    resources = [
        {"name": name, "available": True}
        for name in valid_services(cfg=FakeConfig(), allow_beta=True)
    ]
    return resources


@pytest.fixture(params=[True, False])
def status_dict_attached(request):
    status = DEFAULT_STATUS.copy()

    # The following are required so we don't get an "unattached" error
    status["attached"] = True
    status["expires"] = datetime.datetime.now(datetime.timezone.utc)
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
    status = DEFAULT_STATUS.copy()

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


@mock.patch("uaclient.livepatch.on_supported_kernel", return_value=None)
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
        m_on_supported_kernel,
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
    def test_header_alignment(
        self, m_on_supported_kernel, origin, status_dict_attached
    ):
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
        self,
        m_on_supported_kernel,
        origin,
        expected_headers,
        status_dict_attached,
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

    def test_correct_unattached_column_alignment(
        self, m_on_supported_kernel, status_dict_unattached
    ):
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
        self,
        m_on_supported_kernel,
        attached,
        status_dict_attached,
        status_dict_unattached,
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
        self,
        m_on_supported_kernel,
        description_override,
        uf_status,
        uf_descr,
        status_dict_attached,
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


@pytest.fixture
def esm_desc(FakeConfig):
    return entitlement_factory(cfg=FakeConfig(), name="esm-infra").description


@pytest.fixture
def ros_desc(FakeConfig):
    return entitlement_factory(cfg=FakeConfig(), name="ros").description


@mock.patch("uaclient.livepatch.on_supported_kernel", return_value=None)
@mock.patch("uaclient.files.notices.NoticesManager.remove")
@mock.patch("uaclient.system.should_reboot", return_value=False)
class TestStatus:
    def check_beta(self, cls, show_all, uacfg=None, status=""):
        if not show_all:
            if status == "enabled":
                return False

            if uacfg:
                allow_beta = uacfg.cfg.get("features", {}).get(
                    "allow_beta", False
                )

                if allow_beta:
                    return False

            return cls.is_beta

        return False

    @pytest.mark.parametrize("show_all", (True, False))
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.status.get_available_resources")
    def test_root_unattached(
        self,
        m_get_available_resources,
        _m_status_cache_file,
        _m_should_reboot,
        _m_remove_notice,
        m_on_supported_kernel,
        ros_desc,
        esm_desc,
        show_all,
        FakeConfig,
    ):
        """Test we get the correct status dict when unattached"""
        if show_all:
            expected_services = [
                {
                    "available": "yes",
                    "name": "esm-infra",
                    "description": esm_desc,
                    "description_override": None,
                },
                {
                    "available": "no",
                    "name": "ros",
                    "description": ros_desc,
                    "description_override": None,
                },
            ]
        else:
            expected_services = [
                {
                    "available": "yes",
                    "name": "esm-infra",
                    "description": esm_desc,
                    "description_override": None,
                }
            ]
        cfg = FakeConfig()
        m_get_available_resources.return_value = [
            {"name": "esm-infra", "available": True},
            {"name": "ros", "available": False},
        ]
        expected = copy.deepcopy(DEFAULT_STATUS)
        expected["version"] = mock.ANY
        expected["services"] = expected_services
        with mock.patch(
            "uaclient.status._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == status.status(cfg=cfg, show_all=show_all)

    @pytest.mark.parametrize(
        "features_override", ((None), ({"allow_beta": True}))
    )
    @pytest.mark.parametrize(
        "avail_res,entitled_res,uf_entitled,uf_status",
        (
            (  # Empty lists means UNENTITLED and UNAVAILABLE
                [],
                [],
                ContractStatus.UNENTITLED.value,
                UserFacingStatus.UNAVAILABLE.value,
            ),
            (  # available == False means UNAVAILABLE
                [{"name": "livepatch", "available": False}],
                [],
                ContractStatus.UNENTITLED.value,
                UserFacingStatus.UNAVAILABLE.value,
            ),
            (  # available == True but unentitled means UNAVAILABLE
                [{"name": "livepatch", "available": True}],
                [],
                ContractStatus.UNENTITLED.value,
                UserFacingStatus.UNAVAILABLE.value,
            ),
            (  # available == False and entitled means INAPPLICABLE
                [{"name": "livepatch", "available": False}],
                [{"type": "livepatch", "entitled": True}],
                ContractStatus.ENTITLED.value,
                UserFacingStatus.INAPPLICABLE.value,
            ),
        ),
    )
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch(
        M_PATH + "livepatch.LivepatchEntitlement.application_status",
        return_value=(ApplicationStatus.DISABLED, ""),
    )
    @mock.patch("uaclient.status.get_available_resources")
    def test_root_attached(
        self,
        m_get_avail_resources,
        _m_livepatch_status,
        _m_status_cache_file,
        _m_should_reboot,
        _m_remove_notice,
        m_on_supported_kernel,
        avail_res,
        entitled_res,
        uf_entitled,
        uf_status,
        features_override,
        FakeConfig,
    ):
        """Test we get the correct status dict when attached with basic conf"""
        resource_names = [resource["name"] for resource in avail_res]
        default_entitled = ContractStatus.UNENTITLED.value
        default_status = UserFacingStatus.UNAVAILABLE.value
        token = {
            "availableResources": [],
            "machineTokenInfo": {
                "machineId": "test_machine_id",
                "accountInfo": {
                    "id": "acct-1",
                    "name": "test_account",
                    "createdAt": datetime.datetime(
                        2019,
                        6,
                        14,
                        6,
                        45,
                        50,
                        tzinfo=datetime.timezone.utc,
                    ),
                    "externalAccountIDs": [{"IDs": ["id1"], "origin": "AWS"}],
                },
                "contractInfo": {
                    "id": "cid",
                    "name": "test_contract",
                    "createdAt": datetime.datetime(
                        2020,
                        5,
                        8,
                        19,
                        2,
                        26,
                        tzinfo=datetime.timezone.utc,
                    ),
                    "effectiveFrom": datetime.datetime(
                        2000,
                        5,
                        8,
                        19,
                        2,
                        26,
                        tzinfo=datetime.timezone.utc,
                    ),
                    "effectiveTo": datetime.datetime(
                        2040,
                        5,
                        8,
                        19,
                        2,
                        26,
                        tzinfo=datetime.timezone.utc,
                    ),
                    "resourceEntitlements": entitled_res,
                    "products": ["free"],
                },
            },
        }

        available_resource_response = [
            {
                "name": cls.name,
                "available": bool(
                    {"name": cls.name, "available": True} in avail_res
                ),
            }
            for cls in ENTITLEMENT_CLASSES
        ]
        if avail_res:
            token["availableResources"] = available_resource_response
        else:
            m_get_avail_resources.return_value = available_resource_response

        cfg = FakeConfig.for_attached_machine(
            machine_token=token,
        )
        if features_override:
            cfg.override_features(features_override)

        expected_services = [
            {
                "description": cls.description,
                "entitled": uf_entitled
                if cls.name in resource_names
                else default_entitled,
                "name": cls.name,
                "status": uf_status
                if cls.name in resource_names
                else default_status,
                "status_details": mock.ANY,
                "description_override": None,
                "available": mock.ANY,
                "blocked_by": [],
                "warning": None,
                "variants": {},
            }
            for cls in ENTITLEMENT_CLASSES
        ]
        expected_services.sort(key=lambda x: x.get("name", ""))
        expected = copy.deepcopy(DEFAULT_STATUS)
        expected.update(
            {
                "version": mock.ANY,
                "attached": True,
                "machine_id": "test_machine_id",
                "services": expected_services,
                "effective": datetime.datetime(
                    2000, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
                ),
                "expires": datetime.datetime(
                    2040, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
                ),
                "contract": {
                    "name": "test_contract",
                    "id": "cid",
                    "created_at": datetime.datetime(
                        2020, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
                    ),
                    "products": ["free"],
                    "tech_support_level": "n/a",
                },
                "account": {
                    "name": "test_account",
                    "id": "acct-1",
                    "created_at": datetime.datetime(
                        2019, 6, 14, 6, 45, 50, tzinfo=datetime.timezone.utc
                    ),
                    "external_account_ids": [
                        {"IDs": ["id1"], "origin": "AWS"}
                    ],
                },
            }
        )
        with mock.patch(
            "uaclient.status._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == status.status(cfg=cfg, show_all=True)
        if avail_res:
            assert m_get_avail_resources.call_count == 0
        else:
            assert m_get_avail_resources.call_count == 1
        # status() idempotent
        with mock.patch(
            "uaclient.status._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == status.status(cfg=cfg, show_all=True)

    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.util.we_are_currently_root")
    @mock.patch("uaclient.status.get_available_resources")
    def test_nonroot_unattached_is_same_as_unattached_root(
        self,
        m_get_available_resources,
        m_we_are_currently_root,
        _m_status_cache_file,
        _m_should_reboot,
        _m_remove_notice,
        m_on_supported_kernel,
        FakeConfig,
    ):
        m_get_available_resources.return_value = [
            {"name": "esm-infra", "available": True}
        ]
        m_we_are_currently_root.return_value = False
        cfg = FakeConfig()
        nonroot_status = status.status(cfg=cfg)

        m_we_are_currently_root.return_value = True
        cfg = FakeConfig()
        root_unattached_status = status.status(cfg=cfg)

        assert root_unattached_status == nonroot_status

    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.util.we_are_currently_root")
    @mock.patch("uaclient.status.get_available_resources")
    def test_root_and_non_root_are_same_attached(
        self,
        m_get_available_resources,
        m_we_are_currently_root,
        _m_status_cache_file,
        _m_should_reboot,
        _m_remove_notice,
        m_on_supported_kernel,
        FakeConfig,
    ):
        m_we_are_currently_root.return_value = True
        root_cfg = FakeConfig.for_attached_machine()
        root_status = status.status(cfg=root_cfg)
        m_we_are_currently_root.return_value = False
        normal_cfg = FakeConfig.for_attached_machine()
        normal_status = status.status(cfg=normal_cfg)
        assert normal_status == root_status

    @pytest.mark.parametrize("variants_in_contract", ((True), (False)))
    @pytest.mark.parametrize("show_all", (True, False))
    @pytest.mark.parametrize(
        "features_override", ((None), ({"allow_beta": False}))
    )
    @pytest.mark.parametrize(
        "entitlements",
        (
            [],
            [
                {
                    "type": "support",
                    "entitled": True,
                    "affordances": {"supportLevel": "anything"},
                }
            ],
        ),
    )
    @pytest.mark.usefixtures("all_resources_available")
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch(
        M_PATH + "fips.FIPSCommonEntitlement.application_status",
        return_value=(ApplicationStatus.DISABLED, ""),
    )
    @mock.patch(
        M_PATH + "livepatch.LivepatchEntitlement.application_status",
        return_value=(ApplicationStatus.DISABLED, ""),
    )
    @mock.patch(M_PATH + "livepatch.LivepatchEntitlement.user_facing_status")
    @mock.patch(M_PATH + "livepatch.LivepatchEntitlement.contract_status")
    @mock.patch(M_PATH + "landscape.LandscapeEntitlement.user_facing_status")
    @mock.patch(M_PATH + "landscape.LandscapeEntitlement.contract_status")
    @mock.patch(M_PATH + "esm.ESMAppsEntitlement.user_facing_status")
    @mock.patch(M_PATH + "esm.ESMAppsEntitlement.contract_status")
    @mock.patch(M_PATH + "repo.RepoEntitlement.user_facing_status")
    @mock.patch(M_PATH + "repo.RepoEntitlement.contract_status")
    @mock.patch(M_PATH + "base.UAEntitlement._get_contract_variants")
    def test_attached_reports_contract_and_service_status(
        self,
        m_contract_variants,
        m_repo_contract_status,
        m_repo_uf_status,
        m_esm_contract_status,
        m_esm_uf_status,
        m_landscape_contract_status,
        m_landscape_uf_status,
        m_livepatch_contract_status,
        m_livepatch_uf_status,
        _m_livepatch_status,
        _m_fips_status,
        _m_status_cache_file,
        _m_should_reboot,
        _m_remove_notice,
        m_on_supported_kernel,
        all_resources_available,
        entitlements,
        features_override,
        show_all,
        variants_in_contract,
        FakeConfig,
    ):
        """When attached, return contract and service user-facing status."""
        m_repo_contract_status.return_value = ContractStatus.ENTITLED
        m_repo_uf_status.return_value = (
            UserFacingStatus.INAPPLICABLE,
            messages.NamedMessage("test-code", "repo details"),
        )
        m_livepatch_contract_status.return_value = ContractStatus.ENTITLED
        m_livepatch_uf_status.return_value = (
            UserFacingStatus.ACTIVE,
            messages.NamedMessage("test-code", "livepatch details"),
        )
        m_esm_contract_status.return_value = ContractStatus.ENTITLED
        m_esm_uf_status.return_value = (
            UserFacingStatus.INAPPLICABLE,
            messages.NamedMessage("test-code", "esm-apps details"),
        )
        m_landscape_contract_status.return_value = ContractStatus.ENTITLED
        m_landscape_uf_status.return_value = (
            UserFacingStatus.INAPPLICABLE,
            messages.NamedMessage("test-code", "landscape details"),
        )
        token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "machineId": "test_machine_id",
                "accountInfo": {
                    "id": "1",
                    "name": "accountname",
                    "createdAt": datetime.datetime(
                        2019, 6, 14, 6, 45, 50, tzinfo=datetime.timezone.utc
                    ),
                    "externalAccountIDs": [{"IDs": ["id1"], "origin": "AWS"}],
                },
                "contractInfo": {
                    "id": "contract-1",
                    "name": "contractname",
                    "createdAt": datetime.datetime(
                        2020, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
                    ),
                    "resourceEntitlements": entitlements,
                    "products": ["free"],
                },
            },
        }
        cfg = FakeConfig.for_attached_machine(
            account_name="accountname",
            machine_token=token,
        )
        mock_notice = NoticesManager()
        if features_override:
            cfg.override_features(features_override)
        if not entitlements:
            support_level = UserFacingStatus.INAPPLICABLE.value
        else:
            support_level = entitlements[0]["affordances"]["supportLevel"]
        expected = copy.deepcopy(status.DEFAULT_STATUS)
        expected.update(
            {
                "version": mock.ANY,
                "attached": True,
                "machine_id": "test_machine_id",
                "contract": {
                    "name": "contractname",
                    "id": "contract-1",
                    "created_at": datetime.datetime(
                        2020, 5, 8, 19, 2, 26, tzinfo=datetime.timezone.utc
                    ),
                    "products": ["free"],
                    "tech_support_level": support_level,
                },
                "account": {
                    "name": "accountname",
                    "id": "1",
                    "created_at": datetime.datetime(
                        2019, 6, 14, 6, 45, 50, tzinfo=datetime.timezone.utc
                    ),
                    "external_account_ids": [
                        {"IDs": ["id1"], "origin": "AWS"}
                    ],
                },
            }
        )

        ent_details = {
            "livepatch": "livepatch details",
            "esm-apps": "esm-apps details",
            "landscape": "landscape details",
        }

        rt_variants = {
            "intel-iotg": {
                "available": mock.ANY,
                "blocked_by": [],
                "description": "RT kernel optimized "
                "for Intel IOTG "
                "platform",
                "description_override": None,
                "entitled": "yes",
                "name": "intel-iotg",
                "status": "n/a",
                "status_details": "repo details",
                "warning": None,
            },
            "nvidia-tegra": {
                "available": mock.ANY,
                "blocked_by": [],
                "description": "RT kernel "
                "optimized for "
                "NVIDIA Tegra "
                "platform",
                "description_override": None,
                "entitled": "yes",
                "name": "nvidia-tegra",
                "status": "n/a",
                "status_details": "repo details",
                "warning": None,
            },
            "generic": {
                "available": mock.ANY,
                "blocked_by": [],
                "description": "Generic version of the RT kernel (default)",
                "description_override": None,
                "entitled": "yes",
                "name": "generic",
                "status": "n/a",
                "status_details": "repo details",
                "warning": None,
            },
        }

        for cls in ENTITLEMENT_CLASSES:
            if cls.name == "realtime-kernel":
                if variants_in_contract:
                    m_contract_variants.return_value = set(
                        ["intel-iotg", "nvidia-tegra"]
                    )
                    variants = rt_variants
                else:
                    m_contract_variants.return_value = set()
                    variants = {}
            else:
                variants = {}

            if cls.name == "livepatch":
                expected_status = UserFacingStatus.ACTIVE.value
            elif show_all:
                expected_status = UserFacingStatus.INAPPLICABLE.value
            else:
                continue

            if not show_all and self.check_beta(
                cls, show_all, cfg, expected_status
            ):
                continue

            expected["services"].append(
                {
                    "name": cls.name,
                    "description": cls.description,
                    "entitled": ContractStatus.ENTITLED.value,
                    "status": expected_status,
                    "status_details": ent_details.get(
                        cls.name, "repo details"
                    ),
                    "description_override": None,
                    "available": mock.ANY,
                    "blocked_by": [],
                    "warning": None,
                    "variants": variants,
                }
            )
        expected["services"].sort(key=lambda x: x.get("name", ""))
        with mock.patch(
            "uaclient.status._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            expected_status_calls = 13 if variants_in_contract else 10
            assert expected == status.status(cfg=cfg, show_all=show_all)
            assert expected_status_calls == m_repo_uf_status.call_count
            assert 1 == m_livepatch_uf_status.call_count

        expected_calls = [
            mock.call(Notice.AUTO_ATTACH_RETRY_FULL_NOTICE),
            mock.call(Notice.AUTO_ATTACH_RETRY_TOTAL_FAILURE),
        ]

        assert expected_calls == mock_notice.remove.call_args_list

    @pytest.mark.usefixtures("all_resources_available")
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.util.we_are_currently_root")
    @mock.patch("uaclient.status.get_available_resources")
    def test_expires_handled_appropriately(
        self,
        _m_get_available_resources,
        m_we_are_currently_root,
        _m_status_cache_file,
        _m_should_reboot,
        _m_remove_notice,
        m_on_supported_kernel,
        all_resources_available,
        FakeConfig,
    ):
        m_we_are_currently_root.return_value = True
        token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "machineId": "test_machine_id",
                "accountInfo": {"id": "1", "name": "accountname"},
                "contractInfo": {
                    "name": "contractname",
                    "id": "contract-1",
                    "effectiveTo": datetime.datetime(
                        2020, 7, 18, 0, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "createdAt": datetime.datetime(
                        2020, 5, 8, 0, 0, 0, tzinfo=datetime.timezone.utc
                    ),
                    "resourceEntitlements": [],
                    "products": ["free"],
                },
            },
        }
        cfg = FakeConfig.for_attached_machine(
            account_name="accountname",
            machine_token=token,
        )

        # Test that root's status works as expected (including the cache write)
        expected_dt = datetime.datetime(
            2020, 7, 18, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        assert expected_dt == status.status(cfg=cfg)["expires"]

        # Test that the read from the status cache work properly for non-root
        # users
        m_we_are_currently_root.return_value = False
        cfg = FakeConfig.for_attached_machine(
            account_name="accountname",
            machine_token=token,
        )
        assert expected_dt == status.status(cfg=cfg)["expires"]

    @mock.patch(
        "uaclient.files.state_files.reboot_cmd_marker_file",
        new_callable=mock.PropertyMock,
    )
    @mock.patch("uaclient.files.state_files.status_cache_file.read")
    @mock.patch("uaclient.files.state_files.status_cache_file.write")
    @mock.patch("uaclient.status.get_available_resources", return_value={})
    def test_nonroot_user_does_not_use_cache(
        self,
        _m_get_available_resources,
        _m_status_cache_file_write,
        m_status_cache_file_read,
        m_reboot_cmd_marker_file,
        _m_should_reboot,
        m_remove_notice,
        m_on_supported_kernel,
        FakeConfig,
    ):
        m_reboot_cmd_marker_file.is_present = True
        cached_status = {"pass": True}
        m_status_cache_file_read.return_value = cached_status
        cfg = FakeConfig()
        before = status.status(cfg=cfg)

        # Even non-root users can update execution_status details
        details = messages.ENABLE_REBOOT_REQUIRED_TMPL.format(
            operation="configuration changes"
        )
        reboot_required = UserFacingConfigStatus.REBOOTREQUIRED.value
        cached_status.update(
            {
                "execution_status": reboot_required,
                "execution_details": details,
                "features": {},
                "notices": [],
                "config_path": None,
                "config": {"data_dir": mock.ANY},
                "services": [],
            }
        )

        assert cached_status != status.status(cfg=cfg)
        assert before == status.status(cfg=cfg)


ATTACHED_SERVICE_STATUS_PARAMETERS = [
    # ENTITLED => display the given user-facing status
    (ContractStatus.ENTITLED, UserFacingStatus.ACTIVE, False, "enabled"),
    (ContractStatus.ENTITLED, UserFacingStatus.INACTIVE, False, "disabled"),
    (ContractStatus.ENTITLED, UserFacingStatus.INAPPLICABLE, False, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.UNAVAILABLE, False, "—"),
    # UNENTITLED => UNAVAILABLE
    (ContractStatus.UNENTITLED, UserFacingStatus.ACTIVE, False, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INACTIVE, False, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INAPPLICABLE, False, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.UNAVAILABLE, [], "—"),
    # ENTITLED but in unavailable_resources => INAPPLICABLE
    (ContractStatus.ENTITLED, UserFacingStatus.ACTIVE, True, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.INACTIVE, True, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.INAPPLICABLE, True, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.UNAVAILABLE, True, "n/a"),
    # UNENTITLED and in unavailable_resources => UNAVAILABLE
    (ContractStatus.UNENTITLED, UserFacingStatus.ACTIVE, True, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INACTIVE, True, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INAPPLICABLE, True, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.UNAVAILABLE, True, "—"),
]


class TestAttachedServiceStatus:
    @pytest.mark.parametrize(
        "contract_status,uf_status,in_inapplicable_resources,expected_status",
        ATTACHED_SERVICE_STATUS_PARAMETERS,
    )
    def test_status(
        self,
        contract_status,
        uf_status,
        in_inapplicable_resources,
        expected_status,
        FakeConfig,
    ):
        ent = mock.MagicMock()
        ent.name = "test_entitlement"
        ent.contract_status.return_value = contract_status
        ent.user_facing_status.return_value = (
            uf_status,
            messages.NamedMessage("test-code", ""),
        )

        unavailable_resources = (
            {ent.name: ""} if in_inapplicable_resources else {}
        )
        ret = status._attached_service_status(
            ent, unavailable_resources, FakeConfig()
        )

        assert expected_status == ret["status"]

    @pytest.mark.parametrize(
        "blocking_incompatible_services, expected_blocked_by",
        (
            ([], []),
            (
                [
                    EntitlementWithMessage(
                        FIPSEntitlement, messages.NamedMessage("code", "msg")
                    )
                ],
                [{"name": "fips", "reason": "msg", "reason_code": "code"}],
            ),
            (
                [
                    EntitlementWithMessage(
                        FIPSEntitlement, messages.NamedMessage("code", "msg")
                    ),
                    EntitlementWithMessage(
                        ROSEntitlement, messages.NamedMessage("code2", "msg2")
                    ),
                ],
                [
                    {"name": "fips", "reason": "msg", "reason_code": "code"},
                    {"name": "ros", "reason": "msg2", "reason_code": "code2"},
                ],
            ),
        ),
    )
    def test_blocked_by(
        self,
        blocking_incompatible_services,
        expected_blocked_by,
        tmpdir,
        FakeConfig,
    ):
        cfg = FakeConfig()
        ent = ConcreteTestEntitlement(
            cfg=cfg,
            blocking_incompatible_services=blocking_incompatible_services,
        )
        service_status = status._attached_service_status(ent, [], cfg)
        assert service_status["blocked_by"] == expected_blocked_by
