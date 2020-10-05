from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class ResolutionData(SmartJsonClass):
    response_type = Field(str, 'Response Type')
    response_data = Field(str, 'Response Data')


class IntrigueDeviceInstance(DeviceAdapter):
    net_name = Field(str, 'Net Name')
    resolutions = ListField(ResolutionData, 'Resolutions')
    continent = Field(str, 'Continent')
    country = Field(str, 'Country')
    city = Field(str, 'City')
    subdivisions = ListField(str, 'Subdivisions')
    scoped = Field(bool, 'Scoped')
    hidden = Field(bool, 'Hidden')
