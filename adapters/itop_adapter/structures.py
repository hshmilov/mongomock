import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.smart_json_class import SmartJsonClass


class Ticket(SmartJsonClass):
    ticket_id = Field(str, 'ID')
    ticket_ref = Field(str, 'Ref')
    ticket_title = Field(str, 'Title')
    impact = Field(str, 'Impact')
    impact_code = Field(str, 'Impact Code')
    friendlyname = Field(str, 'Friendly Name')
    ticket_id_friendlyname = Field(str, 'Name')
    ticket_id_finalclass_recall = Field(str, 'Final Class Recall')


class NetworkDevice(SmartJsonClass):
    networkdevice_id = Field(str, 'ID')
    networkdevice_name = Field(str, 'Name')
    network_port = Field(str, 'Network Port')
    device_port = Field(str, 'Device Port')
    connection_type = Field(str, 'Connection Type')
    friendlyname = Field(str, 'Friendly Name')
    networkdevice_id_friendlyname = Field(str, 'NetworkDevice Name')
    obsolescence_flag = Field(str, 'Obsolescence Flag')


class ItopDeviceInstance(DeviceAdapter):
    org_id = Field(str, 'Org ID')
    business_criticity = Field(str, 'Business Criticity')
    move_to_production = Field(str, 'Move To Production')
    location_id = Field(str, 'Location ID')
    status = Field(str, 'Status')
    brand_id = Field(str, 'Brand ID')
    brand_name = Field(str, 'Brand Name')
    model_id = Field(str, 'Model ID')
    asset_number = Field(str, 'Asset Number')
    purchase_date = Field(datetime.datetime, 'Purchase Date')
    end_of_warranty = Field(datetime.datetime, 'End Of Warranty')
    rack_id = Field(str, 'Rack ID')
    rack_name = Field(str, 'Rack Name')
    source = Field(str, 'Source')
    region = Field(str, 'Region')
    zone = Field(str, 'Zone')
    country = Field(str, 'Country')
    obsolescence_date = Field(datetime.datetime, 'Obsolescence Date')
    itop_type = Field(str, 'Type')
    tickets = ListField(Ticket, 'Tickets')
    network_devices = ListField(NetworkDevice, 'Network Devices')


class ItopUserInstance(UserAdapter):
    org_id = Field(str, 'Org ID')
    notify = Field(str, 'Notify')
    function = Field(str, 'Function')
    user_class = Field(str, 'Class')
    obsolescence_date = Field(datetime.datetime, 'Obsolescence Date')
