from enum import auto

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import ListField
from mockingbird.commons.mock_network_entity import MockNetworkEntity, MockNetworkEntityProperties


class MockNetworkDeviceProperties(MockNetworkEntityProperties):
    ADDevice = auto()
    NoGeneralInfo = auto()
    AWSDevice = auto()
    AzureDevice = auto()
    ChefDevice = auto()
    EpoDevice = auto()
    EsxDevice = auto()
    GCEDevice = auto()
    HyperVDevice = auto()
    IllusiveDevice = auto()
    MobileironDevice = auto()
    PuppetDevice = auto()
    QualysScansDevice = auto()
    SccmDevice = auto()
    SplunkDevice = auto()
    TaniumDevice = auto()
    CarbonBlackResponseDevice = auto()
    CiscoMerakiDevice = auto()
    CounteractDevice = auto()
    TenableSC = auto()
    EclypsiumDevice = auto()


class MockNetworkDevice(DeviceAdapter, MockNetworkEntity):
    properties = ListField(MockNetworkDeviceProperties)
