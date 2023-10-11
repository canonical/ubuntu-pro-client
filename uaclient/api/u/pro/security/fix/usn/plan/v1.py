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
    FixPlanUSNResult,
    FixPlanWarning,
    NoOpData,
    PackageCannotBeInstalledData,
    SecurityIssueNotFixedData,
    fix_plan_usn,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class USNFixPlanOptions(DataObject):
    fields = [
        Field("usns", data_list(StringDataValue)),
    ]

    def __init__(self, usns: List[str]):
        self.usns = usns


class USNFixPlanResult(DataObject):
    fields = [
        Field("expected_status", StringDataValue),
        Field("usns", data_list(FixPlanUSNResult)),
    ]

    def __init__(self, *, expected_status: str, usns: List[FixPlanUSNResult]):
        self.expected_status = expected_status
        self.usns = usns


class USNSFixPlanResult(DataObject, AdditionalInfo):
    fields = [
        Field("usns_data", USNFixPlanResult),
    ]

    def __init__(self, *, usns_data: USNFixPlanResult):
        self.usns_data = usns_data


def plan(options: USNFixPlanOptions) -> USNSFixPlanResult:
    return _plan(options, UAConfig())


def _plan(options: USNFixPlanOptions, cfg: UAConfig) -> USNSFixPlanResult:
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
