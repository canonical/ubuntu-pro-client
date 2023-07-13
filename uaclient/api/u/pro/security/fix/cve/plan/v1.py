# from uaclient.api.api import APIEndpoint
# from uaclient.config import UAConfig
# from uaclient.api.data_types import AdditionalInfo
# from uaclient.data_types import DataObject, Field, StringDataValue, data_list
# from uaclient.fix import fix_plan, FixPlanResult
#
#
# class CVEFixPlanResult(DataObject):
#     fields = [
#         Field("expected_status", StringDataValue),
#         Field("cves", data_list(FixPlanResult)),
#     ]
#
#
# class CVESFixPlanResult(DataObject, AdditionalInfo):
#     fields = [
#         Field("cves_data", CVEFixPlanResult),
#     ]
#
#     def __init__(self, *, cves_data: CVEFixPlanResult):
#         self.cves_data = cves_data
