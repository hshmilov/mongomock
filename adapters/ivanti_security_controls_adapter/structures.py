from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


class Policy(SmartJsonClass):
    id = Field(str, 'ID')
    name = Field(str, 'Name')
    cancel_operation = Field(bool, 'Allow Cancel Operations')
    manual_operation = Field(bool, 'Allow Manually Initiate Tasks')
    check_in = Field(str, 'Console Check In', enum=['Unknown', 'Minutes', 'Days'])
    days_check_in = Field(int, 'Days Interval')
    minutes_check_in = Field(int, 'Minutes Interval')
    internet_proxy = Field(str, 'Proxy ID')
    listen_port = Field(int, 'Agent Listen Port')


class IvantiSecurityControlsDeviceInstance(DeviceAdapter):
    listening = Field(bool, 'Listening')
    assigned_policy_id = Field(str, 'Assigned Policy ID')
    report_policy_id = Field(str, 'Report Policy ID')
    policy = Field(Policy, 'Policy')
    status = Field(str, 'Status')
