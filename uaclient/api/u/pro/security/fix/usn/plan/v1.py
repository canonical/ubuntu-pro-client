from typing import List

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list
from uaclient.fix import FixPlanUSNResult, fix_plan_usn
from uaclient.security import FixStatus


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


def _get_expected_overall_status(current_status: str, usn_status: str) -> str:
    if not current_status:
        return usn_status

    if usn_status in (
        FixStatus.SYSTEM_NON_VULNERABLE.value.msg,
        FixStatus.SYSTEM_NOT_AFFECTED.value.msg,
    ):
        if (
            current_status == FixStatus.SYSTEM_NOT_AFFECTED.value.msg
            and current_status != usn_status
        ):
            return usn_status
        else:
            return current_status
    else:
        # This means the system is still affected and we must
        # priotize this as the global state
        return usn_status


def plan(options: USNFixPlanOptions) -> USNSFixPlanResult:
    return _plan(options, UAConfig())


def _plan(options: USNFixPlanOptions, cfg: UAConfig) -> USNSFixPlanResult:
    usns = []  # type: List[FixPlanUSNResult]
    expected_status = ""
    for usn in options.usns:
        usn_plan = fix_plan_usn(usn, cfg=cfg)
        expected_status = _get_expected_overall_status(
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
