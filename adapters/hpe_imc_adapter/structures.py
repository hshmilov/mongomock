import datetime
import logging

from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter

logger = logging.getLogger(f'axonius.{__name__}')


def _login_method_dict():
    return {
        0: 'None',
        1: 'Telnet',
        2: 'SSH'
    }


def _status_dict():
    return {
        -1: 'Unmanaged',
        0: 'Unknown',
        1: 'Normal',
        2: 'Alarm',
        3: 'Minor',
        4: 'Major',
        5: 'Warning'
    }


def parse_login_method(login_method: int):
    return _login_method_dict().get(login_method)


def parse_status(status_id: int):
    return _status_dict().get(status_id)


def parse_int(value):
    # handle already-integers (including 0)
    if isinstance(value, int):
        return value
    # handle nones or empties
    if not value:
        return None
    # handle strings
    try:
        return int(value)
    except Exception as e:
        logger.warning(f'Failed to parse {value} as int: {str(e)}')
        return None


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return None


class HpeImcDeviceInstance(DeviceAdapter):
    label = Field(str, 'Label')
    status = Field(str, 'Status', enum=list(_status_dict().values()))
    status_raw = Field(int, 'Status (raw)', enum=list(_status_dict().keys()))
    contact = Field(str, 'Contact')
    sys_oid = Field(str, 'System OID')
    runtime = Field(str, 'Runtime')
    login_method = Field(str, 'Login Method', enum=list(_login_method_dict().values()))
    login_method_raw = Field(int, 'Login Method (raw)', enum=list(_login_method_dict().keys()))
    category_id = Field(int, 'Category ID')
    is_support_ping = Field(bool, 'Supports Ping Operation')
    snmp_template_id = Field(int, 'SNMP Template ID')
    telnet_template_id = Field(int, 'Telnet Template ID')
    ssh_template_id = Field(int, 'SSH Template ID')
    web_mgmt_port = Field(int, 'Low-Level Mgmt Login Port')
    cfg_poll_interval = Field(int, 'Set Polling Interval (min)', description='In Minutes')
    status_poll_interval = Field(int, 'Status Polling Interval (sec)', description='In Seconds')
    type_name = Field(str, 'Device Type Name')
    bin_file = Field(str, 'Bin File')
    verge_net = Field(int, 'Edge Subnet Identifier')
    phy_name = Field(str, 'Physical Name')
    phy_creator = Field(str, 'Physical Creator')
    created_time = Field(datetime.datetime, 'Creation Time')
    append_unicode = Field(str, 'Attached Unicode')
    parent_id = Field(int, 'Parent Symbol ID')
    children = Field(int, 'Children Count')


class HpeImcUserInstance(UserAdapter):
    ss_type = Field(int, 'Self-Service Account Activation', description='1=active, 2=inactive', enum=[1, 2])
