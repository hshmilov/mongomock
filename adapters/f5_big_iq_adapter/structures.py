from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


class DeviceReference(SmartJsonClass):
    id = Field(str, 'ID')
    kind = Field(str, 'Kind')
    link = Field(str, 'Link')
    machine_id = Field(str, 'Machine ID')
    name = Field(str, 'Name')


class ProfileCollectionReference(SmartJsonClass):
    is_sub_collection = Field(bool, 'Sub Collection')
    link = Field(str, 'Link')


class ReferenceInfo(SmartJsonClass):
    id = Field(str, 'ID')
    kind = Field(str, 'Kind')
    link = Field(str, 'Link')
    name = Field(str, 'Name')
    partition = Field(str, 'Partition')


class ClonePool(SmartJsonClass):
    context = Field(str, 'Context')
    pool_reference = Field(ReferenceInfo, 'Pool Reference')


class SourceAddressTranslation(SmartJsonClass):
    snat_pool_reference = Field(ReferenceInfo, 'Snat Pool Reference')
    type = Field(str, 'Type')


class F5BigIqDeviceInstance(DeviceAdapter):
    address_status = Field(str, 'Address Status')
    auto_last_hop = Field(str, 'Automatically Map Last Hop')
    connection_limit = Field(int, 'Connection Limit')
    default_cookie_persistence_reference = Field(str, 'Default Cookie Persistence Reference')
    device_reference = Field(DeviceReference, 'Device Reference')
    fallback_source_addr_persistence_reference = Field(str, 'Fallback Source Address Persistence Reference')
    generation = Field(int, 'Generation')
    gtm_score = Field(int, 'Global Traffic Manager Score')
    protocol = Field(str, 'Protocol')
    kind = Field(str, 'Kind')
    mask = Field(str, 'Mask')
    mirror = Field(str, 'Mirror')
    nat64 = Field(str, 'NAT64')
    partition = Field(str, 'Partition')
    pool_reference = Field(ReferenceInfo, 'Pool Reference')
    profile_collection_reference = Field(ProfileCollectionReference, 'Profile Collection Reference')
    rate_limit = Field(str, 'Rate Limit')
    rate_limit_mode = Field(str, 'Rate Limit Mode')
    self_link = Field(str, 'Self Link')
    source_address = Field(str, 'Source Address')
    source_address_translation = Field(SourceAddressTranslation, 'Source Address Translation')
    source_port = Field(str, 'Source Port')
    state = Field(str, 'State')
    sub_path = Field(str, 'Sub Path')
    translate_port = Field(str, 'Translate Port')
    vlan_references = ListField(str, 'Vlan Refernces')
    vlans_enabled = Field(str, 'Vlan Enabled')
    tunnel_references = ListField(ReferenceInfo, 'Tunnel References')
    clone_pools = ListField(ClonePool, 'Clone Pools')
    irule_references = ListField(ReferenceInfo, 'IRules References')
