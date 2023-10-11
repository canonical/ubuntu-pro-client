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
    NoOpData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    fix_plan_cve,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class CVEFixPlanOptions(DataObject):
    fields = [
        Field("cves", data_list(StringDataValue)),
    ]

    def __init__(self, cves: List[str]):
        self.cves = cves


class CVEFixPlanResult(DataObject):
    fields = [
        Field("expected_status", StringDataValue),
        Field("cves", data_list(FixPlanResult)),
    ]

    def __init__(self, *, expected_status: str, cves: List[FixPlanResult]):
        self.expected_status = expected_status
        self.cves = cves


class CVESFixPlanResult(DataObject, AdditionalInfo):
    fields = [
        Field("cves_data", CVEFixPlanResult),
    ]

    def __init__(self, *, cves_data: CVEFixPlanResult):
        self.cves_data = cves_data


def plan(options: CVEFixPlanOptions) -> CVESFixPlanResult:
    return _plan(options, UAConfig())


def _plan(options: CVEFixPlanOptions, cfg: UAConfig) -> CVESFixPlanResult:
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
