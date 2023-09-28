from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.fix._common import get_expected_overall_status
from uaclient.api.u.pro.security.fix._common.execute.v1 import (
    FixExecuteResult,
    _execute_fix,
)
from uaclient.api.u.pro.security.fix.cve.plan.v1 import (
    CVEFixPlanOptions,
    _plan,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.security import FixStatus


class CVEFixExecuteOptions(DataObject):
    fields = [
        Field("cves", data_list(StringDataValue)),
    ]

    def __init__(self, cves: List[str]):
        self.cves = cves


class CVEAPIFixExecuteResult(DataObject):
    fields = [
        Field("status", StringDataValue),
        Field("cves", data_list(FixExecuteResult)),
    ]

    def __init__(self, status: str, cves: List[FixExecuteResult]):
        self.status = status
        self.cves = cves


class CVESAPIFixExecuteResult(DataObject, AdditionalInfo):
    fields = [Field("cves_data", CVEAPIFixExecuteResult)]

    def __init__(self, cves_data: CVEAPIFixExecuteResult):
        self.cves_data = cves_data


def execute(options: CVEFixExecuteOptions) -> CVESAPIFixExecuteResult:
    return _execute(options, UAConfig())


def _execute(
    options: CVEFixExecuteOptions, cfg: UAConfig
) -> CVESAPIFixExecuteResult:
    fix_plan = _plan(CVEFixPlanOptions(cves=options.cves), cfg=cfg)
    cves_result = []  # type: List[FixExecuteResult]
    all_cves_status = FixStatus.SYSTEM_NOT_AFFECTED.value.msg

    for cve in fix_plan.cves_data.cves:
        cve_result = _execute_fix(cve)

        all_cves_status = get_expected_overall_status(
            all_cves_status, cve_result.status
        )
        cves_result.append(cve_result)

    return CVESAPIFixExecuteResult(
        cves_data=CVEAPIFixExecuteResult(
            status=all_cves_status, cves=cves_result
        )
    )


endpoint = APIEndpoint(
    version="v1",
    name="CVEFixExecute",
    fn=_execute,
    options_cls=CVEFixExecuteOptions,
)
