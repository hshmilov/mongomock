from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter


class SubnetPolicy(SmartJsonClass):
    ip_address = Field(str, 'IP Address')
    id = Field(str, 'ID')
    note = Field(str, 'Note')
    vlan_id = Field(str, 'VLAN ID')
    tunnel_type = Field(str, 'Tunnel Type')


class DeviceInstance(SmartJsonClass):
    group_name = Field(str, 'Group Name')
    group_number = Field(int, 'Group Number')
    is_local_proxy = Field(bool, 'Is Local Proxy')
    is_mobile_client = Field(bool, 'Is Mobile Client')
    note = Field(str, 'Note')
    type = Field(str, 'Device Type')


# pylint: disable=too-many-instance-attributes
class NodeCollection(SmartJsonClass):
    machine_id = Field(str, 'Machine ID')
    account_setting_id = Field(str, 'Account Setting ID')
    node_state = Field(str, 'Node State')
    initializing_message = Field(str, 'Initializing Message')
    product_class = Field(str, 'Product Class')
    product_family = Field(str, 'Product Family')
    communication_type = Field(str, 'Communication Type')
    communicationSelection = Field(str, 'Communication Selection')
    watermark = Field(str, 'Watermark')
    region = Field(str, 'Region')
    asset_type = Field(str, 'Asset Type')
    asset_id = Field(str, 'Asset ID')
    account_name = Field(str, 'Account Name')
    account_priority = Field(int, 'Account Priority')
    public_url = Field(str, 'Public URL')
    type = Field(str, 'Device Type')


class IbossCloudDeviceInstance(DeviceAdapter):
    device_instance = Field(DeviceInstance, 'Device')
    subnet_policies = ListField(SubnetPolicy, 'Subnet Policies')
    node_collection = Field(NodeCollection, 'Node Collection')


class IbossCloudUserInstance(UserAdapter):
    auth_mode = Field(str, 'Authentication Mode')
    note = Field(str, 'Note')
    policy_group = Field(int, 'Policy Group')
    policy_group_name = Field(str, 'Policy Group Name')
