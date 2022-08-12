from typing import List, Optional

from uaclient.data_types import (
    BoolDataValue,
    DataObject,
    Field,
    IntDataValue,
    StringDataValue,
    data_list,
)


class ActivityInfo(DataObject):
    fields = [
        Field("activityID", StringDataValue, False),
        Field("activityToken", StringDataValue, False),
        Field("activityPingInterval", IntDataValue, False),
        Field("resources", data_list(StringDataValue), False),
    ]

    def __init__(
        self,
        activityID: Optional[str],
        activityToken: Optional[str],
        activityPingInterval: Optional[int],
        resources: Optional[List[str]],
    ):
        self.activityID = activityID
        self.activityPingInterval = activityPingInterval
        self.activityToken = activityToken
        self.resources = resources


class AvailableResource(DataObject):
    fields = [
        Field("available", BoolDataValue, False),
        Field("name", StringDataValue, False),
        Field("description", StringDataValue, False),
        Field("presentedAs", StringDataValue, False),
    ]

    def __init__(
        self,
        available: Optional[bool],
        name: Optional[str],
        description: Optional[str],
        presentedAs: Optional[str],
    ):
        self.available = available
        self.name = name
        self.description = description
        self.presentedAs = presentedAs


class ExternalID(DataObject):
    fields = [
        Field("origin", StringDataValue, False),
        Field("IDs", data_list(StringDataValue), False),
    ]

    def __init__(self, origin: Optional[str], IDs: Optional[List[str]]):
        self.origin = origin
        self.IDs = IDs


class AccountInfo(DataObject):
    fields = [
        Field("name", StringDataValue, False),
        Field("id", StringDataValue, False),
        Field("createdAt", StringDataValue, False),
        Field("type", StringDataValue, False),
        Field("userRoleOnAccount", StringDataValue, False),
        Field("externalAccountIDs", data_list(ExternalID), False),
    ]

    def __init__(
        self,
        name: Optional[str],
        id: Optional[str],
        createdAt: Optional[str],
        type: Optional[str],
        userRoleOnAccount: Optional[str],
        externalAccountIDs: Optional[List[str]],
    ):
        self.name = name
        self.id = id
        self.createdAt = createdAt
        self.type = type
        self.userRoleOnAccount = userRoleOnAccount
        self.externalAccountIDs = externalAccountIDs


class Affordances(DataObject):
    fields = [
        Field("architectures", data_list(StringDataValue), False),
        Field("presentedAs", StringDataValue, False),
        Field("series", data_list(StringDataValue), False),
        Field("kernelFlavors", data_list(StringDataValue), False),
        Field("minKernelVersion", StringDataValue, False),
        Field("tier", StringDataValue, False),
        Field("supportLevel", StringDataValue, False),
    ]

    def __init__(
        self,
        architectures: Optional[List[str]],
        presentedAs: Optional[str],
        series: List[Optional[str]],
        kernelFlavors: List[Optional[str]],
        minKernelVersion: Optional[str],
        tier: Optional[str],
        supportLevel: Optional[str],
    ):
        self.architectures = architectures
        self.presentedAs = presentedAs
        self.series = series
        self.kernelFlavors = kernelFlavors
        self.minKernelVersion = minKernelVersion
        self.tier = tier
        self.supportLevel = supportLevel


class Obligations(DataObject):
    fields = [
        Field("enableByDefault", BoolDataValue, False),
        Field("additionalProperties", StringDataValue, False),
    ]

    def __init__(
        self,
        enableByDefault: Optional[bool],
        additionalProperties: Optional[str],
    ):
        self.enableByDefault = enableByDefault
        self.additionalProperties = additionalProperties


class Directives(DataObject):
    fields = [
        Field("additionalPackages", data_list(StringDataValue), False),
        Field("aptURL", StringDataValue, False),
        Field("suites", data_list(StringDataValue), False),
        Field("server", StringDataValue, False),
        Field("remoteServer", StringDataValue, False),
        Field("caCerts", StringDataValue, False),
        Field("snapChannel", StringDataValue, False),
        Field("pypiURL", StringDataValue, False),
        Field("url", StringDataValue, False),
    ]

    def __init__(
        self,
        additionalPackages: Optional[List[str]],
        aptURL: Optional[str],
        suites: Optional[List[str]],
        server: Optional[str],
        remoteServer: Optional[str],
        caCerts: Optional[str],
        snapChannel: Optional[str],
        pypiURL: Optional[str],
        url: Optional[str],
    ):
        self.additionalPackages = additionalPackages
        self.aptURL = aptURL
        self.suites = suites
        self.server = server
        self.remoteServer = remoteServer
        self.caCerts = caCerts
        self.snapChannel = snapChannel
        self.pypiURL = pypiURL
        self.url = url


class OverrideSelector(DataObject):
    fields = [
        Field("series", StringDataValue, False),
        Field("cloud", StringDataValue, False),
    ]

    def __init__(
        self,
        series: Optional[str],
        cloud: Optional[str],
    ):
        self.series = series
        self.cloud = cloud


class Override(DataObject):
    fields = [
        Field("selector", OverrideSelector, False),
        Field("affordances", Affordances, False),
        Field("obligations", Obligations, False),
        Field("directives", Directives, False),
    ]

    def __init__(
        self,
        selector: Optional[OverrideSelector],
        affordances: Optional[Affordances],
        obligations: Optional[Obligations],
        directives: Optional[Directives],
    ):
        self.selector = selector
        self.affordances = affordances
        self.obligations = obligations
        self.directives = directives


class Entitlement(DataObject):
    fields = [
        Field("entitled", BoolDataValue, False),
        Field("type", StringDataValue, False),
        Field("affordances", Affordances, False),
        Field("obligations", Obligations, False),
        Field("directives", Directives, False),
        Field("overrides", data_list(Override), False),
    ]

    def __init__(
        self,
        entitled: Optional[bool],
        type: Optional[str],
        affordances: Optional[Affordances],
        obligations: Optional[Obligations],
        directives: Optional[Directives],
        overrides: Optional[List[Override]],
    ):
        self.entitled = entitled
        self.type = type
        self.affordances = affordances
        self.obligations = obligations
        self.directives = directives
        self.overrides = overrides


class ContractInfo(DataObject):
    fields = [
        Field("name", StringDataValue, False),
        Field("id", StringDataValue, False),
        Field("createdAt", StringDataValue, False),
        Field("createdBy", StringDataValue, False),
        Field("resourceEntitlements", data_list(Entitlement), False),
        Field("specificResourceEntitlements", data_list(Entitlement), False),
        Field("effectiveFrom", StringDataValue, False),
        Field("effectiveTo", StringDataValue, False),
        Field("products", data_list(StringDataValue), False),
        Field("origin", StringDataValue, False),
    ]

    def __init__(
        self,
        name: Optional[str],
        id: Optional[str],
        createdAt: Optional[str],
        createdBy: Optional[str],
        resourceEntitlements: Optional[List[Entitlement]],
        specificResourceEntitlements: Optional[List[Entitlement]],
        effectiveFrom: Optional[str],
        effectiveTo: Optional[str],
        products: Optional[List[str]],
        origin: Optional[str],
    ):
        self.name = name
        self.id = id
        self.createdAt = createdAt
        self.createdBy = createdBy
        self.resourceEntitlements = resourceEntitlements
        self.specificResourceEntitlements = specificResourceEntitlements
        self.effectiveFrom = effectiveFrom
        self.effectiveTo = effectiveTo
        self.products = products
        self.origin = origin


class MachineTokenInfo(DataObject):
    fields = [
        Field("machineId", StringDataValue, False),
        Field("accountInfo", AccountInfo, False),
        Field("contractInfo", ContractInfo, False),
        Field("expires", StringDataValue, False),
    ]

    def __init__(
        self,
        machineId: Optional[str],
        accountInfo: Optional[AccountInfo],
        contractInfo: Optional[ContractInfo],
        expires: Optional[str],
    ):
        self.machineId = machineId
        self.accountInfo = accountInfo
        self.contractInfo = contractInfo
        self.expires = expires


class PublicMachineTokenData(DataObject):
    fields = [
        Field("activityInfo", ActivityInfo, False),
        Field("machineTokenInfo", MachineTokenInfo, False),
        Field("availableResources", data_list(AvailableResource), False),
    ]

    def __init__(
        self,
        activityInfo: Optional[ActivityInfo],
        machineTokenInfo: Optional[MachineTokenInfo],
        availableResources: Optional[List[AvailableResource]],
    ):
        self.activityInfo = activityInfo
        self.availableResources = availableResources
        self.machineTokenInfo = machineTokenInfo
