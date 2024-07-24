from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.fix._common import get_expected_overall_status

# Some of these imports are intentionally not used in this module.
# The rationale is that we want users to import such Data Objects
# directly from the associated endpoints and not through the _common module
from uaclient.api.u.pro.security.fix._common.plan.v1 import (  # noqa: F401
    AdditionalData,
    AptUpgradeData,
    AttachData,
    EnableData,
    FixPlanError,
    FixPlanResult,
    FixPlanStep,
    FixPlanUSNResult,
    FixPlanWarning,
    NoOpAlreadyFixedData,
    NoOpData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    USNAdditionalData,
    fix_plan_usn,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class USNFixPlanOptions(DataObject):
    fields = [
        Field(
            "usns",
            data_list(StringDataValue),
            doc="A list of USNs (i.e. USN-6119-1) titles",
        ),
    ]

    def __init__(self, usns: List[str]):
        self.usns = usns


class USNFixPlanResult(DataObject):
    fields = [
        Field(
            "expected_status",
            StringDataValue,
            doc="The expected status of fixing the USNs",
        ),
        Field(
            "usns",
            data_list(FixPlanUSNResult),
            doc="A list of ``FixPlanUSNResult`` objects",
        ),
    ]

    def __init__(self, *, expected_status: str, usns: List[FixPlanUSNResult]):
        self.expected_status = expected_status
        self.usns = usns


class USNSFixPlanResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "usns_data",
            USNFixPlanResult,
            doc="A list of ``USNFixPlanResult`` objects",
        ),
    ]

    def __init__(self, *, usns_data: USNFixPlanResult):
        self.usns_data = usns_data


def plan(options: USNFixPlanOptions) -> USNSFixPlanResult:
    return _plan(options, UAConfig())


def _plan(options: USNFixPlanOptions, cfg: UAConfig) -> USNSFixPlanResult:
    """
    This endpoint shows the necessary steps required to fix USNs in the system
    without executing any of those steps.
    """
    usns = []  # type: List[FixPlanUSNResult]
    expected_status = ""
    for usn in options.usns:
        usn_plan = fix_plan_usn(usn, cfg=cfg)
        expected_status = get_expected_overall_status(
            expected_status, usn_plan.target_usn_plan.expected_status
        )
        usns.append(usn_plan)

    return USNSFixPlanResult(
        usns_data=USNFixPlanResult(
            expected_status=expected_status,
            usns=usns,
        )
    )


endpoint = APIEndpoint(
    version="v1",
    name="USNFixPlan",
    fn=_plan,
    options_cls=USNFixPlanOptions,
)

_doc = {
    "introduced_in": "29",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.fix.usn.plan.v1 import plan, USNFixPlanOptions

options = USNFixPlanOptions(cves=["USN-1234-1", "USN-1235-1"])
result = plan(options)
""",  # noqa: E501
    "result_class": USNSFixPlanResult,
    "ignore_result_classes": [DataObject, AdditionalData],
    "extra_result_classes": [
        USNAdditionalData,
        AptUpgradeData,
        AttachData,
        EnableData,
        NoOpData,
        NoOpAlreadyFixedData,
        PackageCannotBeInstalledData,
        SecurityIssueNotFixedData,
    ],
    "exceptions": [],
    "example_cli": """pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-1234-1", "USN-1235-1"]}'""",  # noqa: E501
    "example_json": """
{
    "usns_data": {
        "expected_status": "fixed",
        "usns": [
            {
                "related_usns_plan": [],
                "target_usn_plan": {
                    "title": "USN-1234-5",
                    "expected_status": "fixed",
                    "plan": [
                        {
                            "operation": "apt-upgrade",
                            "order": 1,
                            "data": {
                                "binary_packages": ["pkg1"],
                                "source_packages": ["pkg1"],
                                "pocket": "standard-updates"
                            }
                        }
                    ],
                    "warnings": [],
                    "error": null,
                    "additional_data": {
                        "associated_cves": [
                            "CVE-1234-56789"
                        ],
                        "associated_launchpad_bus": [
                            "https://launchpad.net/bugs/BUG_ID"
                        ]
                    }
                },
            }
        ]
    }
}
""",
}
