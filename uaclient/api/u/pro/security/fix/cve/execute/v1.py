from typing import List

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
from uaclient.api.u.pro.security.fix.cve.plan.v1 import (
    CVEFixPlanOptions,
    _plan,
)
from uaclient.config import UAConfig
from uaclient.data_types import DataObject, Field, StringDataValue, data_list


class CVEFixExecuteOptions(DataObject):
    fields = [
        Field(
            "cves",
            data_list(StringDataValue),
            doc="A list of CVE (i.e. CVE-2023-2650) titles",
        ),
    ]

    def __init__(self, cves: List[str]):
        self.cves = cves


class CVEAPIFixExecuteResult(DataObject):
    fields = [
        Field("status", StringDataValue, doc="The status of fixing the CVEs"),
        Field(
            "cves",
            data_list(FixExecuteResult),
            doc="A list of ``FixExecuteResult`` objects",
        ),
    ]

    def __init__(self, status: str, cves: List[FixExecuteResult]):
        self.status = status
        self.cves = cves


class CVESAPIFixExecuteResult(DataObject, AdditionalInfo):
    fields = [
        Field(
            "cves_data",
            CVEAPIFixExecuteResult,
            doc="A list of ``CVEAPIFixExecuteResult`` objects",
        )
    ]

    def __init__(self, cves_data: CVEAPIFixExecuteResult):
        self.cves_data = cves_data


def execute(options: CVEFixExecuteOptions) -> CVESAPIFixExecuteResult:
    return _execute(options, UAConfig())


def _execute(
    options: CVEFixExecuteOptions, cfg: UAConfig
) -> CVESAPIFixExecuteResult:
    """
    This endpoint fixes the specified CVEs on the machine.
    """
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

_doc = {
    "introduced_in": "30",
    "requires_network": True,
    "example_python": """
from uaclient.api.u.pro.security.fix.cve.execute.v1 import execute, CVEFixExecuteOptions

options = CVEFixExecuteOptions(cves=["CVE-1234-1234", "CVE-1234-1235"])
result = execute(options)
""",  # noqa: E501
    "result_class": CVESAPIFixExecuteResult,
    "exceptions": [],
    "example_cli": """pro api u.pro.security.fix.cve.execute.v1 --data '{"cves": ["CVE-1234-1234", "CVE-1234-1235"]}'""",  # noqa: E501
    "example_json": """
{
    "cves_data": {
        "status": "fixed",
        "cves": [
            {
                "title": "CVE-1234-56789",
                "description": "..."
                "status": "fixed",
                "upgraded_packages": {
                    "name": "pkg1",
                    "version": "1.1",
                    "pocket": "standard-updates"
                },
                "errors": []
            }
        ]
    }
}
""",
    "extra": """
.. tab-item:: Explanation
    :sync: explanation

    When using the CVE endpoint, the expected output is as follows:

    .. code-block:: json

        {
            "_schema_version": "v1",
            "data": {
                "attributes": {
                    "cves_data": {
                        "cves": [
                            {
                                "description": "description",
                                "errors": null,
                                "status": "fixed",
                                "title": "CVE-2021-27135",
                                "upgraded_packages": [
                                    {
                                        "name": "xterm",
                                        "pocket": "standard-updates",
                                        "version": "VERSION"
                                    }
                                ]
                            }
                        ],
                        "status": "fixed"
                    }
                },
                "meta": {
                    "environment_vars": []
                },
                "type": "CVEFixExecute"
            },
            "errors": [],
            "result": "success",
            "version": "30",
            "warnings": []
        }

    From this output, we can see that the **cves_data** object contains two
    attributes:

    * **cves**: A list of CVE objects detailing what happened during the fix
      operation.
    * **status**: The status of the fix operation considering **all** CVEs.
      This means that if one CVE cannot be fixed, this field will reflect that.

    If we take a look at a CVE object, we will see the following structure:

    * **title**: The title of the CVE.
    * **description**: The CVE description.
    * **error**: Any error captured when fixing the CVE will appear here. The
      error object will be detailed in a following section.
    * **status**: The expected status of the CVE after the fix operation.
      There are three possible scenarios: **fixed**, **still-affected** and
      **not-affected**. The system is considered **still-affected** if there
      is something that prevents any required packages from being upgraded.
      The system is considered **not-affected** if the CVE doesn't affect the
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
