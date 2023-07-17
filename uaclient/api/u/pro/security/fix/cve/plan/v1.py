from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.fix import FixPlanResult, fix_plan_cve
from uaclient.security import FixStatus


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


def _get_expected_overall_status(current_status: str, cve_status: str) -> str:
    if not current_status:
        return cve_status

    if cve_status in (
        FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
        FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
    ):
        if (
            current_status == FixStatus.SYSTEM_NOT_AFFECTED.value.msg
            and current_status != cve_status
        ):
            return cve_status
        else:
            return current_status
    else:
        # This means the system is still affected and we must
        # priotize this as the global state
        return cve_status


def plan(options: CVEFixPlanOptions) -> CVESFixPlanResult:
    return _plan(options, UAConfig())


def _plan(options: CVEFixPlanOptions, cfg: UAConfig) -> CVESFixPlanResult:
    cves = []  # type: List[FixPlanResult]
    expected_status = ""
    for cve in options.cves:
        cve_plan = fix_plan_cve(cve, cfg=cfg)
        expected_status = _get_expected_overall_status(
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
