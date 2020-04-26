import datetime

from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class PanoraysFinding(SmartJsonClass):
    status = Field(str, 'Status')
    severity = Field(str, 'Severity')
    category = Field(str, 'Category')
    sub_category = Field(str, 'Sub Category')
    description = Field(str, 'Description')
    finding_text = Field(str, 'Finding Text')
    criterion_text = Field(str, 'Criterion Text')
    insert_time = Field(datetime.datetime, 'Insert Time')
    update_time = Field(datetime.datetime, 'Update Time')


class PanoraysDeviceInstance(DeviceAdapter):
    is_up = Field(bool, 'Is Up')
    asset_type = Field(str, 'Asset Type')
    findings_data = ListField(PanoraysFinding, 'Findings Data')
