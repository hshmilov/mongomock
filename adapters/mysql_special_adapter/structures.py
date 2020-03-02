import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass

# pylint: disable=too-many-instance-attributes


class HostDevices(SmartJsonClass):
    p_key = Field(int, 'Public Key')
    uuid = Field(str, 'UUID')
    cpumhz = Field(int, 'CPU MHz')
    cpu_model = Field(str, 'CPU Model')
    box_model = Field(str, 'Box Model')
    nic_count = Field(int, 'NIC Count')
    moref = Field(str, 'Moref')
    vcenter = Field(str, 'VCenter')
    scrapedate = Field(datetime.datetime, 'Scrape Date')
    data_center = Field(str, 'Data Center')
    esxi_version = Field(str, 'Esxi Version')
    build = Field(str, 'Build')
    on_vsan = Field(str, 'On Vsan')
    cluster = Field(str, 'Cluster')
    vms = ListField(str, 'Vms UUID')


class CrawlerDevices(SmartJsonClass):
    p_key = Field(int, 'Public Key')
    vcenter = Field(str, 'Vcenter')
    path = Field(str, 'Path')
    uuid = Field(str, 'UUID')
    guest_id = Field(str, 'Guest id')
    guest_state = Field(str, 'Guest State')
    tools_running_status = Field(str, 'Tools Running Status')
    tools_version = Field(str, 'Tools Version')
    tools_version_status2 = Field(str, 'Tools Version Status2')
    disk = Field(int, 'Disk')
    bu_build = Field(str, 'BU')
    scrape_date = Field(datetime.datetime, 'Scrape Date')
    shasum = Field(str, 'Sha Sum')
    moref = Field(str, 'Moref')
    vmx_path = Field(str, 'Vmx Path')
    host_uuid = Field(str, 'Host UUID')
    data_stores = Field(str, 'Data Stores')
    v_san = Field(int, 'vSAN')
    host_machine = Field(str, 'Host Machine UUID')
