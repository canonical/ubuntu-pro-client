from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.fix._common import get_expected_overall_status

# Some of these imports are intentionally not used in this module.
# The rationale is that we want users to import such Data Objects
# directly from the associated endpoints and not through the _common module
from uaclient.api.u.pro.security.fix._common.plan.v1 import (  # noqa: F401
    AptUpgradeData,
    AttachData,
    EnableData,
    FixPlanError,
    FixPlanResult,
    FixPlanStep,
    FixPlanWarning,
    NoOpAlreadyFixedData,
    NoOpData,
    NoOpLivepatchFixData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    fix_plan_cve,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class CVEFixPlanOptions(DataObject):
    fields = [
        Field(
            "cves",
            data_list(StringDataValue),
            doc="A list of CVE (i.e. CVE-2023-2650) titles",
        ),
    ]

    def __init__(self, cves: List[str]):
        self.cves = cves


class CVEFixPlanResult(DataObject):
    fields = [
        Field(
            "expected_status",
            StringDataValue,
            doc="The expected status of fixing the CVEs",
        ),
        Field(
            "cves",
            data_list(FixPlanResult),
            doc="A list of ``FixPlanResult`` objects",
        ),
    ]

    def __init__(self, *, expected_status: str, cves: List[FixPlanResult]):
        self.expected_status = expected_status
        self.cves = cves


class CVESFixPlanResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "cves_data",
            CVEFixPlanResult,
            doc="A list of ``CVEFixPlanResult`` objects",
        ),
    ]

    def __init__(self, *, cves_data: CVEFixPlanResult):
        self.cves_data = cves_data


def plan(options: CVEFixPlanOptions) -> CVESFixPlanResult:
    return _plan(options, UAConfig())


def _plan(options: CVEFixPlanOptions, cfg: UAConfig) -> CVESFixPlanResult:
    """
    This endpoint shows the necessary steps required to fix CVEs in the system
    without executing any of those steps.
    """
    cves = []  # type: List[FixPlanResult]
    expected_status = ""
    for cve in options.cves:
        cve_plan = fix_plan_cve(cve, cfg=cfg)
        expected_status = get_expected_overall_status(
            expected_status, cve_plan.expected_status
        )
        cves.append(cve_plan)

    return CVESFixPlanResult(
        cves_data=CVEFixPlanResult(
            expected_status=expected_status,
            cves=cves,
        )
    )


endpoint = APIEndpoint(
    version="v1",
    name="CVEFixPlan",
    fn=_plan,
    options_cls=CVEFixPlanOptions,
)
_doc = {
    "introduced_in": "29",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.fix.cve.plan.v1 import plan, CVEFixPlanOptions

options = CVEFixPlanOptions(cves=["CVE-1234-1234", "CVE-1234-1235"])
result = plan(options)
""",  # noqa: E501
    "result_class": CVESFixPlanResult,
    "ignore_result_classes": [DataObject],
    "extra_result_classes": [
        AptUpgradeData,
        AttachData,
        EnableData,
        NoOpData,
        NoOpAlreadyFixedData,
        NoOpLivepatchFixData,
        PackageCannotBeInstalledData,
        SecurityIssueNotFixedData,
    ],
    "exceptions": [],
    "example_cli": """pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-1234-56789", "CVE-1234-1235"]}'""",  # noqa: E501
    "example_json": """
{
    "cves_data": {
        "expected_status": "fixed",
        "cves": [
            {
                "title": "CVE-1234-56789",
                "expected_status": "fixed",
                "plan": [
                    {
                        "operation": "apt-upgrade",
                        "order": 1,
                        "data": {
                            "binary_packages": ["pkg1"],
                            "source_packages": ["pkg1"],
                            "pocket": "standard-updates",
                        }
                    }
                ],
                "warnings": [],
                "error": null,
                "additional_data": {}
            }
        ]
    }
}
""",
}
