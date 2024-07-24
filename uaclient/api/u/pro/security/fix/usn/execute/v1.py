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
        Field(
            "usns",
            data_list(StringDataValue),
            doc="A list of USNs (i.e. USN-6188-1) titles",
        ),
    ]

    def __init__(self, usns: List[str]):
        self.usns = usns


class FixExecuteUSNResult(DataObject):
    fields = [
        Field(
            "target_usn",
            FixExecuteResult,
            doc="The ``FixExecuteResult`` for the target USN",
        ),
        Field(
            "related_usns",
            data_list(FixExecuteResult),
            required=False,
            doc="A list of ``FixExecuteResult`` objects for the related USNs",
        ),
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
        Field("status", StringDataValue, doc="The status of fixing the USNs"),
        Field(
            "usns",
            data_list(FixExecuteUSNResult),
            doc="A list of ``FixExecuteUSNResult`` objects",
        ),
    ]

    def __init__(self, status: str, usns: List[FixExecuteUSNResult]):
        self.status = status
        self.usns = usns


class USNSAPIFixExecuteResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "usns_data",
            USNAPIFixExecuteResult,
            doc="A list of ``USNAPIFixExecuteResult`` objects",
        )
    ]

    def __init__(self, usns_data: USNAPIFixExecuteResult):
        self.usns_data = usns_data


def execute(options: USNFixExecuteOptions) -> USNSAPIFixExecuteResult:
    return _execute(options, UAConfig())


def _execute(
    options: USNFixExecuteOptions, cfg: UAConfig
) -> USNSAPIFixExecuteResult:
    """
    This endpoint fixes the specified USNs on the machine.
    """
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

_doc = {
    "introduced_in": "30",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.fix.usn.execute.v1 import execute, USNFixExecuteOptions

options = USNFixExecuteOptions(usns=["USN-1234-1", "USN-1235-1"])
result = execute(options)
""",  # noqa: E501
    "result_class": USNSAPIFixExecuteResult,
    "exceptions": [],
    "example_cli": """pro api u.pro.security.fix.usn.execute.v1 --data '{"usns": ["USN-1234-1", "USN-1235-1"]}'""",  # noqa: E501
    "example_json": """
{
    "usns_data": {
        "status": "fixed",
        "usns": [
            {
                "target_usn": {
                    "title": "CVE-1234-56789",
                    "status": "fixed",
                    "upgraded_packages": {
                        "name": "pkg1",
                        "version": "1.1",
                        "pocket": "standard-updates"
                    },
                    "error": null
                },
                "related_usns": []
            }
        ]
    }
}
""",
    "extra": """
.. tab-item:: Explanation
    :sync: explanation

    When using the USN endpoint, the expected output is as follows:

    .. code-block:: json

        {
            "usns_data": {
                "status": "fixed",
                "usns": [
                    {
                        "target_usn": {
                            "title": "CVE-1234-56789",
                            "status": "fixed",
                            "upgraded_packages": {
                                "name": "pkg1",
                                "version": "1.1",
                                "pocket": "standard-updates"
                            },
                            "error": null
                        },
                        "related_usns": []
                    }
                ]
            }
        }

    From this output, we can see that the **usns_data** object contains two
    attributes:

    * **usns**: A list of USN objects detailing what happened during the fix
      operation.
    * **status**: The status of the fix operation considering **all** USNs.
      This means that if one USN cannot be fixed, this field will reflect that.
      Note that related USNs don't interfere with this attribute, meaning that
      a related USN can fail to be fixed without modifying the **status**
      value.

    Each **usn** object contains a reference for both **target_usn** and
    **related_usns**. The target is the USN requested to be fixed by the user,
    while related USNs are USNs that are related to the main USN and an
    attempt to fix them will be performed by the endpoint too. To better
    understand that distinction, please refer to
    :ref:`our explanation of CVEs and USNs <expl-cve-usn>`.

    With that said both **target_usn** object and any object from
    **related_usns** follow this structure:

    * **title**: The title of the USN.
    * **description**: The USN description.
    * **error**: Any error captured when fixing the USN will appear here. The
      error object will be detailed in a following section.
    * **status**: The expected status of the USN after the fix operation.
      There are three possible scenarios: **fixed**, **still-affected** and
      **not-affected**. The system is considered **still-affected** if there
      is something that prevents any required packages from being upgraded.
      The system is considered **not-affected** if the USN doesn't affect the
      system at all.
    * **upgraded_packages**: A list of UpgradedPackage objects referencing each
      package that was upgraded during the fix operation. The UpgradedPackage
      object always contain the **name** of the package, the **version** it was
      upgraded to and the **pocket** where the package upgrade came from.

    **What errors can be generated?**

    There some errors that can happen when executing this endpoint. For
    example, the system might require the user to attach to a Pro subscription
    to install the upgrades, or the user might run the command as non-root
    when a package upgrade is needed.

    In those situations, the error JSON error object will follow this
    representation:

    .. code-block:: json

        {
            "error_type": "error-type",
            "reason": "reason",
            "failed_upgrades": [
                {
                    "name": "pkg1",
                    "pocket": "esm-infra"
                }
            ]
        }

    We can see that the representation has the following fields:

    * **error_type**: The error type
    * **reason**: The explanation of why the error happened
    * **failed_upgrade**: A list of objects that always contain the name of the
      package that was not upgraded and the pocket where the upgrade would have
      come from.
""",
}
