from typing import List, Optional

from uaclient.api.api import APIEndpoint
from uaclient.api.data_types import AdditionalInfo
from uaclient.api.u.pro.security.fix._common import (
    FixStatus,
    get_expected_overall_status,
)

# Some of these imports are intentionally not used in this module.
# The rationale is that we want users to import such Data Objects
# directly from the associated endpoints and not through the _common module
from uaclient.api.u.pro.security.fix._common.execute.v1 import (  # noqa: F401
    FailedUpgrade,
    FixExecuteError,
    FixExecuteResult,
    UpgradedPackage,
    _execute_fix,
)
from uaclient.api.u.pro.security.fix.usn.plan.v1 import (
    USNFixPlanOptions,
    _plan,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class USNFixExecuteOptions(DataObject):
    fields = [
        Field("usns", data_list(StringDataValue)),
    ]

    def __init__(self, usns: List[str]):
        self.usns = usns


class FixExecuteUSNResult(DataObject):
    fields = [
        Field("target_usn", FixExecuteResult),
        Field("related_usns", data_list(FixExecuteResult), required=False),
    ]

    def __init__(
        self,
        target_usn: FixExecuteResult,
        related_usns: Optional[List[FixExecuteResult]] = None,
    ):
        self.target_usn = target_usn
        self.related_usns = related_usns


class USNAPIFixExecuteResult(DataObject):
    fields = [
        Field("status", StringDataValue),
        Field("usns", data_list(FixExecuteUSNResult)),
    ]

    def __init__(self, status: str, usns: List[FixExecuteUSNResult]):
        self.status = status
        self.usns = usns


class USNSAPIFixExecuteResult(DataObject, AdditionalInfo):
    fields = [Field("usns_data", USNAPIFixExecuteResult)]

    def __init__(self, usns_data: USNAPIFixExecuteResult):
        self.usns_data = usns_data


def execute(options: USNFixExecuteOptions) -> USNSAPIFixExecuteResult:
    return _execute(options, UAConfig())


def _execute(
    options: USNFixExecuteOptions, cfg: UAConfig
) -> USNSAPIFixExecuteResult:
    fix_plan = _plan(USNFixPlanOptions(usns=options.usns), cfg=cfg)
    usns_result = []  # type: List[FixExecuteUSNResult]
    all_usns_status = FixStatus.SYSTEM_NOT_AFFECTED.value.msg

    for usn in fix_plan.usns_data.usns:
        target_usn_result = _execute_fix(usn.target_usn_plan)

        all_usns_status = get_expected_overall_status(
            all_usns_status, target_usn_result.status
        )

        usn_fix_execute_result = FixExecuteUSNResult(
            target_usn=target_usn_result
        )

        if (
            target_usn_result.status
            != FixStatus.SYSTEM_STILL_VULNERABLE.value.msg
        ):
            related_usns_result = []  # type: List[FixExecuteResult]

            for related_usn in usn.related_usns_plan:
                related_usns_result.append(_execute_fix(related_usn))

            usn_fix_execute_result.related_usns = related_usns_result

        usns_result.append(usn_fix_execute_result)

    return USNSAPIFixExecuteResult(
        usns_data=USNAPIFixExecuteResult(
            status=all_usns_status, usns=usns_result
        )
    )


endpoint = APIEndpoint(
    version="v1",
    name="USNFixExecute",
    fn=_execute,
    options_cls=USNFixExecuteOptions,
)
